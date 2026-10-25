import unittest
from unittest.mock import patch
from naatik_next.ocr import Tesseract, UnsupportedPythonOCR
from naatik_next.translation import Argos
from naatik_next.storage import UserError
from naatik_next.i18n import t
import re


class AdapterTests(unittest.TestCase):
    def test_command_presence_is_not_ready(self):
        with patch('naatik_next.ocr.shutil.which', return_value='/test/tesseract'), patch('naatik_next.ocr.run', return_value='something else'):
            self.assertEqual(Tesseract().detect()['status'], 'incompatible')
        with patch('naatik_next.ocr.shutil.which', return_value='/test/tesseract'), patch('naatik_next.ocr.run', side_effect=UserError('probe failed')):
            self.assertEqual(Tesseract().detect()['status'], 'error')
        with patch('naatik_next.ocr.shutil.which', return_value=None):
            self.assertEqual(Tesseract().detect()['status'], 'recursos faltantes')

    def test_unsupported_does_not_import_or_execute_engine(self):
        with patch('naatik_next.ocr.importlib.util.find_spec', return_value=object()), patch('naatik_next.ocr.subprocess.Popen') as popen:
            result = UnsupportedPythonOCR('paddleocr', 'paddleocr', 'PaddleOCR').detect()
            self.assertEqual(result['status'], 'incompatible')
            popen.assert_not_called()

    def test_translation_rejects_missing_route_and_oversize(self):
        engine = Argos()
        with self.assertRaisesRegex(UserError, re.escape(t('La ruta elegida ya no está disponible. Abre Preparar traducción para reparar la ruta.'))):
            engine.translate('Hello', ['en', 'es'])
        with self.assertRaisesRegex(UserError, re.escape(t('Máximo 10 000 caracteres y 1 000 por línea. Divide el texto.'))):
            engine.translate('a' * 1001, ['en', 'es'])
