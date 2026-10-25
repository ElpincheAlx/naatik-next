import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from naatik_next.storage import Store, UserError
from naatik_next.dictionary_content import validate_meanings, render_results
from naatik_next.dictionary_view import DictionaryView

APP = QApplication.instance() or QApplication([])
TREE = {'type': 'structured-content', 'content': [
    {'tag': 'ul', 'content': [{'tag': 'li', 'content': 'Japan'}]},
    {'tag': 'ul', 'data': {'content': 'examples'}, 'content': [
        {'tag': 'li', 'lang': 'ja', 'content': '日本です。'},
        {'tag': 'li', 'lang': 'en', 'content': 'It is Japan.'}]},
    {'tag': 'table', 'content': {'tag': 'tr', 'content': [
        {'tag': 'th', 'content': 'にほん'}, {'tag': 'td', 'content': 'にっぽん'}]}},
    {'tag': 'a', 'href': '?query=日本', 'content': '日本'}]}
ROW = ['日本', 'にほん', 'n', '', 12, [TREE], 42, 'news']


class DictionaryContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, rows):
        p = self.root / 'dictionary.zip'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('index.json', json.dumps({'format': 3, 'title': 'Rich', 'revision': '1'}))
            z.writestr('term_bank_1.json', json.dumps(rows))
            z.writestr('tag_bank_1.json', json.dumps([['n', '', 0, 'noun', 0]]))
        return p

    def test_lossless_tree_and_row_metadata_render_and_persistence(self):
        db = self.root / 'db.sqlite'
        store = Store(db)
        try:
            store.import_zip(self.archive([ROW]))
            result = store.lookup('日本')[0]
            self.assertEqual(json.loads(result['meanings']), [TREE])
            self.assertEqual(json.loads(result['source_row']), ROW)
            metadata = json.loads(store.conn.execute('SELECT metadata FROM dictionaries').fetchone()[0])
            self.assertEqual(metadata['tags'][0][3], 'noun')
            html = render_results([result])
            self.assertIn('<table', html)
            self.assertIn('referencia:', html)
            self.assertNotIn('href=', html)
            view = DictionaryView()
            view.setHtml(html)
            for text in ['Japan', 'にほん', 'にっぽん', '日本です。', 'It is Japan.', 'Diccionario:']:
                self.assertIn(text, view.toPlainText())
            self.assertEqual(view.document().rootFrame().childFrames()[0].rows(), 1)
            view.close()
        finally:
            store.close()
        reopened = Store(db)
        self.assertEqual(json.loads(reopened.lookup('にほん')[0]['source_row']), ROW)
        reopened.close()

    def test_late_unsafe_content_rolls_back(self):
        bad = list(ROW)
        bad[5] = [{'type': 'structured-content', 'content': {'tag': 'script', 'content': 'alert(1)'}}]
        s = Store(self.root / 'db.sqlite')
        try:
            with self.assertRaises(UserError):
                s.import_zip(self.archive([ROW, bad]))
            self.assertEqual(s.list(), [])
        finally:
            s.close()

    def test_text_escaped_styles_not_executed_resources_blocked(self):
        content = [{'type': 'structured-content', 'content': {'tag': 'span',
                    'style': {'background': 'url(file:///etc/passwd)'},
                    'content': '<img src="https://example.invalid" onerror="bad()">'}}]
        html = render_results([{'expression': '<script>', 'reading': 'x', 'title': 'Test',
                                'meanings': json.dumps(content)}])
        self.assertNotIn('<img', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('url(', html)
        view = DictionaryView()
        for url in ['https://example.invalid/x', 'file:///etc/passwd', 'data:image/png;base64,x', 'relative.png']:
            self.assertIsNone(view.loadResource(2, QUrl(url)))
        self.assertFalse(view.openLinks())
        self.assertFalse(view.openExternalLinks())
        view.close()

    def test_bounds_and_unknown_nodes(self):
        node = 'x'
        for _ in range(35):
            node = {'tag': 'span', 'content': node}
        for item in [node, {'tag': 'img', 'path': 'file:///etc/passwd'},
                     {'tag': 'span', 'onclick': 'bad()'}, {'tag': ['script']},
                     {'tag': 'a', 'href': 'javascript:bad()', 'content': 'x'}]:
            with self.assertRaises(UserError):
                validate_meanings([{'type': 'structured-content', 'content': item}])

    def test_additive_migration_preserves_plain_rows(self):
        p = self.root / 'old.sqlite'
        c = sqlite3.connect(p)
        c.executescript('''CREATE TABLE terms(dictionary_id INTEGER, expression TEXT, reading TEXT, meanings TEXT);
            INSERT INTO terms VALUES(1,'日本','にほん','["Japan"]');''')
        c.close()
        store = Store(p)
        self.assertEqual(store.conn.execute('SELECT meanings FROM terms').fetchone()[0], '["Japan"]')
        self.assertIn('source_row', [r[1] for r in store.conn.execute('PRAGMA table_info(terms)')])
        store.close()
