"""Resource guidance without network, model installation or real inference."""
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget
from naatik_next.setup_dialog import SetupDialog


class GuidedSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.owner = QWidget()
        self.owner.engines = []
        self.owner.settings = dict(manga_python='/missing/python', manga_model='/missing/model')
        self.owner.tabs = QTabWidget(self.owner)
        for title in ('Captura y resultado', 'Diccionarios', 'Traducción'):
            self.owner.tabs.addTab(QWidget(), title)
        self.dialog = SetupDialog(self.owner)

    def tearDown(self):
        self.dialog.close()
        self.owner.close()

    def test_engine_selection_guides_only_relevant_resources(self):
        self.assertTrue(self.dialog.manga_controls.isHidden())
        self.assertTrue(self.dialog.language.isEnabled())
        self.dialog.engine.setCurrentIndex(1)
        self.assertFalse(self.dialog.manga_controls.isHidden())
        self.assertFalse(self.dialog.language.isEnabled())
        self.assertIn('1. Prepara', self.dialog.guide.text())

    def test_missing_selected_language_is_not_presented_as_ready(self):
        self.dialog.probed([dict(id='tesseract', status='listo', languages=['eng'], detail='Prueba con eng')])
        self.assertTrue(self.dialog.status.toPlainText().startswith('Requiere atención: faltan los datos del idioma elegido'))

    def test_resource_navigation_does_not_save_or_download(self):
        before = dict(self.owner.settings)
        with patch.object(self.dialog.task, 'start') as start:
            self.dialog.open_resource('Traducción')
            start.assert_not_called()
        self.assertEqual(self.owner.tabs.currentIndex(), 2)
        self.assertEqual(self.owner.settings, before)

    def test_busy_preparation_keeps_navigation_in_place(self):
        with patch.object(self.dialog, 'idle', return_value=False):
            self.dialog.open_resource('Diccionarios')
        self.assertEqual(self.owner.tabs.currentIndex(), 0)
