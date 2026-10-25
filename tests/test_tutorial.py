import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QMainWindow
from naatik_next.storage import load_settings, save_settings
from naatik_next.tutorial import initial_state, automatic, persist, open_tutorial

APP = QApplication.instance() or QApplication([])

class Owner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.settings['tutorial'] = initial_state(self.settings)
        self.errors = []
    def fail(self, message):
        self.errors.append(message)

class TutorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {k: str(Path(self.tmp.name)/k) for k in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME')})
        self.env.start()
        self.owners = []
    def tearDown(self):
        for owner in self.owners:
            owner.close()
        self.env.stop()
        self.tmp.cleanup()
    def owner(self):
        owner = Owner(); self.owners.append(owner); return owner
    def test_new_profile(self):
        owner = self.owner()
        self.assertTrue(automatic(owner.settings['tutorial']))
        open_tutorial(owner)
        self.assertEqual(load_settings()['tutorial']['status'], 'in_progress')
    def test_legacy_profile(self):
        for settings in ({}, {'ocr_engine': 'tesseract', 'custom_path': 'keep'}):
            save_settings(settings)
            self.assertFalse(automatic(initial_state(load_settings())))
            self.assertEqual(load_settings(), settings)
    def test_skip_restart(self):
        owner = self.owner(); open_tutorial(owner); owner.tutorial_dialog.skip()
        self.assertFalse(automatic(self.owner().settings['tutorial']))
        self.assertNotIn('setup_completed', load_settings())
    def test_resume_and_close(self):
        owner = self.owner(); open_tutorial(owner); owner.tutorial_dialog.move(1)
        owner.tutorial_dialog.close()
        other = self.owner(); open_tutorial(other)
        self.assertEqual(other.tutorial_dialog.step, 1)
    def test_complete_restart(self):
        owner = self.owner(); open_tutorial(owner)
        for _ in range(6): owner.tutorial_dialog.advance()
        self.assertEqual(load_settings()['tutorial']['status'], 'completed')
        self.assertFalse(automatic(self.owner().settings['tutorial']))
        self.assertNotIn('setup_completed', load_settings())
    def test_help_reopen(self):
        owner = self.owner(); persist(owner, 'completed', 5)
        open_tutorial(owner)
        self.assertEqual(owner.tutorial_dialog.step, 0)
        self.assertTrue(owner.tutorial_dialog.isVisible())
    def test_background_and_popup(self):
        state = self.owner().settings['tutorial']
        self.assertFalse(automatic(state, background=True))
        self.assertFalse(automatic(state, popup_only=True))
        self.assertFalse((Path(self.tmp.name)/'XDG_CONFIG_HOME/naatik-next/settings.json').exists())
    def test_save_failure(self):
        owner = self.owner(); persist(owner, 'in_progress', 1)
        with patch('naatik_next.tutorial.save_settings', side_effect=OSError('disk full')):
            self.assertFalse(persist(owner, 'completed', 5))
        self.assertEqual(owner.settings['tutorial']['step'], 1)
        self.assertEqual(load_settings()['tutorial']['step'], 1)
        self.assertIn('disk full', owner.errors[0])

    def test_window_startup_and_help_wiring(self):
        from naatik_next.app import Window
        for background, popup_only, expect in ((False, False, True), (True, False, False), (True, True, False)):
            with patch('naatik_next.app.QTimer.singleShot') as timer, patch.object(Window, 'ensure_tray'):
                window = Window(background=background, popup_only=popup_only)
            try:
                callbacks = [call.args[1] for call in timer.call_args_list if len(call.args) > 1]
                self.assertEqual(window.show_tutorial in callbacks, expect)
                menus = window.menuBar().actions()
                help_action = next(action for action in menus if action.text() == 'Ayuda')
                help_menu = help_action.menu()
                entries = help_menu.actions()
                entries[0].trigger()
                self.assertTrue(window.tutorial_dialog.isVisible())
            finally:
                window.shutdown()
                window.close()

    def test_preferences_and_resource_evidence_preserved(self):
        original = {'manga_model': '/explicit/model', 'ocr_engine': 'tesseract',
                    'resource_verified': False, 'translation_route': ['ja', 'en']}
        save_settings(original)
        owner = self.owner()
        for status in ('in_progress', 'skipped', 'completed'):
            self.assertTrue(persist(owner, status, 3))
            saved = load_settings()
            for key, value in original.items(): self.assertEqual(saved[key], value)
        self.assertNotIn('setup_completed', saved)

    def run_main_startup(self, args, progress=None):
        """Run real argument parsing and Window; isolate IPC and the event-loop owner."""
        from naatik_next.app import main, Window
        if progress is not None:
            save_settings({'tutorial': progress, 'manga_model': '/explicit/keep/model'})
        with patch('naatik_next.app.Instance') as instance_type, \
             patch('naatik_next.app.QApplication') as app_type, \
             patch('naatik_next.app.Window.prepare_selected'), \
             patch('naatik_next.app.logging.basicConfig'), \
             patch('naatik_next.app.RotatingFileHandler'), \
             patch('sys.argv', ['naatik-next', *args]):
            app = app_type.return_value
            app.platformName.return_value = 'offscreen'
            instance = instance_type.return_value
            instance.acquire_or_forward.return_value = True
            def event_loop():
                handler = instance.server.set_handler.call_args.args[0]
                window = handler.__self__
                self.assertIsInstance(window, Window)
                self.owners.append(window)
                # Drain actual zero-delay Qt callbacks, including automatic onboarding.
                APP.processEvents()
                APP.processEvents()
                if '--capture' in args:
                    self.assertTrue(window.pending_external_capture)
                    self.assertFalse(hasattr(window, 'tutorial_dialog'))
                    self.assertEqual(window.settings['tutorial'], progress or {'status': 'pending', 'step': 0})
                    if progress is not None:
                        self.assertEqual(load_settings()['tutorial'], progress)
                    menus = window.menuBar().actions()
                    action = next(item for item in menus if item.text() == 'Ayuda')
                    menu = action.menu()
                    entries = menu.actions()
                    entries[0].trigger()
                    self.assertTrue(window.tutorial_dialog.isVisible())
                    self.assertEqual(window.tutorial_dialog.step, progress['step'] if progress else 0)
                else:
                    self.assertTrue(window.tutorial_dialog.isVisible())
                return 0
            app.exec.side_effect = event_loop
            self.assertEqual(main(), 0)
            instance.acquire_or_forward.assert_called_once_with('capture' if '--capture' in args else 'show')

    def test_main_capture_new_profile_defers_tutorial_until_help(self):
        self.run_main_startup(['--capture'])

    def test_main_capture_preserves_saved_step_until_help(self):
        self.run_main_startup(['--capture'], {'status': 'in_progress', 'step': 3})
        self.assertEqual(load_settings()['manga_model'], '/explicit/keep/model')

    def test_main_normal_new_profile_opens_tutorial(self):
        self.run_main_startup([])

    def editor_window(self):
        from naatik_next.app import Window
        with patch('naatik_next.app.QTimer.singleShot'):
            window = Window(startup_action='capture')
        self.owners.append(window)
        window.show()
        # No translation/model startup probes while testing dictionary workers.
        window.startup_argos_started = True
        return window

    def test_ocr_automatic_lookup_missing_dictionaries_is_nonmodal(self):
        from tests.test_processes import spin_until
        window = self.editor_window()
        original_progress = window.settings['tutorial'].copy()
        with patch('naatik_next.app.QMessageBox.question') as question, \
             patch('naatik_next.app.QMessageBox.warning') as warning, \
             patch('naatik_next.app.QMessageBox.information') as information, \
             patch('naatik_next.app.QFileDialog.getOpenFileNames', return_value=([], '')) as import_zip:
            for generation in range(1, 4):
                window.ocr_pending = generation
                window.ocr_request_image = window.image_path
                window.recognized({'generation': generation, 'text': '日本'})
                spin_until(lambda: not window.dictionary_setup_btn.isHidden() and not window.selection_task.busy)
                self.assertIn('No hay diccionarios activos', window.selection_definitions.toPlainText())
                self.assertIn('Falta importar o activar', window.selection_hint.text())
                self.assertIs(window.tabs.currentWidget(), window.tabs.widget(0))
            question.assert_not_called(); warning.assert_not_called(); information.assert_not_called()
            import_zip.assert_not_called()
            window.dictionary_setup_btn.click()
            self.assertIs(window.tabs.currentWidget(), window.dictionary_tab)
            window.add_dict.click()
            import_zip.assert_called_once()
        self.assertEqual(window.settings['tutorial'], original_progress)

    def test_editor_selection_can_activate_dictionary_and_retry_real_worker(self):
        import json
        import zipfile
        from tests.test_storage import ROW
        from tests.test_processes import spin_until
        window = self.editor_window()
        archive = Path(self.tmp.name) / 'dictionary.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('index.json', json.dumps({'format': 3, 'title': 'Tutorial test', 'revision': '1'}))
            zipped.writestr('term_bank_1.json', json.dumps([ROW]))
        window.store.import_zip(archive)
        ident = window.store.list()[0]['id']
        window.store.update(ident, False, 0)
        window.editor.setPlainText('日本')
        window.editor.selectAll()
        window.selection_btn.click()
        spin_until(lambda: not window.dictionary_setup_btn.isHidden() and not window.selection_task.busy)
        window.dictionary_setup_btn.click()
        self.assertIs(window.tabs.currentWidget(), window.dictionary_tab)
        window.table.cellWidget(0, 4).setChecked(True)
        self.assertTrue(window.store.list()[0]['enabled'])
        window.tabs.setCurrentIndex(0)
        window.selection_btn.click()
        spin_until(lambda: 'Japan' in window.selection_definitions.toPlainText() and not window.selection_task.busy)
        self.assertTrue(window.dictionary_setup_btn.isHidden())
        self.assertNotIn('Falta importar', window.selection_hint.text())

    def test_skipped_step_resumes_from_help_and_explicit_restart(self):
        owner = self.owner(); open_tutorial(owner)
        owner.tutorial_dialog.move(3); owner.tutorial_dialog.skip()
        other = self.owner(); open_tutorial(other)
        self.assertEqual(other.tutorial_dialog.step, 3)
        other.tutorial_dialog.restart()
        self.assertEqual(load_settings()['tutorial'], {'status':'in_progress','step':0})
        self.assertNotIn('setup_completed', load_settings())
