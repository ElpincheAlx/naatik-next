import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from naatik_next.manga import descriptor
from naatik_next.processes import Task
from tests.test_processes import APP, spin_until


class MangaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {key: str(self.root / key) for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME']})
        self.env.start()
        self.tasks = []

    def tearDown(self):
        for task in self.tasks:
            task.close()
        self.env.stop()
        self.temp.cleanup()

    def fake_model(self, config=None):
        p = self.root / 'model'
        p.mkdir(exist_ok=True)
        for name in ['preprocessor_config.json', 'tokenizer_config.json', 'vocab.txt', 'pytorch_model.bin']:
            (p / name).write_text('fixture, not a model')
        (p / 'config.json').write_text(json.dumps(config or {'model_type': 'vision-encoder-decoder'}))
        return str(p)

    def detect(self, model):
        task = Task(persistent=True, module='naatik_next.manga_worker')
        self.tasks.append(task)
        result, errors = [], []
        task.result.connect(result.append)
        task.error.connect(errors.append)
        task.start({'action': 'detect', 'model': model})
        spin_until(lambda: not task.busy)
        self.assertFalse(errors, errors)
        return result[0]

    def test_missing_model_and_files_alone_are_not_ready(self):
        self.assertEqual(self.detect(str(self.root / 'missing'))['status'], 'recursos faltantes')
        config = {'manga_python': sys.executable, 'manga_model': self.fake_model()}
        self.assertEqual(descriptor(config)['status'], 'detectado')
        # Base Next venv has no manga-ocr package; fake model files cannot confer readiness.
        self.assertEqual(self.detect(config['manga_model'])['status'], 'recursos faltantes')

    def test_model_identity_and_malformed_config(self):
        self.assertEqual(self.detect(self.fake_model({'model_type': 'other'}))['status'], 'incompatible')
        self.assertEqual(self.detect(self.fake_model({'model_type': 'vision-encoder-decoder', 'auto_map': {'x': 'remote.py'}}))['status'], 'incompatible')
        p = self.fake_model()
        (Path(p) / 'config.json').write_text('{broken')
        self.assertEqual(self.detect(p)['status'], 'error')

    def test_fixed_language_selection_and_payload_preserve_tesseract_preference(self):
        from naatik_next.app import Window
        with patch('naatik_next.app.QTimer.singleShot'):
            w = Window()
        try:
            w.settings['ocr_language'] = 'jpn_vert'
            w.detected([{'id': 'tesseract', 'name': 'Tesseract', 'status': 'listo', 'detail': 'fixture', 'languages': ['eng', 'jpn_vert']},
                        {'id': 'mangaocr', 'name': 'MangaOCR', 'status': 'listo', 'detail': 'UI fixture only', 'languages': [], 'fixed_language': 'ja'}])
            w.engine.setCurrentIndex(w.engine.findData('mangaocr'))
            self.assertFalse(w.ocr_language.isEnabled())
            self.assertEqual(w.settings['ocr_language'], 'jpn_vert')
            w.image_path = 'fixture.png'
            with patch.object(w.manga_task, 'start') as send, patch.object(w.ocr_task, 'start') as fallback:
                w.recognize()
                request = send.call_args.args[0]
                self.assertEqual(request['engine'], 'mangaocr')
                self.assertEqual(request['language'], 'ja')
                fallback.assert_not_called()
            w.engine.setCurrentIndex(w.engine.findData('tesseract'))
            self.assertEqual(w.ocr_language.currentText(), 'jpn_vert')
        finally:
            w.close()

    def test_unexpected_idle_worker_exit_is_reported(self):
        task = Task(persistent=True, module='naatik_next.manga_worker')
        self.tasks.append(task)
        results, errors = [], []
        task.result.connect(results.append)
        task.error.connect(errors.append)
        task.start({'action': 'detect', 'model': str(self.root / 'missing')})
        spin_until(lambda: not task.busy)
        self.assertFalse(errors)
        task.process.kill()
        spin_until(lambda: bool(errors))
        self.assertIn('worker persistente terminó', errors[-1])
