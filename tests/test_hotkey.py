"""Offscreen orchestration and protocol regressions; no real desktop claim."""
import base64
import ctypes as C
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QKeySequence
from naatik_next.app import Window
from naatik_next.hotkey import X11Grab, ErrorEvent, Event, combination, DEFAULT_SHORTCUT
from naatik_next.storage import UserError, load_settings
from tests.test_processes import APP


class FakeGrab:
    instances = []
    conflict = False

    def __init__(self):
        self.fd, self.writer = os.pipe()
        self.closed = False
        self.instances.append(self)

    def register(self, name, modifiers):
        if self.conflict:
            raise UserError('Conflicto X11 de prueba')

    def close(self):
        if not self.closed:
            os.close(self.fd)
            os.close(self.writer)
            self.closed = True


class HotkeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {k: self.tmp.name + '/' + k for k in
                            ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME')})
        self.env.start()
        with patch('naatik_next.app.QTimer.singleShot'):
            self.w = Window()
        FakeGrab.instances = []
        FakeGrab.conflict = False

    def tearDown(self):
        self.w.close()
        self.env.stop()
        self.tmp.cleanup()

    def backend(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11', 'XDG_CURRENT_DESKTOP': 'KDE'}))
        stack.enter_context(patch('naatik_next.hotkey.QGuiApplication.platformName', return_value='xcb'))
        stack.enter_context(patch('naatik_next.hotkey.X11Grab', FakeGrab))
        return stack

    def ready(self):
        self.w.detected([{'id': 'tesseract', 'name': 'Tesseract', 'status': 'listo',
                         'detail': 'UI fixture, not a real probe', 'languages': ['jpn']}])
        self.w.raw_text = '日本'
        self.w.editor.setPlainText('日本')

    def png(self):
        image = QImage(10, 10, QImage.Format_RGB32)
        image.fill(Qt.white)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.WriteOnly)
        image.save(buf, 'PNG')
        return base64.b64encode(bytes(data)).decode()

    def test_preferences_registration_change_disable_restore_reopen_close(self):
        self.assertFalse(self.w.settings.get('capture_shortcut_enabled', False))
        with self.backend():
            self.w.shortcut_field.setKeySequence(QKeySequence('Ctrl+Alt+F8'))
            self.w.save_shortcut()
            first = FakeGrab.instances[-1]
            self.assertEqual(self.w.shortcut.active, 'Ctrl+Alt+F8')
            self.assertIn('Registrado', self.w.shortcut_status.text())
            self.w.shortcut_field.setKeySequence(QKeySequence('Ctrl+Alt+F9'))
            self.w.save_shortcut()
            self.assertTrue(first.closed)
            self.assertEqual(load_settings()['capture_shortcut'], 'Ctrl+Alt+F9')
            self.w.restore_shortcut()
            self.assertEqual(self.w.shortcut.active, 'Ctrl+Alt+F9')
            self.assertEqual(self.w.shortcut_field.keySequence().toString(QKeySequence.PortableText), DEFAULT_SHORTCUT)
            self.w.close()
            self.assertTrue(FakeGrab.instances[-1].closed)
            with patch('naatik_next.app.QTimer.singleShot'):
                self.w = Window()
            self.assertEqual(self.w.shortcut.active, 'Ctrl+Alt+F9')
            self.w.disable_shortcut()
            self.assertFalse(load_settings()['capture_shortcut_enabled'])
            self.assertFalse(self.w.shortcut.active)
            self.assertTrue(FakeGrab.instances[-1].closed)

    def test_conflict_invalid_sequence_and_unsupported_platform(self):
        with self.backend():
            self.w.save_shortcut()
            first = FakeGrab.instances[-1]
            self.w.shortcut_field.clear()
            self.w.save_shortcut()
            self.assertFalse(first.closed)  # Invalid input does not remove an active binding.
            self.w.shortcut_field.setKeySequence(QKeySequence('Ctrl+Alt+F9'))
            FakeGrab.conflict = True
            self.w.save_shortcut()
            self.assertTrue(first.closed)
            self.assertTrue(FakeGrab.instances[-1].closed)
            self.assertFalse(self.w.shortcut.active)
            self.assertIn('Error de registro', self.w.shortcut_status.text())
        self.w.apply_saved_shortcut()
        self.assertIn('offscreen', self.w.shortcut_status.text())
        for bad in ('A', 'Shift+A', 'Ctrl+A, Ctrl+B', 'Ctrl+;'):
            with self.assertRaises(UserError):
                combination(bad)

    def test_write_failure_reports_and_restores_previous_registration(self):
        with self.backend():
            self.w.save_shortcut()
            self.w.shortcut_field.setKeySequence(QKeySequence('Ctrl+Alt+F9'))
            with patch('naatik_next.app.save_settings', side_effect=OSError('fixture write failure')):
                self.w.save_shortcut()
            self.assertEqual(self.w.shortcut.active, DEFAULT_SHORTCUT)
            self.assertIn('No se guardaron', self.w.shortcut_status.text())
            self.assertEqual(load_settings()['capture_shortcut'], DEFAULT_SHORTCUT)

    def test_disable_releases_registration_even_if_saving_fails(self):
        with self.backend():
            self.w.save_shortcut()
            old = FakeGrab.instances[-1]
            with patch('naatik_next.app.save_settings', side_effect=OSError('fixture write failure')):
                self.w.disable_shortcut()
            self.assertFalse(self.w.shortcut.active)
            self.assertTrue(old.closed)
            self.assertFalse(self.w.settings['capture_shortcut_enabled'])
            self.assertTrue(load_settings()['capture_shortcut_enabled'])
            self.assertIn('Desactivado en esta sesión', self.w.shortcut_status.text())

    def test_capture_then_selected_ocr_without_translation_and_repeat_guard(self):
        self.ready()
        self.w.showMaximized()
        with patch.object(self.w.capture_task, 'start') as capture, patch.object(self.w.ocr_task, 'start') as ocr, patch.object(self.w.argos_task, 'start') as argos:
            self.w.capture(auto_ocr=True)
            self.assertTrue(self.w.capture_active)
            self.assertFalse(self.w.isVisible())
            for _ in range(5):
                self.w.capture(auto_ocr=True)
            self.w.capture_delay.stop()
            self.w.start_capture_worker()
            self.assertEqual(capture.call_args.args[0]['action'], 'capture')
            self.assertEqual(capture.call_args.args[1], 140000)
            self.w.captured(self.png())
            self.assertTrue(self.w.isVisible())
            self.assertTrue(self.w.isMaximized())
            self.assertFalse(self.w.capture_active)
            ocr.assert_called_once()
            self.assertEqual(ocr.call_args.args[0]['engine'], 'tesseract')
            self.assertEqual(ocr.call_args.args[0]['language'], 'jpn')
            argos.assert_not_called()
            self.w.ocr_task.busy = True
            self.w.capture(auto_ocr=True)
            self.assertFalse(self.w.capture_active)
            self.w.ocr_task.busy = False

    def test_manga_selected_uses_its_worker_and_fixed_language(self):
        self.w.settings['ocr_engine'] = 'mangaocr'
        self.w.detected([{'id': 'mangaocr', 'name': 'MangaOCR', 'status': 'listo',
                          'detail': 'Simulated ready status; no real model load here', 'languages': []}])
        with patch.object(self.w.manga_task, 'start') as manga, patch.object(self.w.ocr_task, 'start') as other:
            self.w.capture(auto_ocr=True)
            self.w.capture_delay.stop()
            self.w.captured(self.png())
            self.assertEqual(manga.call_args.args[0]['engine'], 'mangaocr')
            self.assertEqual(manga.call_args.args[0]['language'], 'ja')
            other.assert_not_called()
            self.assertEqual(self.w.engine.currentData(), 'mangaocr')

    def test_changed_language_does_not_silently_recognize(self):
        self.ready()
        with patch.object(self.w.ocr_task, 'start') as ocr, patch.object(self.w, 'fail') as fail:
            self.w.capture(auto_ocr=True)
            self.w.capture_delay.stop()
            self.w.ocr_language.addItem('eng')
            self.w.ocr_language.setCurrentText('eng')
            self.w.captured(self.png())
            ocr.assert_not_called()
            fail.assert_called_once()
            self.assertEqual(self.w.ocr_language.currentText(), 'eng')

    def test_cancel_delay_and_worker_preserves_previous_content(self):
        self.ready()
        self.w.editor.setPlainText('日本 correction')
        self.w.selection_definitions.setPlainText('dictionary sentinel')
        with patch.object(self.w.capture_task, 'start') as capture, patch.object(self.w.ocr_task, 'start') as ocr, patch('naatik_next.app.QMessageBox.information'):
            self.w.capture()
            self.w.cancel()
            self.w.start_capture_worker()
            capture.assert_not_called()
            self.assertTrue(self.w.isVisible())
            self.w.capture()
            self.w.capture_delay.stop()
            self.w.start_capture_worker()
            self.w.capture_failed('Selección cancelada: fixture')
            self.assertFalse(self.w.capture_active)
            self.assertTrue(self.w.capture_btn.isEnabled())
            self.assertEqual(self.w.raw_text, '日本')
            self.assertEqual(self.w.editor.toPlainText(), '日本 correction')
            self.assertEqual(self.w.selection_definitions.toPlainText(), 'dictionary sentinel')
            ocr.assert_not_called()

    def test_not_ready_and_declined_correction_do_not_capture(self):
        with patch.object(self.w, 'fail') as fail:
            self.w.capture(auto_ocr=True)
            fail.assert_called_once()
            self.assertFalse(self.w.capture_active)
        self.ready()
        self.w.editor.setPlainText('corrected')
        with patch('naatik_next.app.QMessageBox.question', return_value=0):
            self.w.capture(auto_ocr=True)
        self.assertFalse(self.w.capture_active)
        self.assertEqual(self.w.editor.toPlainText(), 'corrected')

    def test_global_activation_when_another_application_has_focus(self):
        self.ready()
        with patch.object(self.w, 'isActiveWindow', return_value=False), patch.object(self.w.shortcut_field, 'hasFocus', return_value=True), patch.object(self.w, 'capture') as capture:
            self.w.shortcut.activated.emit()
            capture.assert_called_once_with(auto_ocr=True)
        with patch.object(self.w, 'isActiveWindow', return_value=True), patch.object(self.w.shortcut_field, 'hasFocus', return_value=True), patch.object(self.w, 'capture') as capture:
            self.w.shortcut.activated.emit()
            capture.assert_not_called()

    def test_real_library_display_error_is_reported(self):
        # Real libX11 ABI/load, deliberately unavailable display; no desktop registration.
        with patch.dict(os.environ, {'DISPLAY': ':9999'}):
            with self.assertRaisesRegex(UserError, 'display X11'):
                X11Grab()


    def test_three_action_shortcuts_independent_persistent_and_legacy_unchanged(self):
        with self.backend():
            for action, combination_text in (('capture-copy','Ctrl+Alt+1'),('translator','Ctrl+Alt+2'),('phrase','Ctrl+Alt+3'),('show','Ctrl+Alt+4')):
                self.w.action_shortcut_fields[action].setKeySequence(QKeySequence(combination_text))
                from PySide6.QtWidgets import QGroupBox,QPushButton
                from naatik_next.integrations import ACTIONS
                self.w.integration_action.setCurrentIndex(self.w.integration_action.findData(action))
                group=next(g for g in self.w.findChildren(QGroupBox) if g.title()=='Atajo de teclado')
                next(b for b in group.findChildren(QPushButton) if b.text()=='Guardar').click()
                self.assertEqual(self.w.action_shortcuts[action].active,combination_text)
            saved=load_settings()
            self.assertFalse(saved.get('capture_shortcut_enabled',False))
            self.w.disable_action_shortcut('translator')
            self.assertEqual(self.w.action_shortcuts['translator'].active,'')
            self.assertEqual(self.w.action_shortcuts['capture-copy'].active,'Ctrl+Alt+1')
            self.assertEqual(self.w.action_shortcuts['phrase'].active,'Ctrl+Alt+3')
            self.w.close()
            with patch('naatik_next.app.QTimer.singleShot'):
                self.w=Window()
            self.assertEqual(self.w.action_shortcuts['capture-copy'].active,'Ctrl+Alt+1')
            self.assertEqual(self.w.action_shortcuts['phrase'].active,'Ctrl+Alt+3')
            self.assertEqual(self.w.action_shortcuts['show'].active,'Ctrl+Alt+4')
            self.assertEqual(self.w.action_shortcuts['translator'].active,'')
            self.assertEqual(self.w.action_shortcut_fields['translator'].keySequence().toString(),'Ctrl+Alt+2')

    def test_action_shortcuts_duplicate_legacy_and_system_conflicts(self):
        with self.backend():
            self.w.action_shortcut_fields['translator'].setKeySequence(QKeySequence('Ctrl+Alt+2'))
            self.w.save_action_shortcut('translator')
            self.w.action_shortcut_fields['phrase'].setKeySequence(QKeySequence('Ctrl+Alt+2'))
            self.w.save_action_shortcut('phrase')
            self.assertIn('duplicada',self.w.action_shortcut_status['phrase'].text())
            self.assertFalse(self.w.settings.get('phrase_shortcut_enabled',False))
            self.w.change_shortcut_settings('Ctrl+Alt+2',True)
            self.assertIn('duplicada',self.w.shortcut_status.text())
            self.assertEqual(self.w.action_shortcuts['translator'].active,'Ctrl+Alt+2')
            self.w.action_shortcut_fields['capture-copy'].setKeySequence(QKeySequence('Ctrl+Alt+1'))
            FakeGrab.conflict=True
            self.w.save_action_shortcut('capture-copy')
            self.assertIn('Conflicto X11',self.w.action_shortcut_status['capture-copy'].text())
            self.assertFalse(self.w.settings.get('capture_copy_shortcut_enabled',False))

    def test_all_new_global_shortcuts_dispatch_the_same_internal_action(self):
        with patch.object(self.w,'external_command',return_value='accepted') as dispatch:
            for action,shortcut in self.w.action_shortcuts.items():
                shortcut.activated.emit()
                dispatch.assert_called_with(action)
        with patch.object(self.w,'capture_and_recognize') as capture, \
                patch.object(self.w,'isActiveWindow',return_value=True), \
                patch.object(self.w.action_shortcut_fields['translator'],'hasFocus',return_value=True):
            self.w.global_capture()
            capture.assert_not_called()

    def test_show_conflict_with_other_action_and_legacy_and_disable_write_error(self):
        with self.backend():
            self.w.action_shortcut_fields['show'].setKeySequence(QKeySequence('Ctrl+Alt+4'))
            self.w.save_action_shortcut('show')
            self.w.action_shortcut_fields['translator'].setKeySequence(QKeySequence('Ctrl+Alt+4'))
            self.w.save_action_shortcut('translator')
            self.assertIn('duplicada', self.w.action_shortcut_status['translator'].text())
            self.w.change_shortcut_settings('Ctrl+Alt+4', True)
            self.assertIn('duplicada', self.w.shortcut_status.text())
            with patch('naatik_next.app.save_settings', side_effect=OSError('fixture write failure')):
                self.w.disable_action_shortcut('show')
            self.assertFalse(self.w.action_shortcuts['show'].active)
            self.assertIn('Desactivado en esta sesión', self.w.action_shortcut_status['show'].text())
            self.assertIn('No se pudo guardar', self.w.action_shortcut_status['show'].text())
            self.assertTrue(load_settings()['show_shortcut_enabled'])

    def test_offscreen_saved_request_does_not_claim_registration(self):
        from naatik_next.storage import save_settings
        self.w.settings.update(show_shortcut='Ctrl+Alt+4', show_shortcut_enabled=True)
        save_settings(self.w.settings); self.w.close()
        with patch('naatik_next.app.QTimer.singleShot'): self.w = Window()
        self.assertFalse(self.w.action_shortcuts['show'].active)
        self.assertIn('No registrado', self.w.action_shortcut_status['show'].text())
        self.assertIn('offscreen', self.w.action_shortcut_status['show'].text())
        self.assertTrue(load_settings()['show_shortcut_enabled'])



class GrabProtocolTests(unittest.TestCase):
    def test_bad_access_rolls_back_only_own_specific_grabs(self):
        class Library:
            def __init__(self):
                self.handler = None
                self.added = []
                self.removed = []
            def XSetErrorHandler(self, handler):
                previous = self.handler
                self.handler = handler
                return previous
            def XSync(self, display, discard):
                if self.handler:
                    callback = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(ErrorEvent))(self.handler.value)
                    error = ErrorEvent()
                    error.error_code = 10
                    callback(display, C.pointer(error))
            def XGrabKey(self, display, code, mask, root, owner, pointer, keyboard):
                self.added.append((code, mask))
                assert code != 0 and mask != 32768  # No AnyKey / AnyModifier.
            def XUngrabKey(self, display, code, mask, root):
                self.removed.append((code, mask))
        backend = X11Grab.__new__(X11Grab)
        backend.lib = Library()
        backend.display = 1
        backend.root = 2
        backend.grabs = []
        backend.code = lambda name: 27
        backend.modifier_masks = lambda: {'ctrl': 4, 'alt': 8, 'shift': 1, 'meta': 64, 'locks': 18}
        with self.assertRaisesRegex(UserError, 'Conflicto X11'):
            backend.register('r', Qt.ControlModifier | Qt.AltModifier)
        self.assertEqual(backend.lib.added, [(27, x) for x in (12, 14, 28, 30)])
        self.assertEqual(backend.lib.removed, backend.lib.added)
        self.assertEqual(backend.grabs, [])
        self.assertIsNone(backend.lib.handler)

    def test_repeat_and_unrelated_events_do_not_activate(self):
        class Events:
            def __init__(self, values):
                self.events = []
                for kind, code, timestamp in values:
                    event = Event()
                    event.key.type = kind
                    event.key.keycode = code
                    event.key.time = timestamp
                    self.events.append(event)
            def XPending(self, display):
                return len(self.events)
            def XNextEvent(self, display, pointer):
                event = self.events.pop(0)
                C.memmove(pointer, C.byref(event), C.sizeof(Event))
            def XPeekEvent(self, display, pointer):
                C.memmove(pointer, C.byref(self.events[0]), C.sizeof(Event))
        backend = X11Grab.__new__(X11Grab)
        backend.display = 1
        backend.keycode = 27
        backend.down = False
        backend.lib = Events([(2, 99, 1), (2, 27, 2)])
        self.assertTrue(backend.drain())
        # A held-key repeat does not emit another activation.
        backend.lib = Events([(3, 27, 3), (2, 27, 3), (2, 99, 4)])
        self.assertFalse(backend.drain())
        backend.lib = Events([(3, 27, 5)])
        self.assertFalse(backend.drain())
        backend.lib = Events([(2, 27, 6)])
        self.assertTrue(backend.drain())
