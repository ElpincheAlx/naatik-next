import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from naatik_next.resources import prepare_model
from naatik_next.manga import defaults
from naatik_next.storage import UserError


class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = headers or {}

    def geturl(self):
        return 'https://huggingface.co/test/file'


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'HOME': self.tmp.name,
            **{key: str(Path(self.tmp.name) / key) for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME']}})
        self.env.start()
        self.data = b'known model data'
        self.spec = {'id': 'test/model', 'revision': '0'*40, 'files': [
            {'name': 'config.json', 'bytes': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest()}]}

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_defaults_have_no_legacy_or_shared_cache(self):
        config = defaults()
        self.assertNotIn('JapaneseMining', str(config))
        self.assertNotIn('.cache/huggingface', str(config))
        self.assertIn(self.tmp.name, config['manga_model'])

    def test_interruption_resume_and_second_run_without_network(self):
        class Interrupted(Response):
            calls = 0
            def read(inner, size):
                inner.calls += 1
                if inner.calls == 1: return self.data[:5]
                raise TimeoutError('synthetic interrupted transport')
        with self.assertRaisesRegex(UserError, 'interrumpida'):
            prepare_model(spec=self.spec, opener=lambda *a, **k: Interrupted(b''))
        def resume(req, timeout):
            self.assertEqual(req.get_header('Range'), 'bytes=5-')
            self.assertEqual(timeout, 20)
            return Response(self.data[5:], 206, {'Content-Range': f'bytes 5-{len(self.data)-1}/{len(self.data)}'})
        result = prepare_model(spec=self.spec, opener=resume)
        final = Path(result['model']) / 'config.json'
        self.assertEqual(final.read_bytes(), self.data)
        prepare_model(spec=self.spec, opener=lambda *a, **k: self.fail('second run used network'))

    def test_bad_hash_is_not_accepted_or_kept(self):
        with self.assertRaisesRegex(UserError, 'Integridad'):
            prepare_model(spec=self.spec, opener=lambda *a, **k: Response(b'x'*len(self.data)))
        target = Path(defaults()['manga_model'])
        self.assertFalse((target / 'config.json').exists())
        self.assertFalse((target / 'config.json.part').exists())

    def test_absent_network_and_unsafe_name(self):
        with self.assertRaisesRegex(UserError, 'sin red'):
            prepare_model(spec=self.spec, opener=lambda *a, **k: (_ for _ in ()).throw(OSError('sin red')))
        self.spec['files'][0]['name'] = '../escape'
        with self.assertRaisesRegex(UserError, 'Nombre'):
            prepare_model(spec=self.spec)

    def test_server_ignores_range_restarts_and_rejects_oversize(self):
        target = Path(defaults()['manga_model']); target.mkdir(parents=True)
        (target / 'config.json.part').write_bytes(b'bad prefix')
        prepare_model(spec=self.spec, opener=lambda *a, **k: Response(self.data))
        (target / 'config.json').unlink()
        with self.assertRaisesRegex(UserError, 'supera'):
            prepare_model(spec=self.spec, opener=lambda *a, **k: Response(self.data+b'extra'))

    def test_wrong_resume_range_is_rejected(self):
        target = Path(defaults()['manga_model']); target.mkdir(parents=True)
        (target / 'config.json.part').write_bytes(self.data[:5])
        with self.assertRaisesRegex(UserError, 'reanudación'):
            prepare_model(spec=self.spec, opener=lambda *a, **k: Response(self.data[5:], 206, {'Content-Range': 'bytes 0-4/5'}))

    def test_cancel_preserves_partial_for_next_attempt(self):
        from naatik_next.storage import Cancelled
        class CancelledResponse(Response):
            calls = 0
            def read(inner, size):
                inner.calls += 1
                if inner.calls == 1: return self.data[:5]
                raise Cancelled('synthetic cancellation')
        with self.assertRaises(Cancelled):
            prepare_model(spec=self.spec, opener=lambda *a, **k: CancelledResponse(b''))
        target = Path(defaults()['manga_model'])
        self.assertEqual((target / 'config.json.part').read_bytes(), self.data[:5])
        self.assertFalse((target / 'verified-manifest.json').exists())
        prepare_model(spec=self.spec, opener=lambda *a, **k: Response(self.data[5:],206,
            {'Content-Range': f'bytes 5-{len(self.data)-1}/{len(self.data)}'}))
        self.assertEqual((target / 'config.json').read_bytes(), self.data)

    def test_concurrent_preparation_is_rejected(self):
        import fcntl
        target = Path(defaults()['manga_model']); target.mkdir(parents=True)
        with (target / '.download.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(UserError, 'en curso'):
                prepare_model(spec=self.spec, opener=lambda *a, **k: self.fail('concurrent network'))
