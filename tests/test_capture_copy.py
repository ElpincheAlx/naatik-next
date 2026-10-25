"""Offscreen capture-copy lifecycle with injected capture/OCR; no desktop focus claim."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QMessageBox
from naatik_next.app import Window, main
from tests import test_hotkey as fixtures
from tests.test_processes import APP


class CaptureCopyTests(unittest.TestCase):
    tearDown = fixtures.HotkeyTests.tearDown
    ready = fixtures.HotkeyTests.ready
    png = fixtures.HotkeyTests.png

    def setUp(self):
        fixtures.HotkeyTests.setUp(self)
        self.ready()
        self.w.startup_detection_started = True
        APP.clipboard().setText('previous clipboard')
        self.w.editor.setPlainText('manual corrections')
        self.w.translation.setPlainText('translation sentinel')
        self.w.selection_definitions.setPlainText('dictionary sentinel')

    def capture_result(self):
        self.w.capture_delay.stop()
        with patch.object(self.w.ocr_task, 'start') as start:
            self.w.captured(self.png())
        return start.call_args.args[0]

    def test_open_instance_quiet_copy_ignores_preference_preserves_editor(self):
        self.w.auto_copy.setChecked(False)
        with patch.object(self.w, 'raise_') as raised, patch.object(self.w, 'activateWindow') as activate, \
                patch.object(self.w.selection_task, 'start') as dictionary, \
                patch.object(self.w.lookup_task, 'start') as lookup, \
                patch.object(self.w.argos_task, 'start') as argos, \
                patch('naatik_next.app.QMessageBox.question') as question:
            self.assertEqual(self.w.external_command('capture-copy'), 'accepted')
            self.assertEqual(self.w.external_command('capture-copy'), 'ignored')
            request = self.capture_result()
            self.assertFalse(self.w.isVisible())
            self.assertEqual(self.w.external_command('capture-copy'), 'ignored')
            self.assertIs(QThread.currentThread(), APP.thread())
            self.w.ocr_task.result.emit(dict(generation=request['generation'], text=' 日本\n原文 '))
            self.assertEqual(APP.clipboard().text(), ' 日本\n原文 ')
            self.assertIsNone(self.w.copy_job)
            self.assertFalse(self.w.isVisible())
            dictionary.assert_not_called()
            lookup.assert_not_called()
            argos.assert_not_called()
            question.assert_not_called()
            raised.assert_not_called()
            activate.assert_not_called()
        self.assertEqual(self.w.editor.toPlainText(), 'manual corrections')
        self.assertEqual(self.w.raw_text, '日本')
        self.assertEqual(self.w.translation.toPlainText(), 'translation sentinel')
        self.assertEqual(self.w.selection_definitions.toPlainText(), 'dictionary sentinel')
        self.assertFalse(self.w.settings['auto_copy_ocr'])
        self.assertFalse(Path(request['image']).exists())
        self.w.external_command('show')
        self.assertTrue(self.w.isVisible())
        self.assertEqual(APP.clipboard().text(), ' 日本\n原文 ')

    def test_visible_window_restores_state_without_activation_or_repeated_show(self):
        self.w.showMinimized()
        original = self.w.windowState()
        with patch.object(self.w, 'raise_') as raised, patch.object(self.w, 'activateWindow') as activate:
            self.w.external_command('capture-copy')
            self.assertFalse(self.w.isVisible())
            request = self.capture_result()
            self.assertTrue(self.w.isVisible())
            self.assertEqual(self.w.windowState(), original)
            with patch.object(self.w, 'show') as show:
                self.w.recognized(dict(generation=request['generation'], text='result'))
                show.assert_not_called()
            raised.assert_not_called()
            activate.assert_not_called()

    def test_cancellation_error_empty_and_obsolete_answers_preserve_clipboard(self):
        with patch.object(self.w, 'notify_configuration') as notice, \
                patch.object(self.w.selection_task, 'start') as lookup, \
                patch('naatik_next.app.QMessageBox.warning') as modal:
            self.w.external_command('capture-copy')
            self.w.cancel()
            self.w.captured(self.png())
            self.assertIsNone(self.w.copy_job)
            self.w.external_command('capture-copy')
            self.w.capture_failed('Selección cancelada.')
            notice.assert_not_called()
            self.w.external_command('capture-copy')
            request = self.capture_result()
            self.w.cancel()
            self.w.external_command('capture-copy')
            new = self.capture_result()
            self.w.recognized(dict(generation=request['generation'], text='STALE'))
            self.assertEqual(APP.clipboard().text(), 'previous clipboard')
            self.w.recognized(dict(generation=new['generation'], text=' \n'))
            notice.assert_called_once()
            self.w.external_command('capture-copy')
            failed = self.capture_result()
            self.w.ocr_task.error.emit('fixture OCR failure')
            self.w.recognized(dict(generation=failed['generation'], text='late failed response'))
            self.assertEqual(APP.clipboard().text(), 'previous clipboard')
            self.assertIsNone(self.w.copy_job)
            self.assertFalse(self.w.isVisible())
            lookup.assert_not_called()
            modal.assert_not_called()

    def test_startup_requests_coalesce_and_cancel_drops_queue(self):
        self.w.startup_detection_started = False
        for _ in range(4):
            self.assertEqual(self.w.external_command('capture-copy'), 'queued')
        self.w.flush_external_capture()
        self.assertIsNone(self.w.copy_job)
        self.w.startup_detection_started = True
        self.w.flush_external_capture()
        self.assertIsNotNone(self.w.copy_job)
        self.assertFalse(self.w.pending_copy_capture)
        self.w.cancel()
        self.w.startup_detection_started = False
        self.w.external_command('capture-copy')
        self.w.cancel()
        self.w.startup_detection_started = True
        self.w.flush_external_capture()
        self.assertIsNone(self.w.copy_job)

    def test_unconfigured_ocr_notifies_with_configuration_action(self):
        self.w.engines = []
        with patch('naatik_next.app.QSystemTrayIcon') as tray, \
                patch('naatik_next.app.QMessageBox.warning') as modal, \
                patch.object(self.w, 'show') as show:
            self.assertEqual(self.w.external_command('capture-copy'), 'unavailable')
            tray.return_value.showMessage.assert_called_once()
            tray.return_value.messageClicked.connect.assert_called_once_with(self.w.open_configuration)
            menu = tray.return_value.setContextMenu.call_args.args[0]
            self.assertIn('Abrir Configuración', [action.text() for action in menu.actions()])
            show.assert_not_called()
            modal.assert_not_called()
        with patch.object(self.w, 'external_command') as command, patch.object(self.w, 'show_setup') as setup:
            self.w.open_configuration()
            command.assert_called_once_with('show')
            setup.assert_called_once()

    def test_manga_selected_uses_same_quiet_result_path(self):
        self.w.settings['ocr_engine'] = 'mangaocr'
        self.w.detected([dict(id='mangaocr', name='MangaOCR', status='listo', languages=[], detail='fixture')])
        with patch.object(self.w.manga_task, 'start') as manga, \
                patch.object(self.w.ocr_task, 'start') as other, \
                patch.object(self.w.selection_task, 'start') as dictionary:
            self.w.external_command('capture-copy')
            self.w.capture_delay.stop()
            self.w.captured(self.png())
            request = manga.call_args.args[0]
            self.assertEqual(request['engine'], 'mangaocr')
            self.assertEqual(request['language'], 'ja')
            self.w.manga_task.result.emit(dict(generation=request['generation'], text='原文'))
            self.assertEqual(APP.clipboard().text(), '原文')
            other.assert_not_called()
            dictionary.assert_not_called()

    def test_main_cold_background_and_forward_without_second_window(self):
        for owner in (True, False):
            broker = Mock()
            broker.acquire_or_forward.return_value = owner
            app = Mock()
            app.exec.return_value = 0
            with patch('naatik_next.app.os.umask'), patch('naatik_next.app.RotatingFileHandler'), \
                    patch('naatik_next.app.logging.basicConfig'), \
                    patch('naatik_next.app.sys.argv', ['launch', '--capture-copy']), \
                    patch('naatik_next.app.Instance', return_value=broker), \
                    patch('naatik_next.app.QApplication', return_value=app), \
                    patch('naatik_next.app.Window') as window:
                self.assertEqual(main(), 0)
                broker.acquire_or_forward.assert_called_once_with('capture-copy')
                if owner:
                    window.assert_called_once_with(background=True)
                    window.return_value.show.assert_not_called()
                    window.return_value.external_command.assert_called_once_with('capture-copy')
                    app.setQuitOnLastWindowClosed.assert_called_once_with(False)
                    app.exec.assert_called_once()
                else:
                    window.assert_not_called()
                    app.exec.assert_not_called()
                broker.close.assert_called_once()

    def test_background_initialization_never_schedules_setup_or_argos(self):
        scheduled = []
        with patch('naatik_next.app.QTimer.singleShot', side_effect=lambda delay, callback: scheduled.append(callback)), \
                patch.object(Window, 'notify_configuration'):
            background = Window(background=True)
        try:
            self.assertFalse(background.isVisible())
            self.assertNotIn(background.show_setup, scheduled)
            self.assertNotIn(background.redetect_argos, scheduled)
            self.assertIn(background.prepare_selected, scheduled)
            with patch.object(background, 'notify_configuration') as notice, \
                    patch('naatik_next.app.QMessageBox.warning') as modal:
                background.fail('startup failure')
                notice.assert_called_once()
                modal.assert_not_called()
        finally:
            background.close()

    def test_late_cancel_errors_from_workers_never_show_gui(self):
        with patch('naatik_next.app.QMessageBox.warning') as modal, \
                patch.object(self.w, 'showNormal') as normal, \
                patch.object(self.w, 'activateWindow') as activate:
            self.w.external_command('capture-copy')
            self.w.capture_delay.stop()
            with patch.object(self.w.capture_task, 'start'):
                self.w.start_capture_worker()
            self.w.cancel()
            self.w.capture_task.error.emit('Operación cancelada.')
            self.w.external_command('capture-copy')
            self.capture_result()
            self.w.cancel()
            self.w.ocr_task.error.emit('Operación cancelada.')
            self.assertEqual(APP.clipboard().text(), 'previous clipboard')
            modal.assert_not_called()
            normal.assert_not_called()
            activate.assert_not_called()

    def test_real_offscreen_event_loop_stays_alive_then_opens_gui(self):
        import subprocess
        import sys
        code = r'''
import base64
from unittest.mock import patch
from PySide6.QtCore import QTimer, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from naatik_next.app import main, Window
class Broker:
    def __init__(self, state): self.server = self
    def acquire_or_forward(self, action):
        assert action == 'capture-copy'
        return True
    def set_handler(self, handler): pass
    def close(self): pass
class ProbeWindow(Window):
    def __init__(self, **kwargs):
        assert kwargs == {'background': True}
        with patch('naatik_next.app.QTimer.singleShot'):
            super().__init__(**kwargs)
        self.needs_setup = False
        self.detected([dict(id='tesseract', name='Tesseract', status='listo', languages=['jpn'], detail='fixture')])
        self.startup_detection_started = True
        self.capture_delay.stop()
        QTimer.singleShot(0, self.complete)
    def complete(self):
        assert not self.isVisible()
        self.capture_delay.stop()
        image = QImage(20, 10, QImage.Format_RGB32)
        image.fill(0xffffffff)
        data = QByteArray(); buffer = QBuffer(data); buffer.open(QIODevice.WriteOnly)
        assert image.save(buffer, 'PNG')
        with patch.object(self.ocr_task, 'start') as start, patch.object(self.selection_task, 'start') as lookup, patch.object(self.argos_task, 'start') as argos:
            self.captured(base64.b64encode(bytes(data)).decode())
            request = start.call_args.args[0]
            self.recognized(dict(generation=request['generation'], text='persistent OCR'))
            lookup.assert_not_called(); argos.assert_not_called()
        assert not self.isVisible()
        QTimer.singleShot(100, self.later)
    def later(self):
        assert not self.isVisible()
        assert QApplication.clipboard().text() == 'persistent OCR'
        assert not QApplication.instance().quitOnLastWindowClosed()
        with patch.object(self, 'redetect_argos'):
            assert self.external_command('show') == 'shown'
        assert self.isVisible()
        assert QApplication.clipboard().text() == 'persistent OCR'
        print('hidden owner persisted and GUI opened', flush=True)
        self.close()
        QApplication.instance().quit()
with patch('naatik_next.app.Instance', Broker), patch('naatik_next.app.Window', ProbeWindow), patch('sys.argv', ['launch', '--capture-copy']):
    raise SystemExit(main())
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('hidden owner persisted and GUI opened', result.stdout)
