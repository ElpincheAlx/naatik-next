"""Bilingual journeys with fresh XDG roots; no user's installation/profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLabel
from naatik_next.i18n import CATALOGS, set_language, t
from naatik_next.install_language import persist, select
from naatik_next.storage import load_settings, save_settings
from tests.test_processes import APP, spin_until


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {key:str(self.root/key) for key in
            ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME')})
        self.env.start(); set_language('es'); self.windows = []
    def tearDown(self):
        for window in self.windows: window.shutdown(); window.close()
        set_language('es'); self.env.stop(); self.tmp.cleanup()
    def window(self):
        from naatik_next.app import Window
        with patch('naatik_next.app.QTimer.singleShot'):
            window = Window(startup_action='capture')
        self.windows.append(window)
        return window
    def test_cancel_before_install_writes_nothing(self):
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='c'):
            self.assertIsNone(select())
        self.assertEqual(list(self.root.iterdir()), [])
    def test_choose_before_install_and_noninteractive_requires_choice(self):
        with patch('sys.stdin.isatty', return_value=False): self.assertIsNone(select())
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='2'):
            self.assertEqual(select(), 'en')
        self.assertEqual(list(self.root.iterdir()), [])
    def test_install_and_update_preserve_all_preferences(self):
        persist('en')
        settings = load_settings()
        self.assertEqual(settings['tutorial'], {'status':'pending', 'step':0})
        settings.update(manga_model='/explicit/model', manga_python='/explicit/python', ocr_language='jpn_vert',
                        translation_route=['ja', 'en', 'es'], anki={'deck':'keep'}, appearance={'theme':'dark'})
        save_settings(settings)
        with patch('sys.stdin.isatty', return_value=False): self.assertEqual(select(), 'en')
        persist('en'); self.assertEqual(load_settings(), settings)
        persist('es'); settings['ui_language']='es'; self.assertEqual(load_settings(), settings)
    def test_empty_legacy_install_never_marks_tutorial_pending(self):
        save_settings({}); persist('en'); self.assertNotIn('tutorial', load_settings())
        from naatik_next.tutorial import initial_state
        self.assertEqual(initial_state(load_settings())['status'], 'skipped')
    def test_both_languages_persist_and_reopen(self):
        for code, title, menu in [('en','local OCR and translation','Settings'),('es','OCR y traducción local','Configuración')]:
            persist(code)
            window=self.window()
            self.assertIn(title, window.windowTitle())
            self.assertIn(menu, [action.text() for action in window.menuBar().actions()])
            window.show_tutorial()
            self.assertEqual(window.tutorial_dialog.text.text(), t(__import__('naatik_next.tutorial',fromlist=['STEPS']).STEPS[0][1]))
            self.assertEqual(load_settings()['ui_language'],code)
    def test_switch_preserves_editor_selection_resources_and_progress(self):
        window=self.window(); window.editor.setPlainText('Texto del usuario — 日本'); window.editor.selectAll()
        window.show_tutorial(); window.tutorial_dialog.move(2)
        previous=dict(window.settings)
        with patch('naatik_next.i18n.choose_language', return_value='en'): window.choose_language()
        self.assertEqual(window.editor.toPlainText(),'Texto del usuario — 日本')
        self.assertEqual(window.selected_term(),'Texto del usuario — 日本')
        self.assertEqual(window.settings,dict(previous,ui_language='en'))
        self.assertEqual(window.tabs.tabText(0),'Capture and result')
        self.assertEqual(window.tutorial_dialog.text.text(),t(__import__('naatik_next.tutorial',fromlist=['STEPS']).STEPS[2][1]))
        with patch('naatik_next.i18n.choose_language', return_value=None): window.choose_language()
        self.assertEqual(load_settings()['ui_language'],'en')
        with patch('naatik_next.i18n.choose_language', return_value='es'): window.choose_language()
        self.assertEqual(window.tabs.tabText(0),'Captura y resultado')
    def test_live_worker_uses_new_language_without_restart(self):
        window=self.window(); errors=[]
        from naatik_next.processes import Task
        task=Task(window,persistent=True); window.tasks.append(task);task.error.connect(errors.append)
        for code in ('en','es'):
            set_language(code)
            task.start({'action':'does-not-exist'})
            spin_until(lambda:not task.busy)
            self.assertEqual(errors[-1],t('Operación desconocida.'))

    def test_cancel_uses_language_at_action_time(self):
        from naatik_next.processes import Task
        task = Task()
        errors = []
        task.error.connect(errors.append)
        try:
            for code in ('en', 'es', 'en'):
                set_language(code)
                task.busy = True
                task.cancel_reason = None
                task.cancel()
                self.assertEqual(errors[-1], t('Operación cancelada.'))
        finally:
            task.close()

    def test_capture_cancellation_stays_nonmodal_in_both_languages(self):
        window = self.window()
        window.editor.setPlainText('Keep edited text — 日本')
        for code in ('en', 'es'):
            set_language(code)
            with patch('naatik_next.app.QMessageBox.warning') as warning, patch('naatik_next.app.timings.event') as event:
                window.capture_failed(t('Selección cancelada o Spectacle no produjo una imagen.'))
                warning.assert_not_called()
                event.assert_called_once_with('cancelled', window.capture_trace)
            self.assertEqual(window.editor.toPlainText(), 'Keep edited text — 日本')
    def test_catalogs_have_same_keys_and_tutorial_is_translated(self):
        self.assertEqual(set(CATALOGS['en']),set(CATALOGS['es']))
        from naatik_next.tutorial import STEPS
        for title,body in STEPS:
            self.assertIn(title,CATALOGS['en']); self.assertIn(body,CATALOGS['en'])
            if title!='OCR':self.assertNotEqual(CATALOGS['en'][title],CATALOGS['es'][title])
    def test_shell_language_gate_precedes_venv_and_pip(self):
        import shutil
        root=Path(__file__).resolve().parents[1]
        copy=self.root/'install copy';copy.mkdir()
        shutil.copytree(root/'naatik_next',copy/'naatik_next',ignore=shutil.ignore_patterns('__pycache__'))
        (copy/'tools').mkdir();shutil.copy2(root/'tools/install.sh',copy/'tools/install.sh')
        environment=dict(os.environ,NAATIK_NEXT_UI_LANGUAGE='',NAATIK_NEXT_PYTHON=sys.executable)
        environment.pop('PYTHONDONTWRITEBYTECODE',None)
        result=subprocess.run(['bash',str(copy/'tools/install.sh')],env=environment,input='',capture_output=True,text=True,timeout=5)
        # Empty/absent environment choice is an interactive gate, never a download.
        self.assertEqual(result.returncode,130,result.stderr)
        self.assertFalse((copy/'.venv').exists())
        self.assertFalse((self.root/'XDG_CONFIG_HOME').exists())
        self.assertFalse(list(copy.rglob('__pycache__')))

    def test_english_dictionary_absence_activation_and_retry(self):
        import zipfile
        from tests.test_storage import ROW
        persist('en'); window=self.window()
        window.editor.setPlainText('日本'); window.editor.selectAll()
        with patch('naatik_next.app.QMessageBox.question') as question, patch('naatik_next.app.QMessageBox.warning') as warning:
            window.lookup_selection();spin_until(lambda:not window.selection_task.busy)
            self.assertIn('No dictionaries are active',window.selection_definitions.toPlainText())
            self.assertFalse(window.dictionary_setup_btn.isHidden())
            self.assertEqual(window.dictionary_setup_btn.text(),'Import or enable dictionaries…')
            archive=self.root/'test.zip'
            with zipfile.ZipFile(archive,'w') as zipped:
                zipped.writestr('index.json',json.dumps({'format':3,'title':'Fixture','revision':'1'}))
                zipped.writestr('term_bank_1.json',json.dumps([ROW]))
            window.store.import_zip(archive)
            ident=window.store.list()[0]['id'];window.store.update(ident,False,0)
            window.open_dictionary_configuration();window.table.cellWidget(0,4).setChecked(True)
            window.tabs.setCurrentIndex(0);window.lookup_selection();spin_until(lambda:not window.selection_task.busy)
            self.assertIn('Japan',window.selection_definitions.toPlainText())
            self.assertTrue(window.dictionary_setup_btn.isHidden())
            question.assert_not_called();warning.assert_not_called()

    def test_real_terminal_cancel_does_not_create_profile_or_environment(self):
        import pty
        import shutil
        root=Path(__file__).resolve().parents[1]
        copy=self.root/'terminal install';copy.mkdir()
        shutil.copytree(root/'naatik_next',copy/'naatik_next',ignore=shutil.ignore_patterns('__pycache__'))
        (copy/'tools').mkdir();shutil.copy2(root/'tools/install.sh',copy/'tools/install.sh')
        environment=dict(os.environ,NAATIK_NEXT_UI_LANGUAGE='',NAATIK_NEXT_PYTHON=sys.executable)
        environment.pop('PYTHONDONTWRITEBYTECODE',None)
        master,slave=pty.openpty()
        try:
            process=subprocess.Popen(['bash',str(copy/'tools/install.sh')],stdin=slave,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env=environment)
            os.close(slave);slave=None
            os.write(master,b'c\n')
            output,error=process.communicate(timeout=5)
            self.assertEqual(process.returncode,130,error)
            self.assertIn(b'Idioma / Language',error)
            self.assertFalse((copy/'.venv').exists())
            self.assertFalse((self.root/'XDG_CONFIG_HOME').exists())
            self.assertFalse(list(copy.rglob('__pycache__')))
        finally:
            os.close(master)
            if slave is not None:os.close(slave)
