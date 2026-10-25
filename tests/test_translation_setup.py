"""Explicit setup contracts; fake packages are never called real neural inference."""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from naatik_next import translation_setup as setup
from naatik_next.storage import UserError,Cancelled


class Response(io.BytesIO):
    status=200
    def __init__(self,body=b'',status=200,headers=None,url=setup.INDEX):
        super().__init__(body);self.status=status;self.headers=headers or {};self.url=url
    def geturl(self):return self.url


def records(direct=False):
    pairs=[('ja','en'),('en','es')]+([('ja','es')] if direct else [])
    return [dict(from_code=a,to_code=b,from_name=a,to_name=b,package_version='1.0',argos_version='1.0',links=[f'https://argos-net.com/{a}_{b}.argosmodel']) for a,b in pairs]


def archive(a='ja',b='en'):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('model/metadata.json',json.dumps(dict(from_code=a,to_code=b,package_version='1.0',argos_version='1.0')))
        z.writestr('model/model/fixture.bin',b'not a real model'+b'x'*(300*1024))
        z.writestr('model/sentencepiece.model',b'not a real tokenizer')
    return stream.getvalue()


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='translation-setup-test-')
        self.profile=patch.dict(os.environ,{key:self.tmp.name+'/'+key for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME')})
        self.profile.start()
    def tearDown(self):self.profile.stop();self.tmp.cleanup()
    def cache(self,direct=False):
        return setup.catalogue(online=True,opener=lambda *a,**kw:Response(json.dumps(records(direct)).encode()))

    def test_confirmed_preparation_preserves_existing_model_versions(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        value = self.cache()
        proposal = setup.plans(value['items'])[0]
        api = Mock()
        api.get_installed_packages.return_value = [SimpleNamespace(from_code=a, to_code=b)
                                                  for a,b in [('ja','en'),('en','es')]]
        with patch('naatik_next.translation.package_api', return_value=(api, Path(self.tmp.name))), \
             patch.object(setup, 'download') as download, \
             patch('naatik_next.translation.install_package') as install, \
             patch.object(setup, 'validate', return_value={'verified':'fixture'}) as validate:
            result = setup.install_models(proposal['keys'], value['sha256'], preserve_installed=True)
        download.assert_not_called(); install.assert_not_called()
        validate.assert_called_once_with(['ja','en','es'], _locked=True)
        self.assertEqual(result, {'verified':'fixture'})

    def test_disappearing_installed_component_requires_new_consent(self):
        from unittest.mock import Mock
        value = self.cache(); proposal = setup.plans(value['items'])[0]
        api = Mock(); api.get_installed_packages.return_value = []
        with patch('naatik_next.translation.package_api', return_value=(api, Path(self.tmp.name))), \
             patch.object(setup, 'download') as download:
            with self.assertRaisesRegex(UserError, 'confirma de nuevo'):
                setup.install_models(proposal['keys'], value['sha256'], preserve_installed=True,
                                     download_keys=[proposal['keys'][1]])
        download.assert_not_called()

    def test_official_catalogue_cache_compatibility_and_explicit_plan(self):
        self.assertEqual(setup.catalogue()['items'],[])
        value=self.cache();self.assertEqual(setup.catalogue(),value)
        self.assertEqual(setup.plans(value['items'])[0]['route'],['ja','en','es'])
        direct=self.cache(True)
        self.assertEqual(setup.plans(direct['items'])[0]['route'],['ja','es'])
        items=records(True);items[-1]['argos_version']='99.0'
        self.assertEqual(setup.plans(setup.normalize(items))[0]['route'],['ja','en','es'])
        with self.assertRaises(UserError):setup.selected([value['items'][0]['key']],value['sha256'])
        self.assertEqual(setup.normalize([dict(records()[0],links=['https://evil.example/model'])]),[])
        with self.assertRaises(UserError):setup.secure_url('http://argos-net.com/model')
        with self.assertRaises(UserError):setup.secure_url('https://user:password@argos-net.com/model')

    def test_size_unpublished_is_not_invented_and_details_do_not_get_model(self):
        value=self.cache();plan=setup.plans(value['items'])[0];calls=[]
        def head(request,**kw):calls.append(request.get_method());return Response(headers={'Content-Length':'456'},url=request.full_url)
        result=setup.details(plan['keys'],value['sha256'],opener=head)
        self.assertEqual(calls,['HEAD','HEAD']);self.assertEqual(result['items'][0]['bytes'],456)
        def unavailable(*a,**kw):raise OSError('network blocked')
        result=setup.details(plan['keys'],value['sha256'],opener=unavailable)
        self.assertIsNone(result['items'][0]['bytes'])
        self.assertFalse((setup.root()/'downloads').exists())

    def test_cancel_partial_resume_and_offline_reuse(self):
        item=self.cache()['items'][0];body=archive();calls=[]
        def first(request,**kw):return Response(body,headers={'Content-Length':str(len(body)),'ETag':'"model-1"'},url=request.full_url)
        def cancel(text):raise Cancelled('injected cancellation')
        with self.assertRaises(Cancelled):setup.download(item,opener=first,progress=cancel)
        offset=(setup.root()/'downloads'/(item['key']+'.part')).stat().st_size
        self.assertEqual(offset,256*1024)
        def resume(request,**kw):
            calls.append(dict(request.header_items()))
            return Response(body[offset:],206,dict(ETag='"model-1"',**{'Content-Length':str(len(body)-offset),'Content-Range':f'bytes {offset}-{len(body)-1}/{len(body)}'}),request.full_url)
        target=setup.download(item,opener=resume)
        self.assertEqual(calls[0]['Range'],f'bytes={offset}-')
        self.assertEqual(target.read_bytes(),body)
        def blocked(*a,**kw):raise AssertionError('must reuse offline download')
        self.assertEqual(setup.download(item,opener=blocked),target)

    def test_wrong_range_and_corrupt_zip_never_install(self):
        item=self.cache()['items'][0];body=archive()
        with self.assertRaises(UserError):setup.download(item,opener=lambda req,**kw:Response(b'not zip',headers={'Content-Length':'7'},url=req.full_url))
        self.assertFalse((setup.root()/'packages').exists())
        folder=setup.root()/'downloads'
        (folder/(item['key']+'.part')).write_bytes(body[:10])
        setup.atomic_json(folder/(item['key']+'.json'),dict(validator='"v1"',total=len(body)))
        with self.assertRaises(UserError):setup.download(item,opener=lambda req,**kw:Response(body[10:],206,{'Content-Range':f'bytes 9-{len(body)-1}/{len(body)}','ETag':'"v1"'},req.full_url))

    def test_local_import_languages_and_real_validation_gate(self):
        from naatik_next.translation import install_package
        file=Path(self.tmp.name)/'local.argosmodel';file.write_bytes(archive())
        with self.assertRaises(UserError):install_package(file,expected=('ja','es'))
        result=install_package(file,expected=('ja','en'));self.assertTrue(Path(result['model']).is_dir())
        # This synthetic archive must fail actual CTranslate2 loading/inference.
        with self.assertRaises(UserError):setup.validate(['ja','en'])
        self.assertFalse((setup.root()/'validation.json').exists())

    def test_offline_guard_restores_network_and_rejects_access(self):
        import socket
        original=socket.getaddrinfo
        with setup.offline_guard():
            with self.assertRaises(UserError):socket.getaddrinfo('example.com',443)
        self.assertIs(socket.getaddrinfo,original)

    def test_runtime_provisioning_is_pinned_no_cache_and_partial_not_used(self):
        from naatik_next import translation_runtime as runtime
        target=runtime.runtime_directory();(target/'bin').mkdir(parents=True);(target/'bin/python').touch()
        self.assertNotEqual(runtime.program(),str(target/'bin/python'))
        calls=[]
        with patch.object(runtime,'run_progress',side_effect=lambda args,*a,**kw:calls.append((args,kw))):
            result=runtime.prepare()
        self.assertEqual(result['program'],str(target/'bin/python'))
        pip=next(args for args,_ in calls if 'pip' in args)
        self.assertIn('--require-hashes',pip);self.assertIn('--no-cache-dir',pip);self.assertIn('--no-deps',pip)
        self.assertIn('https://pypi.org/simple',pip)
        self.assertTrue((target/'next-runtime.json').exists())

    def test_runtime_failure_never_creates_readiness_manifest(self):
        from naatik_next import translation_runtime as runtime
        with patch.object(runtime,'run_progress',side_effect=UserError('injected DNS failure')):
            with self.assertRaises(UserError):runtime.prepare()
        self.assertFalse((runtime.runtime_directory()/'next-runtime.json').exists())

    def test_clean_source_contains_new_lock_but_no_runtime_or_models(self):
        from tools.public_install_validation import copy_source
        root=Path(__file__).resolve().parents[1];dest=Path(self.tmp.name)/'source with spaces'
        copy_source(root,dest)
        self.assertTrue((dest/'requirements-translation.lock').is_file())
        self.assertFalse((dest/'.venv').exists());self.assertFalse((dest/'.wheelhouse').exists())
        code='from naatik_next.translation_setup import status; import json; print(json.dumps(status()))'
        result=subprocess.run(['/usr/bin/python3.14','-c',code],cwd=dest,env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1'),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout);self.assertEqual(value['installed'],[])
        self.assertIn('Falta preparar',value['detail']);self.assertTrue(value['runtime_error'])
        result=subprocess.run(['/usr/bin/python3.14','-m','naatik_next.worker'],cwd=dest,
            env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1'),
            input=json.dumps(dict(action='translation_validate',route=['ja','en']))+'\n',text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('error',json.loads(result.stdout));self.assertNotIn('UnboundLocalError',result.stderr)

    def test_launcher_without_environment_opens_graphical_bootstrap(self):
        from tools.public_install_validation import copy_source
        import stat
        root=Path(__file__).resolve().parents[1];dest=Path(self.tmp.name)/'fresh source';copy_source(root,dest)
        bindir=Path(self.tmp.name)/'bin';bindir.mkdir()
        fake=bindir/'python3.14';fake.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$NEXT_TEST_CAPTURE"\n')
        fake.chmod(stat.S_IRWXU)
        capture=Path(self.tmp.name)/'args'
        result=subprocess.run([str(dest/'launch'),'--translator'],cwd=dest,env=dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'],NEXT_TEST_CAPTURE=str(capture)),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(capture.read_text().splitlines(),['-m','naatik_next.bootstrap','--translator'])

    def test_runtime_model_install_and_probe_share_exclusive_lock(self):
        from naatik_next import translation_runtime as runtime
        value=self.cache();plan=setup.plans(value['items'])[0]
        with setup.locked('.provision.lock'):
            with self.assertRaisesRegex(UserError,'otra preparación'):runtime.prepare()
            with self.assertRaisesRegex(UserError,'otra preparación'):setup.status()
            with self.assertRaisesRegex(UserError,'otra preparación'):setup.validate(['ja','en'])
            with self.assertRaisesRegex(UserError,'otra preparación'):setup.install_models(plan['keys'],value['sha256'])

    def test_http_denial_identifies_request_without_guessing_cause(self):
        import urllib.request,urllib.error
        for method in ('GET','HEAD'):
            request=urllib.request.Request('https://argos-net.com/ja_en.argosmodel',method=method)
            error=urllib.error.HTTPError(request.full_url,403,'Forbidden',{},None)
            with patch('urllib.request.build_opener') as factory:
                factory.return_value.open.side_effect=error
                with self.assertRaises(setup.AccessError) as caught:setup.open_url(request)
            message=str(caught.exception)
            self.assertIn('HTTP 403 en '+method,message)
            self.assertIn(request.full_url,message)
            self.assertIn('no identifica la causa',message)
            self.assertIn('navegador',message)
        value=self.cache();plan=setup.plans(value['items'])[0]
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.HTTPError('https://argos-net.com/model',403,'Forbidden',{},None)
            result=setup.details(plan['keys'],value['sha256'])
        self.assertIsNone(result['items'][0]['bytes'])
        self.assertIn('HTTP 403 en HEAD',result['items'][0]['size_detail'])
        self.assertFalse((setup.root()/'downloads').exists())
