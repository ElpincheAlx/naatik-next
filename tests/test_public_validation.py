import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from tools.public_install_validation import (parse_lock, audit_locks, snapshot,
    copy_source, command, fetch, Blocked, Failed)


class PublicValidationTests(unittest.TestCase):
    def test_every_hash_must_be_public_not_just_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); metadata=root/'metadata';metadata.mkdir()
            for name in ['requirements.lock','requirements-manga-build.lock','requirements-manga-cpu.lock','requirements-phrase.lock','requirements-translation.lock']:
                (root/name).write_text('test==1.0 --hash=sha256:'+'a'*64+' --hash=sha256:'+'b'*64+'\n')
            body=json.dumps({'info':{},'urls':[{'digests':{'sha256':'a'*64},'filename':'test.whl',
                'url':'https://files.pythonhosted.org/test.whl','size':1,'packagetype':'bdist_wheel'}]}).encode()
            with patch('tools.public_install_validation.fetch',return_value=body):
                with self.assertRaisesRegex(Failed,'no publicado'):
                    audit_locks(root,metadata)

    def test_public_artifact_and_official_cpu_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);metadata=root/'metadata';metadata.mkdir()
            for name in ['requirements.lock','requirements-manga-build.lock','requirements-phrase.lock','requirements-translation.lock']:
                (root/name).write_text('test==1.0 --hash=sha256:'+'a'*64+'\n')
            url='https://download-r2.pytorch.org/whl/cpu/torch-2.13.0%2Bcpu-cp314-cp314-manylinux_2_28_x86_64.whl'
            (root/'requirements-manga-cpu.lock').write_text('torch @ '+url+' --hash=sha256:'+'b'*64+'\n')
            body=json.dumps({'info':{'requires_python':'>=3.12'},'urls':[{'digests':{'sha256':'a'*64},
                'filename':'test.whl','url':'https://files.pythonhosted.org/test.whl','size':1,'packagetype':'bdist_wheel'}]}).encode()
            def response(target):
                return f'<a href="{url}#sha256:{"b"*64}">'.replace('#sha256:','#sha256=').encode() if 'pytorch' in target else body
            with patch('tools.public_install_validation.fetch',side_effect=response):
                records=audit_locks(root,metadata)
            self.assertEqual(len(records),5)
            self.assertTrue(all(r['verified'] for r in records))

    def test_missing_version_fails_and_network_is_blocked(self):
        with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://pypi.org/test',404,'missing',{},None)):
            with self.assertRaises(Failed): fetch('https://pypi.org/test')
        with patch('urllib.request.urlopen',side_effect=urllib.error.URLError('synthetic DNS failure')):
            with self.assertRaises(Blocked): fetch('https://pypi.org/test')

    def test_unpinned_requirement_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'lock';p.write_text('unfixed>=1\n')
            with self.assertRaises(Failed):parse_lock(p)

    def test_copy_excludes_developer_env_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            for name in ['naatik_next','tools','tests','examples','.wheelhouse','.venv']:
                (source/name).mkdir()
            for name in ['requirements.lock','requirements-manga-build.lock','requirements-manga-cpu.lock','requirements-phrase.lock','requirements-translation.lock','launch','naatik-next.desktop.in']:
                (source/name).write_text('fixture')
            for name in ['hello.png','nihon.png','personal.png']:(source/'examples'/name).write_bytes(b'test')
            (source/'.wheelhouse/private.whl').write_bytes(b'secret cache fixture')
            dest=root/'copy';copy_source(source,dest)
            self.assertFalse((dest/'.venv').exists())
            self.assertFalse((dest/'.wheelhouse').exists())
            self.assertEqual(sorted(p.name for p in (dest/'examples').iterdir()),['hello.png','nihon.png'])

    def test_subprocess_timeout_failure_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);log=root/'log'
            with self.assertRaisesRegex(Failed,'Timeout'):
                command([sys.executable,'-c','import time; time.sleep(5)'],root,log,.05)
            with self.assertRaisesRegex(Failed,'código 4'):
                command([sys.executable,'-c','raise SystemExit(4)'],root,log,5)
            with self.assertRaises(Blocked):
                command([sys.executable,'-c','print("HTTP Error 403: Forbidden"); raise SystemExit(1)'],root,log,5)
            command([sys.executable,'-c','print("checked")'],root,log,5)
            self.assertIn('checked',log.read_text())

    def test_profile_fingerprint_detects_existing_and_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);before=snapshot(root,root)
            folder=root/'naatik-next';folder.mkdir();(folder/'settings.json').write_text('{"test":true}')
            after=snapshot(root,root)
            self.assertNotEqual(before,after)
            self.assertNotIn('test',str(after))

    def test_metadata_python_minimum_is_separate_from_wheel_abi(self):
        from tools.python_compatibility import matrix
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'example.json').write_text(json.dumps({'info':{'name':'example','version':'1.0','requires_python':'>=3.12'},
                'urls':[{'packagetype':'bdist_wheel','filename':'example-1.0-cp312-cp312-manylinux_2_28_x86_64.whl'}]}))
            result=matrix(root)['matrix']
            self.assertFalse(result['3.11'][0]['metadata_accepts'])
            self.assertTrue(result['3.12'][0]['metadata_accepts'])
            self.assertTrue(result['3.12'][0]['compatible_public_wheels'])
            self.assertTrue(result['3.14'][0]['metadata_accepts'])
            self.assertFalse(result['3.14'][0]['compatible_public_wheels'])

    def test_owned_venv_accepts_system_python_symlink_without_accepting_external_env(self):
        from tools.public_model_smoke import runtime_root
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env=root/'venv';(env/'bin').mkdir(parents=True)
            (env/'pyvenv.cfg').write_text('include-system-site-packages = false')
            python=env/'bin/python';python.symlink_to(sys.executable)
            self.assertEqual(runtime_root(python,root),env)
            with self.assertRaises(AssertionError):runtime_root(python,root/'other')
