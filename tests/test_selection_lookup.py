import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PySide6.QtGui import QTextCursor
from naatik_next.app import Window
from tests.test_processes import APP, spin_until
from tests.test_storage import ROW


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {k: self.tmp.name + '/' + k for k in
                                          ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME')})
        self.env.start()
        with patch('naatik_next.app.QTimer.singleShot'):
            self.w = Window()
        self.w.raw_text = '原文'
        self.w.translation.setPlainText('Argos sentinel')

    def tearDown(self):
        self.w.close()
        self.env.stop()
        self.tmp.cleanup()

    def select(self, text):
        self.w.editor.setPlainText(text)
        self.w.editor.selectAll()
        APP.processEvents()

    def import_dictionary(self, title, priority=0):
        path = Path(self.tmp.name) / (title + '.zip')
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('index.json', json.dumps({'format': 3, 'title': title, 'revision': '1'}))
            z.writestr('term_bank_1.json', json.dumps([ROW]))
        self.w.store.import_zip(path)
        ident = next(d['id'] for d in self.w.store.list() if d['title'] == title)
        self.w.store.update(ident, True, priority)
        return ident

    def query(self, text):
        self.select(text)
        self.w.selection_action.trigger()
        spin_until(lambda: not self.w.selection_task.busy)
        return self.w.selection_definitions.toPlainText()

    def test_real_worker_priority_empty_exact_and_no_active(self):
        self.assertFalse(self.w.selection_action.isEnabled())
        self.assertFalse(self.w.selection_btn.isEnabled())
        self.assertIn('Selecciona', self.w.selection_hint.text())
        self.assertIn('No hay diccionarios activos', self.query('日本'))
        first = self.import_dictionary('First', 1)
        second = self.import_dictionary('Second', 10)
        text = self.query('日本')
        self.assertLess(text.index('Second'), text.index('First'))
        self.assertIn('にほん', text)
        self.assertIn('Japan', text)
        self.assertIn('Diccionario:', text)
        self.assertEqual(self.w.raw_text, '原文')
        self.assertEqual(self.w.editor.toPlainText(), '日本')
        self.assertEqual(self.w.translation.toPlainText(), 'Argos sentinel')
        self.assertEqual(self.w.tabs.currentIndex(), 0)
        self.assertIn('Sin coincidencias exactas', self.query('不存在'))
        self.assertIn('Sin coincidencias exactas', self.query(' 日本 '))
        self.w.store.update(second, False, 10)
        self.assertNotIn('Second', self.query('日本'))
        self.w.store.update(first, False, 1)
        self.assertIn('No hay diccionarios activos', self.query('日本'))
        self.w.editor.moveCursor(QTextCursor.End)
        self.assertFalse(self.w.selection_btn.isEnabled())

    def test_out_of_order_and_edit_invalidation(self):
        def result(generation, term, title):
            return {'generation': generation, 'term': term, 'active': 1,
                    'results': [{'title': title, 'expression': term, 'reading': '', 'meanings': '["Japan"]'}]}
        with patch.object(self.w.selection_task, 'start') as start:
            self.select('日本')
            self.w.lookup_selection()
            old = start.call_args.args[0]['generation']
            self.select('日本語')
            self.w.lookup_selection()
            new = start.call_args.args[0]['generation']
            self.w.selection_result(result(new, '日本語', 'NEW'))
            self.w.selection_result(result(old, '日本', 'OLD'))
            self.assertIn('NEW', self.w.selection_definitions.toPlainText())
            self.assertNotIn('OLD', self.w.selection_definitions.toPlainText())
            self.w.editor.insertPlainText('edited')
            self.w.selection_result(result(new, '日本語', 'STALE'))
            self.assertNotIn('STALE', self.w.selection_definitions.toPlainText())

    def test_busy_worker_coalesces_latest_and_error(self):
        with patch.object(self.w.selection_task, 'start') as start:
            self.select('日本')
            self.w.lookup_selection()
            self.w.selection_task.busy = True
            self.select('old pending')
            self.w.lookup_selection()
            self.select('latest')
            self.w.lookup_selection()
            self.assertEqual(start.call_count, 1)
            self.w.selection_task.busy = False
            self.w.selection_error('old error')
            self.assertEqual(start.call_count, 2)
            self.assertEqual(start.call_args.args[0]['term'], 'latest')
            self.assertNotIn('old error', self.w.selection_definitions.toPlainText())
            self.w.selection_error('timeout de prueba')
            self.assertIn('timeout de prueba', self.w.selection_definitions.toPlainText())
