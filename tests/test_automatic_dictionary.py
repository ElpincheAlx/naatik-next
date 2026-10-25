"""Injected OCR completion with real dictionary worker/SQLite and Qt offscreen."""
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from tests import test_selection_lookup as fixtures
from tests.test_processes import spin_until


class AutomaticDictionaryTests(unittest.TestCase):
    setUp = fixtures.SelectionTests.setUp
    tearDown = fixtures.SelectionTests.tearDown
    import_dictionary = fixtures.SelectionTests.import_dictionary
    select = fixtures.SelectionTests.select

    def complete_ocr(self, text):
        self.w.image_path = self.w.ocr_request_image = 'fixture'
        self.w.ocr_generation += 1
        self.w.ocr_pending = self.w.ocr_generation
        self.w.recognized({'generation': self.w.ocr_pending, 'text': text})

    def wait_lookup(self):
        spin_until(lambda: not self.w.selection_task.busy and self.w.selection_pending is None)
        return self.w.selection_definitions.toPlainText()

    def test_ocr_copies_and_queries_active_dictionaries_in_priority_order(self):
        low = self.import_dictionary('Low', 1)
        self.import_dictionary('High', 10)
        disabled = self.import_dictionary('Disabled', 100)
        self.w.store.update(disabled, False, 100)
        self.complete_ocr('日本')
        self.assertFalse(self.w.editor.textCursor().hasSelection())
        text = self.wait_lookup()
        self.assertLess(text.index('High'), text.index('Low'))
        self.assertNotIn('Disabled', text)
        self.assertEqual(QApplication.clipboard().text(), '日本')
        self.assertEqual(self.w.statusBar().currentMessage(), 'Texto reconocido y copiado')
        self.assertEqual(self.w.raw_text, '日本')
        self.assertEqual(self.w.editor.toPlainText(), '日本')
        # Existing OCR behavior clears an earlier translation, definitions stay separate.
        self.assertEqual(self.w.translation.toPlainText(), '')
        self.w.store.update(low, False, 1)
        self.w.auto_copy.setChecked(False)
        QApplication.clipboard().setText('sentinel')
        self.complete_ocr('日本')
        self.assertNotIn('Low', self.wait_lookup())
        self.assertEqual(QApplication.clipboard().text(), 'sentinel')

    def test_no_active_and_exact_phrase_without_segmentation(self):
        self.complete_ocr('日本')
        self.assertIn('No hay diccionarios activos', self.wait_lookup())
        self.import_dictionary('Dictionary')
        self.complete_ocr('日本 の 文')
        self.assertIn('Sin coincidencias exactas', self.wait_lookup())
        self.assertEqual(self.w.selection_query_term, '日本 の 文')
        self.complete_ocr(' 日本 ')
        self.assertIn('Sin coincidencias exactas', self.wait_lookup())

    def test_stale_lookup_cancel_empty_and_failure_do_not_chain_old_text(self):
        def answer(request, title):
            return dict(generation=request['generation'], term=request['term'], active=1,
                        results=[dict(title=title, expression=request['term'], reading='', meanings='["value"]')])
        with patch.object(self.w.selection_task, 'start') as start, patch.object(self.w, 'fail'):
            self.complete_ocr('old')
            old = start.call_args.args[0]
            self.complete_ocr('new')
            new = start.call_args.args[0]
            self.w.selection_result(answer(new, 'NEW'))
            self.w.selection_result(answer(old, 'OLD'))
            self.assertIn('NEW', self.w.selection_definitions.toPlainText())
            self.assertNotIn('OLD', self.w.selection_definitions.toPlainText())
            self.w.cancel()
            self.w.selection_result(answer(new, 'CANCELLED'))
            self.assertNotIn('CANCELLED', self.w.selection_definitions.toPlainText())
            count = start.call_count
            QApplication.clipboard().setText('sentinel')
            self.complete_ocr(' \n')
            self.assertEqual(start.call_count, count)
            self.w.ocr_pending = 99
            self.w.invalidate_ocr('OCR failed')
            self.w.recognized({'generation': 99, 'text': 'late OCR'})
            self.assertEqual(start.call_count, count)
            self.assertEqual(QApplication.clipboard().text(), 'sentinel')

    def test_new_capture_invalidates_old_lookup_before_ocr_completes(self):
        self.w.detected([dict(id='tesseract', name='Tesseract', status='listo', languages=['jpn'], detail='fixture')])
        with patch.object(self.w.selection_task, 'start') as start:
            self.complete_ocr('old')
            old = start.call_args.args[0]
            self.w.capture_btn.click()
            self.w.capture_delay.stop()
            self.w.selection_result(dict(generation=old['generation'], term='old', active=0, results=[]))
            self.assertNotIn('No hay diccionarios activos', self.w.selection_definitions.toPlainText())
            self.w.cancel()

    def test_manual_selection_still_works_after_automatic_lookup(self):
        self.import_dictionary('Dictionary')
        self.complete_ocr('日本 の 文')
        self.wait_lookup()
        self.select('日本')
        self.w.lookup_selection()
        self.assertIn('Dictionary', self.wait_lookup())

    def test_cancelled_and_invalid_capture_never_query_previous_ocr(self):
        self.w.detected([dict(id='tesseract', name='Tesseract', status='listo', languages=['jpn'], detail='fixture')])
        self.w.editor.setPlainText(self.w.raw_text)
        QApplication.clipboard().setText('sentinel')
        with patch.object(self.w.selection_task, 'start') as lookup, \
                patch('naatik_next.app.QMessageBox.warning'):
            self.w.capture_btn.click()
            self.w.cancel()
            self.w.captured('')
            self.w.capture_btn.click()
            self.w.capture_delay.stop()
            self.w.captured('')
            lookup.assert_not_called()
            self.assertEqual(QApplication.clipboard().text(), 'sentinel')
            self.assertEqual(self.w.raw_text, '原文')

    def test_busy_lookup_coalesces_latest_ocr_and_discards_old_answer(self):
        with patch.object(self.w.selection_task, 'start') as start:
            self.complete_ocr('first')
            first = start.call_args.args[0]
            self.w.selection_task.busy = True
            self.complete_ocr('second')
            self.complete_ocr('latest')
            self.assertEqual(start.call_count, 1)
            self.w.selection_task.busy = False
            self.w.selection_result(dict(generation=first['generation'], term='first', active=0, results=[]))
            self.assertEqual(start.call_count, 2)
            self.assertEqual(start.call_args.args[0]['term'], 'latest')
            self.assertNotIn('No hay diccionarios activos', self.w.selection_definitions.toPlainText())
