import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from naatik_next.processes import Task
from naatik_next.i18n import t as translate

APP = QApplication.instance() or QApplication([])


def spin_until(predicate, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        APP.processEvents()
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('Qt process deadline exceeded')


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {key: self.tmp.name + '/' + key for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME']})
        self.env.start()
        self.tasks = []

    def tearDown(self):
        for task in self.tasks:
            task.close()
        self.env.stop()
        self.tmp.cleanup()

    def task(self, persistent=False):
        t = Task(persistent=persistent)
        self.tasks.append(t)
        return t

    def test_actual_worker_error_keeps_event_loop_running(self):
        t = self.task()
        errors = []
        t.error.connect(errors.append)
        t.start({'action': 'import', 'path': '/nonexistent/dictionary.zip'})
        spin_until(lambda: bool(errors))
        self.assertFalse(t.busy)
        self.assertIn('dictionary.zip', errors[0])

    def test_cancel_actual_running_import_and_rollback(self):
        import zipfile
        from naatik_next.storage import Store
        p = Path(self.tmp.name) / 'test.zip'
        from tests.test_storage import ROW
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('index.json', json.dumps({'format': 3, 'title': 'Cancel', 'revision': '1'}))
            z.writestr('term_bank_1.json', json.dumps([ROW] * 40000))
        t = self.task(persistent=True)
        errors = []
        progress = []
        t.progress.connect(lambda value: (progress.append(value), t.cancel()))
        t.error.connect(errors.append)
        t.start({'action': 'import', 'path': str(p)})
        spin_until(lambda: bool(errors))
        self.assertTrue(progress)
        self.assertEqual(translate('Operación cancelada.'), errors[0])
        s = Store()
        self.assertEqual(s.list(), [])
        s.close()
        self.assertTrue(p.is_file())

    def test_timeout_actual_worker(self):
        t = self.task()
        errors = []
        t.error.connect(errors.append)
        t.start({'action': 'detect'}, timeout=1)
        spin_until(lambda: bool(errors))
        self.assertEqual(translate('Se agotó el tiempo de espera.'), errors[0])

    def test_gui_provenance_and_preferences(self):
        from naatik_next.app import Window
        # Do not run scheduled startup probes in this unit test.
        with patch('naatik_next.app.QTimer.singleShot'):
            w = Window()
        self.assertEqual(w.tabs.count(), 8)
        self.assertIn('Traducción', [w.tabs.tabText(i) for i in range(w.tabs.count())])
        w.raw_text = 'original'
        w.editor.setPlainText('corregido')
        self.assertIn('corregido', w.provenance.text())
        self.assertEqual(w.raw_text, 'original')
        w.close()

    def test_closing_active_worker_is_silent(self):
        t = self.task()
        errors = []
        t.error.connect(errors.append)
        t.start({'action': 'detect'})
        t.close()
        APP.processEvents()
        self.assertEqual(errors, [])
        self.assertFalse(t.busy)

    def test_translation_uses_edit_snapshot_without_overwriting_original_or_dictionary(self):
        from naatik_next.app import Window
        with patch('naatik_next.app.QTimer.singleShot'):
            w = Window()
        try:
            w.detected([{'id': 'tesseract', 'name': 'Tesseract', 'status': 'listo',
                         'detail': 'Fixture de UI, no detección real', 'languages': ['jpn', 'jpn_vert']}])
            w.ocr_language.setCurrentText('jpn')
            w.target.addItem('ja → en', ['ja', 'en'])
            w.image_path = w.ocr_request_image = 'fixture-image'
            original = 'OCR simulado — 日木'
            w.ocr_pending = 1
            w.recognized({'generation': 1, 'text': original})
            w.editor.setPlainText('日本')
            self.assertIn('corregido', w.provenance.text())
            with patch.object(w.argos_task, 'start') as send, patch.object(w.lookup_task, 'start') as lookup:
                w.translate()
                send.assert_called_once_with({'action': 'translate', 'text': '日本', 'route': ['ja', 'en']}, 180000)
                lookup.assert_not_called()
            self.assertEqual(w.raw_text, original)
            # A later correction cannot change the text associated with the response.
            w.editor.setPlainText('otra corrección')
            w.argos_result({'text': 'Japanese', 'route': ['ja', 'en']})
            self.assertEqual(w.translated_source, '日本')
            self.assertEqual(w.editor.toPlainText(), 'otra corrección')
            self.assertEqual(w.raw_text, original)
            self.assertIn('anterior', w.translation_status.text())
            self.assertEqual(w.engine.currentData(), 'tesseract')
            self.assertEqual(w.ocr_language.currentText(), 'jpn')
            self.assertEqual(w.target.currentData(), ['ja', 'en'])
            w.looked_up([{'title': 'Diccionario de prueba', 'expression': '日本',
                          'reading': 'にほん', 'meanings': '["Japan"]'}])
            self.assertIn('Diccionario de prueba', w.definitions.toPlainText())
            self.assertIn('Japan', w.definitions.toPlainText())
            self.assertEqual(w.translation.toPlainText(), 'Japanese')
        finally:
            w.close()

    def test_close_is_terminal_idempotent_and_stops_cancel_timer(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        t = self.task(persistent=True)
        results, errors = [], []
        t.result.connect(results.append)
        t.error.connect(errors.append)
        t.start({'action': 'detect'})
        spin_until(lambda: t.process is not None and t.process.processId() > 0)
        p = t.process
        t.cancel()
        t.close()
        t.close()
        self.assertFalse(t.kill_timer.isActive())
        self.assertFalse(t.timer.isActive())
        t.start({'action': 'detect'})
        self.assertIs(t.process, p)
        self.assertFalse(t.busy)
        p.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        # Stale/queued paths must reject the destroyed emitting process before IO.
        t._stderr(p)
        t._read(p)
        t._finished(0, None, p)
        t._process_error(None, p)
        t._kill_cancelled()
        self.assertEqual((results, errors), ([], []))
        t.process = None

    def test_old_callbacks_rejected_after_explicit_reopen(self):
        t = self.task()
        t.start({'action': 'import', 'path': '/nonexistent'})
        spin_until(lambda: not t.busy)
        old = t.process
        t.close()
        t.reopen()
        t.start({'action': 'import', 'path': '/nonexistent-again'})
        current = t.process
        t._stderr(old)
        t._read(old)
        t._finished(0, None, old)
        self.assertIs(t.process, current)
        self.assertTrue(t.busy)
        spin_until(lambda: not t.busy)
