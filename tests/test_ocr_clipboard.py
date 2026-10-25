"""Qt offscreen clipboard/orchestration tests; no cross-application paste claim."""
import unittest
from unittest.mock import patch
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QPushButton
from naatik_next.storage import load_settings
from tests import test_hotkey as fixtures
from tests.test_processes import APP


class ClipboardTests(unittest.TestCase):
    tearDown = fixtures.HotkeyTests.tearDown
    ready = fixtures.HotkeyTests.ready
    png = fixtures.HotkeyTests.png

    def setUp(self):
        fixtures.HotkeyTests.setUp(self)
        QApplication.clipboard().setText('previous clipboard')
        self.ready()

    def start_ocr(self):
        with patch.object(self.w.ocr_task, 'start') as start:
            self.w.recognize()
        return start.call_args.args[0]['generation']

    def deliver(self, generation, text):
        self.w.ocr_task.result.emit({'generation': generation, 'text': text})

    def test_all_capture_entries_and_selected_engines(self):
        for engine in ('tesseract', 'mangaocr'):
            self.w.settings['ocr_engine'] = engine
            self.w.detected([{'id': engine, 'name': engine, 'status': 'listo',
                              'languages': ['jpn'] if engine == 'tesseract' else [], 'detail': 'fixture'}])
            task = self.w.ocr_task if engine == 'tesseract' else self.w.manga_task
            for entry in ('button', 'hotkey', 'external'):
                with self.subTest(engine=engine, entry=entry), patch.object(task, 'start') as start, \
                        patch.object(self.w.selection_task, 'start') as lookup:
                    self.w.startup_detection_started = True
                    if entry == 'button':
                        self.w.capture_btn.click()
                    elif entry == 'hotkey':
                        self.w.shortcut.activated.emit()
                    else:
                        self.assertEqual(self.w.external_command('capture'), 'accepted')
                    self.w.capture_delay.stop()
                    self.w.captured(self.png())
                    request = start.call_args.args[0]
                    self.assertEqual(request['engine'], engine)
                    self.assertEqual(request['language'], 'jpn' if engine == 'tesseract' else 'ja')
                    self.assertIs(QThread.currentThread(), APP.thread())
                    task.result.emit({'generation': request['generation'], 'text': ' 日本\n原文 '})
                    self.assertEqual(QApplication.clipboard().text(), ' 日本\n原文 ')
                    self.assertEqual(self.w.raw_text, ' 日本\n原文 ')
                    self.assertEqual(self.w.editor.toPlainText(), ' 日本\n原文 ')
                    self.assertEqual(self.w.statusBar().currentMessage(), 'Texto reconocido y copiado')
                    lookup.assert_called_once()
                    self.assertEqual(lookup.call_args.args[0]['term'], ' 日本\n原文 ')
                    self.assertFalse(self.w.editor.textCursor().hasSelection())

    def test_disabled_persistent_and_manual_copy_and_edits(self):
        self.assertTrue(self.w.auto_copy.isChecked())
        self.w.auto_copy.setChecked(False)
        self.assertIs(load_settings()['auto_copy_ocr'], False)
        with patch('naatik_next.app.QTimer.singleShot'):
            reopened = fixtures.Window()
        try:
            self.assertFalse(reopened.auto_copy.isChecked())
        finally:
            reopened.close()
        self.w.image_path = 'fixture'
        generation = self.start_ocr()
        self.deliver(generation, 'OCR original')
        self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')
        self.w.editor.setPlainText('manual edit')
        self.w.translation.setPlainText('translation sentinel')
        self.w.selection_definitions.setPlainText('definition sentinel')
        self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')
        self.assertEqual(self.w.raw_text, 'OCR original')
        next(b for b in self.w.findChildren(QPushButton) if b.text() == 'Copiar texto').click()
        self.assertEqual(QApplication.clipboard().text(), 'manual edit')
        self.w.auto_copy.setChecked(True)
        self.assertIs(load_settings()['auto_copy_ocr'], True)
        self.w.editor.insertPlainText('typing')
        self.assertEqual(QApplication.clipboard().text(), 'manual edit')

    def test_empty_failure_cancel_stale_and_duplicate(self):
        self.w.image_path = 'fixture'
        with patch.object(self.w, 'fail'):
            old = self.start_ocr()
            self.deliver(old, ' \n\t')
            self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')
            failed = self.start_ocr()
            self.w.ocr_task.error.emit('fixture OCR error')
            self.deliver(failed, 'late after error')
            cancelled = self.start_ocr()
            self.w.cancel()
            self.deliver(cancelled, 'late after cancel')
            current = self.start_ocr()
            self.deliver(cancelled, 'stale during newer request')
            self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')
            self.deliver(current, 'new OCR')
            QApplication.clipboard().setText('later user clipboard')
            self.deliver(current, 'duplicate response')
            self.assertEqual(QApplication.clipboard().text(), 'later user clipboard')
            self.assertEqual(self.w.raw_text, 'new OCR')

    def test_capture_cancel_and_changed_image_preserve_clipboard(self):
        self.w.capture_btn.click()
        self.w.cancel()
        self.w.captured(self.png())
        self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')
        self.assertEqual(self.w.raw_text, '日本')
        self.w.image_path = 'fixture'
        generation = self.start_ocr()
        self.w.image_path = 'different fixture'
        self.deliver(generation, 'old image OCR')
        self.assertEqual(QApplication.clipboard().text(), 'previous clipboard')


class WorkerIdentityTests(unittest.TestCase):
    def test_both_worker_protocols_echo_identity(self):
        import io
        import json
        from naatik_next import worker, manga_worker
        for module, adapter in ((worker, 'naatik_next.ocr.Tesseract'),
                                (manga_worker, 'naatik_next.manga_worker.Engine')):
            request = {'action': 'ocr', 'engine': 'tesseract', 'image': 'fixture',
                       'language': 'jpn', 'generation': 42}
            output = io.StringIO()
            with self.subTest(worker=module.__name__), patch(adapter) as engine, \
                    patch('sys.stdin', io.StringIO(json.dumps(request) + '\n')), \
                    patch('sys.stdout', output), patch.object(module.signal, 'signal'), \
                    patch('logging.basicConfig'):
                engine.return_value.recognize.return_value = '原文'
                module.main()
            self.assertEqual(json.loads(output.getvalue()),
                             {'result': {'generation': 42, 'text': '原文'}})
