import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from naatik_next.storage import Store,UserError,Cancelled
from naatik_next.dictionary_content import render_results
from naatik_next.dictionary_import_dialog import ImportReview
from naatik_next.app import Window
from PySide6.QtCore import Qt
from naatik_next.dictionary_view import DictionaryView
from tests.test_processes import APP,spin_until
from tests.test_storage import ROW

KANJI = ['日','ニチ ジツ','ひ -び -か','jouyou',['day','sun'],{'strokes':'4','grade':'1'}]
PITCH = [['日本','pitch',{'reading':'にほん','pitches':[{'position':2}]}],
         ['日本','pitch',{'reading':'にっぽん','pitches':[{'position':3}]}]]
GRAMMAR = ['くらい','くらい','','',0,['文法項目 | くらい\n[解説] Approximate quantity.\n[例文] 九時間くらいかかる。'],0,'DOJG基本']


class MultiDictionaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.store=Store(self.root/'db.sqlite')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def archive(self,title='Mixed',banks=None):
        p=self.root/(title+'.zip')
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('index.json',json.dumps({'format':3,'title':title,'revision':'1'}))
            for name,rows in (banks or {'term_bank_1.json':[ROW],'kanji_bank_1.json':[KANJI],
                    'term_meta_bank_1.json':PITCH,'term_bank_2.json':[GRAMMAR]}).items():
                z.writestr(name,json.dumps(rows,ensure_ascii=False))
        return p

    def test_all_types_lossless_association_render_activation_delete(self):
        p=self.archive()
        before=p.read_bytes()
        preview=self.store.inspect_zip(p)
        self.assertEqual(preview['counts'],{'kanji':1,'term':1,'grammar':1,'pitch':2})
        self.assertEqual(self.store.list(),[])
        self.store.import_zip(p,expected_digest=preview['digest'])
        self.assertTrue(self.store.inspect_zip(p)['duplicate'])
        rows=self.store.lookup('日本')
        term=next(r for r in rows if r['kind']=='term')
        self.assertEqual([r['reading'] for r in term['accents']],['にほん'])
        self.assertEqual(json.loads(term['accents'][0]['pitches'])[0]['position'],2)
        self.assertEqual(len([r for r in rows if r['kind']=='pitch']),2)
        self.assertEqual(json.loads(self.store.lookup('日')[0]['source_row']),KANJI)
        self.assertEqual(self.store.lookup('くらい')[0]['kind'],'grammar')
        view=DictionaryView()
        view.setHtml(render_results(rows+self.store.lookup('日')+self.store.lookup('くらい')))
        for text in ['Japan','On:','Kun:','strokes','日','Gramática','九時間','mora 2','mora 3','Acento tonal']:
            self.assertIn(text,view.toPlainText())
        view.close()
        ident=self.store.list()[0]['id']
        self.store.update(ident,False,20)
        for q in ['日本','日','くらい']:self.assertFalse(self.store.lookup(q))
        self.store.update(ident,True,20)
        other=self.archive('Other',{'term_bank_1.json':[ROW]})
        self.store.import_zip(other)
        self.assertEqual(self.store.lookup('日本')[0]['title'],'Mixed')
        self.store.remove(ident)
        self.assertEqual([r['title'] for r in self.store.lookup('日本')],['Other'])
        self.assertFalse(self.store.lookup('日'))
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM pitches').fetchone()[0],0)
        self.assertEqual(before,p.read_bytes())

    def test_unsupported_modes_explicit_and_invalid_pitch_rollback(self):
        p=self.archive(banks={'term_bank_1.json':[ROW],'term_meta_bank_1.json':[
            ['日本','freq',1],*PITCH],'kanji_meta_bank_1.json':[['日','freq',10]]})
        entry=self.store.inspect_zip(p)
        self.assertEqual(len(entry['warnings']),2)
        result=self.store.import_zip(p)
        self.assertEqual(result['count'],3)
        metadata=json.loads(self.store.list()[0]['metadata'])
        self.assertEqual(metadata['warnings'],entry['warnings'])
        p=self.archive('Bad',{'term_bank_1.json':[ROW],'term_meta_bank_1.json':[['日本','pitch',{
            'reading':'にほん','pitches':[{'position':-1}]}]]})
        with self.assertRaisesRegex(UserError,'Posición'):self.store.import_zip(p)
        self.assertEqual(len(self.store.list()),1)
        p=self.archive('Unknown',{'term_meta_bank_1.json':[['日本','shell','ignored']]})
        with self.assertRaisesRegex(UserError,'desconocido') as failed:self.store.import_zip(p)
        self.assertEqual(failed.exception.preview['title'],'Unknown')

    def test_cancel_mixed_transaction_and_changed_preview(self):
        p=self.archive(banks={'kanji_bank_1.json':[KANJI]*1100,'term_meta_bank_1.json':PITCH})
        stop=[False]
        with self.assertRaises(Cancelled):
            self.store.import_zip(p,cancelled=lambda:stop[0],progress=lambda msg:stop.__setitem__(0,True))
        self.assertEqual(self.store.list(),[])
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM kanji').fetchone()[0],0)
        with self.assertRaisesRegex(UserError,'cambió'):self.store.import_zip(p,expected_digest='bad')

    def test_migration_keeps_old_rows_metadata_settings_and_is_idempotent(self):
        old=self.root/'old.sqlite'
        c=sqlite3.connect(old)
        c.executescript('''CREATE TABLE dictionaries(id INTEGER PRIMARY KEY,digest TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL,revision TEXT NOT NULL,source_language TEXT,target_language TEXT,
 enabled INTEGER NOT NULL DEFAULT 1,priority INTEGER NOT NULL DEFAULT 0,count INTEGER NOT NULL DEFAULT 0,
 metadata TEXT, UNIQUE(title,revision));
 CREATE TABLE terms(dictionary_id INTEGER NOT NULL REFERENCES dictionaries(id) ON DELETE CASCADE,
 expression TEXT NOT NULL, reading TEXT NOT NULL, meanings TEXT NOT NULL,source_row TEXT);
 INSERT INTO dictionaries VALUES(7,'hash','Old','1','ja','en',0,42,1,'{"retained":"yes"}');
 INSERT INTO terms VALUES(7,'日本','にほん','["Japan"]',NULL);''')
        before=c.execute('SELECT * FROM dictionaries').fetchall(),c.execute('SELECT * FROM terms').fetchall()
        c.close()
        for _ in range(2):
            s=Store(old)
            self.assertEqual((s.conn.execute('SELECT * FROM dictionaries').fetchall()[0][:],
                              s.conn.execute('SELECT * FROM terms').fetchall()[0][:]),(before[0][0],before[1][0]))
            self.assertEqual(s.conn.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertEqual(s.list()[0]['priority'],42)
            self.assertFalse(s.lookup('日本'))
            s.close()

    def test_review_blocked_duplicates_and_warnings_require_explicit_selection(self):
        entries=[self.store.inspect_zip(self.archive()),{'path':'bad.zip','error':'Invalid'},
                 dict(self.store.inspect_zip(self.archive('Other')),duplicate='repeated'),
                 dict(self.store.inspect_zip(self.archive('Warnings')),warnings=['Not imported: freq'])]
        dialog=ImportReview(entries)
        self.assertEqual([e['title'] for e in dialog.selected()],['Mixed'])
        self.assertFalse(dialog.table.item(1,0).flags() & Qt.ItemIsEnabled)
        dialog.table.item(3,0).setCheckState(Qt.Checked)
        self.assertEqual(len(dialog.selected()),2)
        dialog.close()

    def test_pattern_text_and_untrusted_kanji_are_escaped(self):
        p=self.archive(banks={'kanji_bank_1.json':[['字','<script>','x','', ['<img src=x>'],{'<x>':'<iframe>'}]],
            'term_meta_bank_1.json':[['字','pitch',{'reading':'じ','pitches':[{'position':'HL','nasal':[0],'devoice':1,'tags':['<img>']}]}]]})
        self.store.import_zip(p)
        html=render_results(self.store.lookup('字'))
        self.assertNotIn('<script>',html)
        self.assertNotIn('<iframe>',html)
        self.assertNotIn('<img',html)
        self.assertIn('H = alto',html)

    def test_actual_multi_file_preview_and_sequential_workers_offscreen(self):
        env={k:str(self.root/k) for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME')}
        first=self.archive('First',{'term_bank_1.json':[ROW]})
        second=self.archive('Second',{'kanji_bank_1.json':[KANJI],'term_meta_bank_1.json':PITCH})
        with patch.dict(os.environ,env):
            with patch('naatik_next.app.QTimer.singleShot'):w=Window()
            try:
                with patch('naatik_next.app.QFileDialog.getOpenFileNames',return_value=([str(first),str(second),str(self.root/'invalid.zip')],'')), patch('naatik_next.app.ImportReview.exec',return_value=ImportReview.Accepted):
                    w.add_dictionary()
                    spin_until(lambda:not w.inspect_task.busy and not w.import_task.busy and not w.import_queue and w.current_import is None)
                self.assertEqual(len(w.store.list()),2)
                self.assertIn('invalid.zip',w.import_report.toPlainText())
                self.assertIn('Importado: First',w.import_report.toPlainText())
                self.assertIn('Importado: Second',w.import_report.toPlainText())
                self.assertEqual(len(w.store.lookup('日')),1)
                self.assertEqual(len(w.store.lookup('日本')),3)
                self.assertTrue(w.add_dict.isEnabled())
            finally:w.close()

    def test_batch_cancel_does_not_start_remaining_files_or_remove_existing(self):
        env={k:str(self.root/k) for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME')}
        existing=self.archive('Keep',{'term_bank_1.json':[ROW]})
        cancel=self.archive('Cancel',{'kanji_bank_1.json':[KANJI]*40000})
        pending=self.archive('Pending',{'term_meta_bank_1.json':PITCH})
        with patch.dict(os.environ,env):
            with patch('naatik_next.app.QTimer.singleShot'):w=Window()
            try:
                w.store.import_zip(existing)
                w.import_queue=[w.store.inspect_zip(cancel),w.store.inspect_zip(pending)]
                w.import_task.progress.connect(lambda text:w.cancel())
                w.next_dictionary_import()
                spin_until(lambda:not w.import_task.busy and w.current_import is None)
                self.assertEqual([d['title'] for d in w.store.list()],['Keep'])
                self.assertIn('Pending.zip: no iniciado por cancelación',w.import_report.toPlainText())
                self.assertFalse(w.import_queue)
            finally:w.close()


    def test_cancel_after_commit_before_ack_reports_existing_complete_import(self):
        env={k:str(self.root/k) for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME')}
        source=self.archive()
        with patch.dict(os.environ,env):
            with patch('naatik_next.app.QTimer.singleShot'):w=Window()
            try:
                w.current_import=w.store.inspect_zip(source)
                w.store.import_zip(source)
                w.import_failed('Operación cancelada (regresión de la frontera commit/ACK)')
                self.assertIn('Ya está importado y completo',w.import_report.toPlainText())
                self.assertEqual(w.table.rowCount(),1)
                self.assertEqual(w.store.list()[0]['count'],5)
            finally:w.close()
