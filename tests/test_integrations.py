import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QMessageBox
from naatik_next.app import Window
from naatik_next.integrations import capture_script, write_capture_script
from naatik_next.storage import UserError
from tests.test_processes import APP


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {k: str(self.root / k) for k in
                       ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME')})
        self.env.start()
        with patch('naatik_next.app.QTimer.singleShot'):
            self.w = Window()

    def tearDown(self):
        self.w.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_script_special_paths_different_cwd_and_no_injection(self):
        folder = self.root / "con espacios '日本' $(touch DANGER); &"
        folder.mkdir()
        launcher = folder / "launch ' & $()"
        output = self.root / 'args'
        launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" "$XDG_CONFIG_HOME" > ' + __import__('shlex').quote(str(output)) + '\n')
        launcher.chmod(0o700)
        script = folder / "capturar ' $().sh"
        with patch('naatik_next.integrations.launcher_path', return_value=launcher):
            write_capture_script(script)
        self.assertTrue(os.access(script, os.X_OK))
        self.assertEqual(script.stat().st_mode & 0o777, 0o700)
        self.assertNotIn('while', script.read_text())
        subprocess.run([str(script)], cwd='/', env=dict(os.environ, XDG_CONFIG_HOME='/wrong-runner-profile'), check=True, timeout=5)
        self.assertEqual(output.read_text(), '--capture-copy\n' + os.environ['XDG_CONFIG_HOME'] + '\n')
        self.assertFalse((self.root / 'DANGER').exists())

    def test_existing_file_confirmation_gui_and_safe_overwrite(self):
        script = self.root / 'capture.sh'
        script.write_text('original')
        with self.assertRaises(FileExistsError):
            write_capture_script(script)
        with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(script), '')), patch('naatik_next.app.QMessageBox.question', return_value=QMessageBox.No) as confirm:
            self.w.create_stream_script()
            confirm.assert_called_once()
            self.assertEqual(script.read_text(), 'original')
        with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(script), '')), patch('naatik_next.app.QMessageBox.question', return_value=QMessageBox.Yes):
            self.w.create_stream_script()
        self.assertEqual(script.read_text(), capture_script())
        self.assertEqual(self.w.stream_script_path.text(), str(script))
        self.w.copy_stream_path()
        self.assertEqual(APP.clipboard().text(), str(script))
        with patch('naatik_next.app.QDesktopServices.openUrl', return_value=True) as opened:
            self.w.open_stream_folder()
            self.assertEqual(opened.call_args.args[0].toLocalFile(), str(self.root))
        self.w.close()
        with patch('naatik_next.app.QTimer.singleShot'):
            self.w = Window()
        self.assertEqual(self.w.stream_script_path.text(), str(script))

    def test_no_symlink_or_launcher_overwrite_and_cancel_file_dialog(self):
        original = self.root / 'original'
        original.write_text('keep')
        link = self.root / 'link.sh'
        link.symlink_to(original)
        with self.assertRaises(UserError):
            write_capture_script(link, overwrite=True)
        self.assertEqual(original.read_text(), 'keep')
        with patch('naatik_next.integrations.launcher_path', return_value=original):
            with self.assertRaises(UserError):
                write_capture_script(original, overwrite=True)
        with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=('', '')):
            self.w.create_stream_script()
        self.assertFalse(self.w.stream_script_path.text())

    def test_main_cold_and_open_routes_without_a_second_window(self):
        from naatik_next.app import main
        from unittest.mock import Mock
        for owner in (True, False):
            broker = Mock()
            broker.acquire_or_forward.return_value = owner
            application = Mock()
            application.exec.return_value = 0
            with patch('naatik_next.app.os.umask'), patch('naatik_next.app.RotatingFileHandler'), patch('naatik_next.app.logging.basicConfig'), patch('naatik_next.app.sys.argv', ['launch', '--capture']), patch('naatik_next.app.Instance', return_value=broker), patch('naatik_next.app.QApplication', return_value=application), patch('naatik_next.app.Window') as window:
                self.assertEqual(main(), 0)
                broker.acquire_or_forward.assert_called_once_with('capture')
                if owner:
                    window.assert_called_once()
                    window.return_value.external_command.assert_called_once_with('capture')
                    broker.server.set_handler.assert_called_once_with(window.return_value.external_command)
                else:
                    window.assert_not_called()
                    application.exec.assert_not_called()
                broker.close.assert_called_once()

    def test_startup_request_coalesced_until_all_initial_ocr_probes_finish(self):
        with patch.object(self.w, 'capture_and_recognize', return_value='accepted') as shared:
            self.assertEqual(self.w.external_command('capture'), 'queued')
            self.assertEqual(self.w.external_command('capture'), 'queued')
            self.w.flush_external_capture()
            shared.assert_not_called()
            self.w.startup_detection_started = True
            self.w.detect_task.busy = True
            self.w.flush_external_capture()
            shared.assert_not_called()
            self.w.detect_task.busy = False
            self.w.manga_task.busy = True
            self.w.manga_action = 'detect'
            self.w.flush_external_capture()
            shared.assert_not_called()
            self.w.manga_task.busy = False
            self.w.flush_external_capture()
            shared.assert_called_once()
            self.assertFalse(self.w.pending_external_capture)
            self.assertEqual(self.w.external_command('capture'), 'accepted')
            self.assertEqual(shared.call_count, 2)

    def test_hotkey_and_remote_use_same_action_and_cancel_drops_queued(self):
        self.w.startup_detection_started = True
        with patch.object(self.w, 'isActiveWindow', return_value=False), patch.object(self.w, 'capture_and_recognize', return_value='accepted') as shared:
            self.w.shortcut.activated.emit()
            self.w.external_command('capture')
            self.assertEqual(shared.call_count, 2)
        self.w.startup_detection_started = False
        self.w.external_command('capture')
        self.w.cancel()
        self.assertFalse(self.w.pending_external_capture)
        self.w.startup_detection_started = True
        with patch.object(self.w, 'capture_and_recognize') as shared:
            self.w.flush_external_capture()
            shared.assert_not_called()

    def test_not_ready_visible_warning_and_repeat_cancel_new_request(self):
        self.w.startup_detection_started = True
        with patch.object(self.w, 'fail') as fail:
            self.assertEqual(self.w.external_command('capture'), 'unavailable')
            fail.assert_called_once()
        self.w.detected([{'id': 'tesseract', 'name': 'Tesseract', 'status': 'listo',
                         'detail': 'UI fixture only', 'languages': ['jpn']}])
        self.assertEqual(self.w.external_command('capture'), 'accepted')
        self.assertEqual(self.w.external_command('capture'), 'ignored')
        self.w.cancel()  # Before launching Spectacle, preserving previous content.
        self.assertFalse(self.w.capture_active)
        self.assertEqual(self.w.external_command('capture'), 'accepted')
        self.w.cancel()
        self.w.ocr_task.busy = True
        self.assertEqual(self.w.external_command('capture'), 'ignored')
        self.w.ocr_task.busy = False
        self.w.capture()  # Existing button remains capture-only.
        self.assertFalse(self.w.capture_auto_ocr)
        self.w.cancel()

    def test_three_generated_scripts_and_commands_preserve_action_and_xdg(self):
        from naatik_next.integrations import write_action_script,action_command,ACTIONS
        import shlex
        folder=self.root/"space '日本' $() % back\\slash";folder.mkdir()
        launcher=folder/'launch';output=self.root/'output'
        launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" "$XDG_CONFIG_HOME" > '+shlex.quote(str(output))+'\n')
        launcher.chmod(0o700)
        with patch('naatik_next.integrations.launcher_path',return_value=launcher):
            for action in ACTIONS:
                script=write_action_script(folder/(action+'.sh'),action)
                for args in ([str(script)],['/bin/sh','-c',action_command(action)]):
                    subprocess.run(args,cwd='/',env=dict(os.environ,XDG_CONFIG_HOME='/wrong'),check=True,timeout=5)
                    self.assertEqual(output.read_text(),'--'+action+'\n'+os.environ['XDG_CONFIG_HOME']+'\n')
                with self.assertRaises(FileExistsError):write_action_script(script,action)

    def test_desktop_exec_with_system_gio_and_literal_special_paths(self):
        from naatik_next.integrations import write_action_desktop,ACTIONS
        import shlex,shutil
        check=subprocess.run(['/usr/bin/python3','-c','import gi; from gi.repository import Gio'],capture_output=True)
        if check.returncode:self.skipTest('System Gio validation tool unavailable')
        folder=self.root/"space '日本' $() % back\\slash";folder.mkdir()
        launcher=folder/'launch';output=self.root/'desktop-output'
        launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" "$XDG_CONFIG_HOME" > '+shlex.quote(str(output))+'\n')
        launcher.chmod(0o700)
        with patch('naatik_next.integrations.launcher_path',return_value=launcher):
            for action in ACTIONS:
                output.unlink(missing_ok=True)
                path=write_action_desktop(folder/(action+'.desktop'),action)
                if shutil.which('desktop-file-validate'):
                    subprocess.run(['desktop-file-validate',str(path)],check=True,capture_output=True)
                code='from gi.repository import Gio; import sys; app=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]); assert app; assert app.launch([],None)'
                subprocess.run(['/usr/bin/python3','-c',code,str(path)],check=True,capture_output=True,timeout=5)
                from tests.test_processes import spin_until
                spin_until(lambda:output.exists() and bool(output.read_text()))
                self.assertEqual(output.read_text(),'--'+action+'\n'+os.environ['XDG_CONFIG_HOME']+'\n')
                with self.assertRaises(FileExistsError):write_action_desktop(path,action)

    def test_popup_launcher_owner_or_client_does_not_show_main(self):
        from naatik_next.app import main
        from unittest.mock import Mock
        for action in ('translator','phrase'):
            for owner in (True,False):
                broker=Mock();broker.acquire_or_forward.return_value=owner
                application=Mock();application.exec.return_value=0
                with patch('naatik_next.app.os.umask'),patch('naatik_next.app.RotatingFileHandler'),patch('naatik_next.app.logging.basicConfig'), \
                        patch('naatik_next.app.QApplication',return_value=application),patch('naatik_next.app.Instance',return_value=broker), \
                        patch('naatik_next.app.Window') as window, patch('sys.argv',['launch','--'+action]):
                    self.assertEqual(main(),0)
                    broker.acquire_or_forward.assert_called_once_with(action)
                    if owner:
                        window.assert_called_once_with(background=True,popup_only=True)
                        window.return_value.show.assert_not_called()
                        window.return_value.external_command.assert_called_once_with(action)
                    else:window.assert_not_called()

    def test_each_popup_script_gui_refuses_overwrite_and_saves_separately(self):
        from naatik_next.integrations import action_script
        for action in ('translator','phrase'):
            path=self.root/(action+'.sh');path.write_text('keep')
            with patch('naatik_next.app.QFileDialog.getSaveFileName',return_value=(str(path),'')), \
                    patch('naatik_next.app.QMessageBox.question',return_value=QMessageBox.No):
                self.w.create_action_script(action)
            self.assertEqual(path.read_text(),'keep')
            with patch('naatik_next.app.QFileDialog.getSaveFileName',return_value=(str(path),'')), \
                    patch('naatik_next.app.QMessageBox.question',return_value=QMessageBox.Yes):
                self.w.create_action_script(action)
            self.assertEqual(path.read_text(),action_script(action))
            self.assertEqual(self.w.settings[action+'_script'],str(path))
        self.assertFalse(self.w.settings.get('stream_deck_script'))

    def test_integration_buttons_dispatch_their_own_action_with_qt_checked_argument(self):
        from PySide6.QtWidgets import QGroupBox,QPushButton
        from naatik_next.integrations import ACTIONS,action_script
        group=next(g for g in self.w.findChildren(QGroupBox) if g.title()=='Script y acceso directo')
        buttons={b.text():b for b in group.findChildren(QPushButton)}
        for action,title in ACTIONS.items():
            self.w.integration_action.setCurrentIndex(self.w.integration_action.findData(action))
            path=self.root/(action+'.sh')
            with patch('naatik_next.app.QFileDialog.getSaveFileName',return_value=(str(path),'')):
                buttons['Crear script…'].click()
            self.assertEqual(path.read_text(),action_script(action))
            buttons['Copiar ruta'].click()
            self.assertEqual(APP.clipboard().text(),str(path))
            buttons['Copiar comando'].click()
            self.assertEqual(APP.clipboard().text(),self.w.integration_fields[action]['command'].toPlainText())
            with patch('naatik_next.app.QDesktopServices.openUrl',return_value=True) as opened:
                buttons['Abrir carpeta'].click()
                self.assertEqual(opened.call_args.args[0].toLocalFile(),str(self.root))
            desktop=self.root/(action+'.desktop')
            with patch('naatik_next.app.QFileDialog.getSaveFileName',return_value=(str(desktop),'')):
                buttons['Crear acceso directo…'].click()
            self.assertIn(' --'+action,desktop.read_text())

    def test_selector_keeps_paths_commands_drafts_and_desktops_independent(self):
        from PySide6.QtGui import QKeySequence
        from naatik_next.integrations import ACTIONS, action_command
        from naatik_next.storage import load_settings
        from PySide6.QtWidgets import QKeySequenceEdit
        expected = {}
        for index, action in enumerate(ACTIONS):
            self.w.integration_action.setCurrentIndex(index)
            path = self.root / (action+" '日本' $().sh")
            with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(path), '')):
                self.w.create_action_script(action)
            desktop = self.root / (action+'.desktop')
            with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(desktop), '')):
                self.w.create_action_desktop(action)
            self.w.action_shortcut_fields[action].setKeySequence(QKeySequence('Ctrl+Alt+'+str(index+1)))
            expected[action] = (str(path), __import__('shlex').quote(str(path)), desktop)
        saved = load_settings()
        with patch('naatik_next.hotkey.GlobalShortcut.register') as register:
            for index, action in reversed(list(enumerate(ACTIONS))):
                self.w.integration_action.setCurrentIndex(index)
                self.assertEqual(self.w.shortcut_pages.currentIndex(), index)
                self.assertEqual(self.w.script_pages.currentIndex(), index)
                self.assertEqual(self.w.command_pages.currentIndex(), index)
                path, command, desktop = expected[action]
                self.assertEqual(self.w.integration_fields[action]['path'].text(), path)
                self.w.copy_integration_command(); self.assertEqual(APP.clipboard().text(), command)
                self.w.copy_integration_path(); self.assertEqual(APP.clipboard().text(), path)
                self.assertIn(str(desktop), self.w.integration_fields[action]['desktop'].text())
                self.assertEqual(self.w.action_shortcut_fields[action].keySequence().toString(), 'Ctrl+Alt+'+str(index+1))
            register.assert_not_called()
        self.assertEqual(load_settings(), saved)  # Selecting/drafting never writes settings.
        self.assertEqual(self.w.tabs.count(), 8)
        self.assertEqual(len(self.w.integrations_tab.findChildren(QKeySequenceEdit)), 5)
        prefs = self.w.tabs.widget(next(i for i in range(self.w.tabs.count()) if self.w.tabs.tabText(i)=='Preferencias y diagnóstico'))
        self.assertFalse(prefs.findChildren(QKeySequenceEdit))
        self.w.close()
        with patch('naatik_next.app.QTimer.singleShot'): self.w = Window()
        for action, (path, command, desktop) in expected.items():
            self.assertEqual(self.w.integration_fields[action]['path'].text(), path)
            self.assertIn(str(desktop), self.w.integration_fields[action]['desktop'].text())
            self.assertEqual(self.w.integration_fields[action]['command'].toPlainText(), command)
            self.assertTrue(Path(path).exists())

    def test_details_hidden_but_copy_command_includes_complete_profile(self):
        from PySide6.QtWidgets import QGroupBox
        self.w.tabs.setCurrentWidget(self.w.integrations_tab); self.w.show(); APP.processEvents()
        details = next(g for g in self.w.findChildren(QGroupBox) if g.title()=='Detalles')
        self.assertFalse(details.isChecked())
        for index in range(4):
            self.w.integration_action.setCurrentIndex(index)
            command = self.w.integration_fields[self.w.integration_action.currentData()]['command']
            self.assertFalse(command.isVisible())
            self.w.copy_integration_command()
            self.assertIn('XDG_CONFIG_HOME=', APP.clipboard().text())
            self.assertIn('XDG_DATA_HOME=', APP.clipboard().text())
            self.assertIn('XDG_STATE_HOME=', APP.clipboard().text())
            self.assertIn('XDG_CACHE_HOME=', APP.clipboard().text())
        details.setChecked(True); APP.processEvents(); self.assertTrue(command.isVisible())

    def test_show_cli_forwards_main_window_instead_of_creating_popup(self):
        from naatik_next.app import main
        from unittest.mock import Mock
        broker = Mock(); broker.acquire_or_forward.return_value = False
        with patch('naatik_next.app.os.umask'), patch('naatik_next.app.RotatingFileHandler'), \
             patch('naatik_next.app.logging.basicConfig'), patch('naatik_next.app.QApplication'), \
             patch('naatik_next.app.Instance', return_value=broker), patch('sys.argv', ['launch','--show']):
            self.assertEqual(main(), 0)
        broker.acquire_or_forward.assert_called_once_with('show')

    def test_copied_script_command_executes_literal_path_and_profile(self):
        import shlex
        folder = self.root / "copy '日本' $(touch BAD) &"; folder.mkdir()
        launcher = folder/'fake launch'; result = self.root/'copied-result'
        launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" "$XDG_CONFIG_HOME" > '+shlex.quote(str(result))+'\n')
        launcher.chmod(0o700)
        for action in ('capture-copy','translator','phrase','show'):
            self.w.integration_action.setCurrentIndex(self.w.integration_action.findData(action))
            script = folder/(action+" 'script'.sh")
            with patch('naatik_next.integrations.launcher_path', return_value=launcher), \
                 patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(script), '')):
                self.w.create_action_script(action)
            self.w.copy_integration_command()
            subprocess.run(['/bin/sh','-c',APP.clipboard().text()], cwd='/', env=dict(os.environ,XDG_CONFIG_HOME='/wrong'), check=True, timeout=5)
            self.assertEqual(result.read_text(), '--'+action+'\n'+os.environ['XDG_CONFIG_HOME']+'\n')
        self.assertFalse((self.root/'BAD').exists())

    def test_files_appearing_after_dialog_are_not_silently_overwritten(self):
        for action in ('capture-copy','translator','phrase','show'):
            for kind in ('script','desktop'):
                path = self.root/(action+'.'+kind)
                def appears(filename):
                    Path(filename).write_text('created concurrently')
                    return True
                with patch('naatik_next.app.QFileDialog.getSaveFileName', return_value=(str(path), '')), \
                     patch.object(self.w, 'confirm_integration_overwrite', side_effect=appears):
                    getattr(self.w, 'create_action_'+kind)(action)
                self.assertEqual(path.read_text(), 'created concurrently')
                self.assertIn('No se creó', self.w.integration_fields[action]['status'].text())
