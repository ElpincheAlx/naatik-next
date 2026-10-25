import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from naatik_next.storage import Store, UserError, Cancelled, load_settings, save_settings, paths

ROW = ['日本', 'にほん', '', '', 0, ['Japan'], 1, '']


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'db.sqlite')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def archive(self, name='terms.zip', title='Test', revision='1', rows=None, extra=None):
        p = self.root / name
        with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('index.json', json.dumps({'title': title, 'revision': revision, 'format': 3, 'sourceLanguage': 'ja', 'targetLanguage': 'en'}))
            z.writestr('term_bank_1.json', json.dumps([ROW] if rows is None else rows))
            for key, value in (extra or {}).items():
                z.writestr(key, value)
        return p

    def test_import_lookup_priority_activation_persistence_safe_remove(self):
        source = self.archive()
        original = source.read_bytes()
        self.store.import_zip(source)
        self.assertEqual(self.store.lookup('日本')[0]['title'], 'Test')
        self.assertEqual(self.store.lookup('にほん')[0]['expression'], '日本')
        self.store.import_zip(self.archive('two.zip', title='Second'))
        first, second = [d['id'] for d in sorted(self.store.list(), key=lambda d: d['id'])]
        self.store.update(second, True, 10)
        self.assertEqual(self.store.lookup('日本')[0]['title'], 'Second')
        self.store.update(first, False, 5)
        self.store.close()
        self.store = Store(self.root / 'db.sqlite')
        self.assertEqual(len(self.store.lookup('日本')), 1)
        self.store.remove(second)
        self.assertEqual(self.store.lookup('日本'), [])
        self.store.remove(first)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM terms').fetchone()[0], 0)

    def test_duplicate_hash_and_title_revision(self):
        source = self.archive()
        self.store.import_zip(source)
        with self.assertRaisesRegex(UserError, 'SHA-256'):
            self.store.import_zip(source)
        changed = self.archive('changed.zip', rows=[ROW, ROW])
        with self.assertRaisesRegex(UserError, 'duplicado'):
            self.store.import_zip(changed)
        self.assertEqual(len(self.store.list()), 1)

    def test_late_invalid_entry_rolls_back(self):
        source = self.archive(rows=[ROW, ['bad']])
        with self.assertRaisesRegex(UserError, 'entrada inválida'):
            self.store.import_zip(source)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM terms').fetchone()[0], 0)

    def test_cancel_after_inserts_rolls_back(self):
        stop = [False]
        source = self.archive(rows=[ROW] * 1100)
        def progress(message):
            stop[0] = True
        with self.assertRaises(Cancelled):
            self.store.import_zip(source, cancelled=lambda: stop[0], progress=progress)
        self.assertEqual(self.store.list(), [])

    def test_unsafe_paths_and_unsupported_payload(self):
        for extra in ({'../escape': 'x'}, {'/absolute': 'x'}, {'C:/evil': 'x'}, {'a\\b': 'x'}, {'unsafe.py': 'print(1)'}):
            with self.subTest(extra=extra), self.assertRaises(UserError):
                self.store.import_zip(self.archive(extra=extra))
        with self.assertRaisesRegex(UserError, 'enriquecido'):
            self.store.import_zip(self.archive(rows=[ROW[:5] + [[{'type': 'structured-content', 'content': {'tag': 'img', 'path': 'https://example.invalid/x.png'}}]] + ROW[6:]]))
        self.assertEqual(self.store.list(), [])
        self.assertFalse((self.root.parent / 'escape').exists())

    def test_duplicate_members_symlinks_and_bomb(self):
        p = self.archive()
        with zipfile.ZipFile(p, 'a') as z:
            link = zipfile.ZipInfo('link')
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            z.writestr(link, '/etc/passwd')
        with self.assertRaisesRegex(UserError, 'peligrosa'):
            self.store.import_zip(p)
        p = self.archive(extra={'tag_bank_1.json': ' ' * 200000})
        with self.assertRaisesRegex(UserError, 'límites'):
            self.store.import_zip(p)

    def test_invalid_and_non_zip(self):
        p = self.root / 'invalid.zip'
        p.write_text('not a zip')
        with self.assertRaisesRegex(UserError, 'inválido'):
            self.store.import_zip(p)
        with self.assertRaisesRegex(UserError, 'Solo se admite'):
            self.store.import_zip(self.root / 'data.db')

    def test_xdg_settings_and_corrupt_error(self):
        with patch.dict(os.environ, {key: str(self.root / key) for key in ['XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME']}):
            save_settings({'ocr_engine': 'tesseract', 'translation_route': ['ja', 'en', 'es']})
            self.assertEqual(load_settings()['translation_route'], ['ja', 'en', 'es'])
            self.assertTrue(str(paths()['data']).startswith(str(self.root)))
            (paths()['config'] / 'settings.json').write_text('invalid')
            with self.assertRaisesRegex(UserError, 'preferencias'):
                load_settings()
