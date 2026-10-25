"""Appearance uses isolated preferences and never executes sample content."""
import copy
import os
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtGui import QColor, QFontDatabase, QPalette
from naatik_next import appearance
from naatik_next.storage import load_settings
from naatik_next.app import Window
from naatik_next.processes import Task
from tests.test_processes import APP


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='next-appearance-')
        self.env=patch.dict(os.environ,{k:self.tmp.name+'/'+k for k in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')});self.env.start()
        self.start=patch.object(Task,'start');self.start.start()
        self.windows=[]
        self.w=self.window();self.section=self.w.appearance_section

    def window(self):
        with patch('naatik_next.app.QTimer.singleShot'):
            w=Window(background=True,popup_only=True)
        self.windows.append(w);return w

    def tearDown(self):
        for w in self.windows:w.close();w.deleteLater()
        APP.processEvents();self.start.stop();self.env.stop();self.tmp.cleanup()

    def popup(self,mode):
        self.w.external_command(mode)
        p=self.w.popups[mode];p.debounce.stop();p.editor.setPlainText('日本を読む。');p.debounce.stop()
        return p

    def test_preview_cancel_and_defaults_never_persist_or_change_live_text(self):
        p=self.popup('translator');style=p.styleSheet();original=self.w.palette().color(QPalette.Window).name()
        before=copy.deepcopy(load_settings())
        self.section.theme.setCurrentIndex(self.section.theme.findData('dark'))
        self.section.sizes['text_size'].setValue(26)
        self.assertEqual(self.section.preview.palette().color(QPalette.Window).name(),appearance.PRESETS['dark']['background'])
        self.assertEqual(p.styleSheet(),style);self.assertEqual(self.w.palette().color(QPalette.Window).name(),original)
        self.assertEqual(load_settings(),before);self.assertEqual(p.editor.toPlainText(),'日本を読む。')
        self.section.cancel();self.assertEqual(self.section.draft,self.section.saved)
        self.section.defaults();self.assertEqual(load_settings(),before)

    def test_save_applies_to_existing_and_future_popups_and_restart(self):
        p=self.popup('translator');revision=p.revision
        self.section.theme.setCurrentIndex(self.section.theme.findData('dark'))
        self.section.sizes['text_size'].setValue(25)
        self.section.sizes['ui_size'].setValue(14)
        self.section.draft['colors']['accent']='#f9a826';self.section.refresh()
        self.section.save()
        self.assertIn('font-size:25pt',p.styleSheet());self.assertIn('#f9a826',p.styleSheet())
        self.assertEqual(p.editor.toPlainText(),'日本を読む。');self.assertEqual(p.revision,revision)
        self.assertEqual(self.section.theme.font().pointSize(),14)
        self.section.ensurePolished()
        self.assertEqual(self.section.palette().color(QPalette.Window).name(),appearance.PRESETS['dark']['background'])
        self.section.color_buttons['text'].ensurePolished()
        future=self.popup('phrase');self.assertEqual(p.styleSheet(),future.styleSheet())
        saved=load_settings()['appearance'];self.assertEqual(saved['theme'],'dark');self.assertEqual(saved['text_size'],25)
        next_window=self.window();self.assertEqual(next_window.appearance_section.saved,saved)
        self.assertEqual(next_window.palette().color(QPalette.Window).name(),appearance.PRESETS['dark']['background'])
        self.section.defaults();self.section.cancel();self.assertEqual(self.section.draft,saved)

    def test_font_color_validation_missing_font_and_contrast(self):
        config=appearance.normalize(dict(theme='bad',ui_size=True,text_size=500,ui_font='bad\nfont',colors=dict(text='red',accent='#AABBCC',background='url(file:secret)')))
        self.assertEqual(config['theme'],'system');self.assertEqual(config['ui_size'],10)
        self.assertEqual(config['text_size'],40);self.assertEqual(config['ui_font'],'')
        self.assertEqual(config['colors'],{'accent':'#aabbcc'})
        self.section.draft['text_font']='Missing font for isolated appearance test'
        self.section.draft['colors']=dict(text='#ffffff',surface='#ffffff')
        self.section.refresh();self.assertIn('Contraste bajo',self.section.status.text());self.assertIn('Fuente no disponible',self.section.status.text())
        self.assertAlmostEqual(appearance.contrast('#000000','#ffffff'),21,places=2)
        font=QFontDatabase.families()[0]
        self.section.system_fonts['text_font'].setChecked(False)
        from PySide6.QtGui import QFont
        self.section.fonts['text_font'].setCurrentFont(QFont(font))
        self.assertEqual(self.section.draft['text_font'],font)

    def test_failed_save_retains_previous_settings_and_appearance(self):
        before=copy.deepcopy(self.w.settings);style=self.w.styleSheet()
        self.section.theme.setCurrentIndex(self.section.theme.findData('dark'))
        with patch('naatik_next.appearance_ui.save_settings',side_effect=OSError('test')):self.section.save()
        self.assertEqual(self.w.settings,before);self.assertEqual(self.w.styleSheet(),style)
        self.assertEqual(self.section.draft['theme'],'dark');self.assertIn('No se pudo guardar',self.section.status.text())

    def test_theme_and_color_reset_are_scoped_to_draft(self):
        self.section.draft['colors']['accent']='#ff0000';self.section.refresh()
        self.section.reset_color('accent');self.assertNotIn('accent',self.section.draft['colors'])
        with patch('naatik_next.appearance_ui.QColorDialog.getColor',return_value=QColor()):self.section.choose_color('text')
        self.assertNotIn('text',self.section.draft['colors'])
        with patch('naatik_next.appearance_ui.QColorDialog.getColor',return_value=QColor('#123456')):self.section.choose_color('text')
        self.assertEqual(self.section.draft['colors']['text'],'#123456')
        self.section.theme.setCurrentIndex(self.section.theme.findData('light'));self.assertEqual(self.section.draft['colors'],{})
        self.assertNotIn('appearance',load_settings())
