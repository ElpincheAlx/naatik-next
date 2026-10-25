"""Isolated protocol and UI acceptance. Never contact the default Anki port."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from naatik_next.anki import Client, Journal, AnkiError, execute, validate
from naatik_next.i18n import t


class FakeClient(Client):
    calls = []
    notes = {}
    mode = 'ok'

    def call(self, action, **params):
        self.calls.append((action, copy.deepcopy(params)))
        if action == 'requestPermission': return {'permission': 'granted', 'requireApiKey': False}
        if action == 'version': return 6
        if action == 'deckNames': return ['試験 mazo']
        if action == 'modelNames': return ['Prueba tipo']
        if action == 'modelFieldNames': return ['表', '裏']
        if action == 'modelTemplates': return {'Tarjeta': {'Front':'{{表}}','Back':'{{裏}}'}}
        if action == 'canAddNotes': return [True]
        if action == 'addNote':
            self.notes[9] = copy.deepcopy(params['note'])
            if self.mode == 'lost': raise AnkiError('lost')
            if self.mode == 'invalid': return True
            return 9
        if action == 'findNotes':
            assert params['query'].startswith('tag:naatik_tx_')
            return list(self.notes)
        if action == 'cardsInfo': return [dict(deckName='試験 mazo',note=9)]
        if action == 'notesInfo':
            return [dict(noteId=i, cards=[19], modelName=self.notes[i]['modelName'], tags=self.notes[i]['tags'],
                         fields={k:dict(value=v) for k,v in self.notes[i]['fields'].items()}) for i in params['notes']]
        raise AssertionError(action)


class AnkiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {key:self.tmp.name+'/'+key for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME')}); self.env.start()
        FakeClient.calls=[]; FakeClient.notes={}; FakeClient.mode='ok'
        self.note=dict(deckName='試験 mazo',modelName='Prueba tipo',fields={'表':'日本', '裏':''})

    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()

    def request(self, operation, **kwargs):
        with patch('naatik_next.anki.Client', FakeClient):
            return execute(dict(endpoint='http://127.0.0.1:19439',operation=operation,**kwargs))

    def test_metadata_never_writes(self):
        self.request('check'); self.request('fields',model='Prueba tipo')
        self.assertEqual([a for a,_ in FakeClient.calls], ['requestPermission','version','deckNames','modelNames','modelFieldNames'])

    def test_single_write_and_private_journal(self):
        record=Journal().reserve(self.note)
        result=self.request('send',record=record,note=self.note)
        self.assertEqual(result['state'],'confirmed')
        self.assertEqual(result['record']['note_id'],9)
        self.assertFalse(FakeClient.notes[9]['options']['allowDuplicate'])
        with self.assertRaises(AnkiError): Journal().reserve(self.note)
        self.assertEqual(sum(a=='addNote' for a,_ in FakeClient.calls),1)
        self.assertNotIn('日本', ''.join(p.read_text() for p in Journal().directory.glob('*.json')))

    def test_lost_response_reconciles_without_resend(self):
        FakeClient.mode='lost'
        record=Journal().reserve(self.note)
        self.assertEqual(self.request('send',record=record,note=self.note)['state'],'uncertain')
        with self.assertRaises(AnkiError): Journal().reserve(self.note)
        self.assertEqual(self.request('reconcile',record=record)['state'],'confirmed')
        self.assertEqual(sum(a=='addNote' for a,_ in FakeClient.calls),1)

    def test_zero_changed_multiple_results_stay_uncertain(self):
        FakeClient.mode='lost'; record=Journal().reserve(self.note)
        self.assertEqual(self.request('reconcile',record=record)['state'],'uncertain')
        self.request('send',record=record,note=self.note)
        FakeClient.notes[9]['fields']['表']='changed'
        self.assertEqual(self.request('reconcile',record=record)['state'],'uncertain')
        FakeClient.notes[10]=FakeClient.notes[9]
        self.assertEqual(self.request('reconcile',record=record)['state'],'uncertain')

    def test_validation_and_endpoint(self):
        for endpoint in ('https://127.0.0.1:8765','http://example.org','http://127.0.0.1/a','http://user@localhost'):
            with self.assertRaises(AnkiError): Client(endpoint)
        for first in ('<br> &nbsp;', '', '{{c1::text}}'):
            self.note['fields']['表']=first
            with self.assertRaises(AnkiError): validate(self.note,['表','裏'])

    def test_invalid_id_is_uncertain(self):
        FakeClient.mode='invalid'; record=Journal().reserve(self.note)
        self.assertEqual(self.request('send',record=record,note=self.note)['state'],'uncertain')

    def test_corrupt_journal_and_disk_failure_block(self):
        (Journal().directory/'bad.json').write_text('bad')
        with self.assertRaises(ValueError): Journal().reserve(self.note)
        self.assertFalse(FakeClient.calls)


class TransportTests(unittest.TestCase):
    def test_ephemeral_loopback_http(self):
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(body)
                value={'requestPermission':{'permission':'granted','requireApiKey':False},'version':6,'deckNames':['d'],'modelNames':['m']}[body['action']]
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(dict(result=value,error=None)).encode())
        try: server=HTTPServer(('127.0.0.1',0),Handler)
        except PermissionError: self.skipTest('Sandbox denies loopback listener')
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            client=Client('http://127.0.0.1:'+str(server.server_port))
            self.assertEqual(client.check()['decks'],['d'])
            self.assertNotIn('addNote',[c['action'] for c in calls])
        finally: server.shutdown(); server.server_close(); thread.join()


class GuiTests(unittest.TestCase):
    setUp = AnkiTests.setUp
    tearDown = AnkiTests.tearDown
    def test_guided_setup_edit_cancel_and_two_drafts(self):
        from PySide6.QtWidgets import QApplication, QWidget, QTabWidget
        from naatik_next.anki_ui import AnkiSection
        app=QApplication.instance() or QApplication([])
        owner=QWidget(); owner.settings={}; owner.tasks=[]; owner.closing=False
        owner.interrupted=lambda:False; owner.persist=lambda:None; owner.tabs=QTabWidget(owner)
        section=AnkiSection(owner); section.parent_scroll=section; owner.tabs.addTab(section,'Anki')
        def result(operation, **kwargs):
            section.operation=operation
            with patch('naatik_next.anki.Client', FakeClient):
                section.completed(execute(dict(endpoint='http://127.0.0.1:19345',operation=operation,**kwargs)))
        section.run=lambda operation,**kwargs: result(operation,**kwargs)
        section.open_draft(dict(sentence='日本',translation='Japan'))
        draft=section.drafts[-1]
        self.assertIsNone(draft.config)
        self.assertFalse(FakeClient.calls)
        section.check()
        self.assertIsNone(section.deck.currentData()); self.assertIsNone(section.model.currentData())
        section.deck.setCurrentIndex(1); section.model.setCurrentIndex(1)
        section.mapping['表'].setCurrentIndex(section.mapping['表'].findData('sentence'))
        section.save_config(); draft.adopt()
        self.assertEqual(draft.editors['表'].toPlainText(),'日本')
        self.assertFalse(draft.blocks['translation'][0].isChecked())
        draft.editors['表'].setPlainText('編集'); draft.hide(); draft.show()
        self.assertEqual(draft.editors['表'].toPlainText(),'編集')
        draft.profile.setChecked(True); draft.send(); draft.send()
        self.assertEqual(sum(a=='addNote' for a,_ in FakeClient.calls),1)
        self.assertIn(t('Nota agregada · ID '),draft.status.text())
        section.open_draft(dict(sentence='編集')); second=section.drafts[-1]
        second.profile.setChecked(True); second.send()
        self.assertEqual(sum(a=='addNote' for a,_ in FakeClient.calls),1)
        self.assertIn(t('Este contenido ya tiene un intento registrado. Comprueba su resultado; no se reenviará.'),second.status.text())
        for task in owner.tasks: task.close()
        for item in section.drafts: item.close()
        owner.close(); owner.deleteLater(); app.processEvents()

class ParsingTests(unittest.TestCase):
    def test_transport_errors_limits_and_no_retry_or_redirect(self):
        from unittest.mock import Mock
        import http.client
        for status, data in [(302,b'{}'), (200,b'broken'), (200,b'{}'),
                             (200,b'{"result":true,"error":"secret text"}'),
                             (200,b'x'*(2*1024*1024+1))]:
            connection=Mock(); response=connection.getresponse.return_value
            response.status=status; response.read.return_value=data
            with patch('http.client.HTTPConnection',return_value=connection):
                with self.assertRaises(AnkiError) as raised: Client('http://127.0.0.1:19123').call('version')
            self.assertNotIn('secret text',str(raised.exception))
            connection.request.assert_called_once(); connection.close.assert_called_once()
        connection=Mock(); connection.getresponse.side_effect=http.client.RemoteDisconnected()
        with patch('http.client.HTTPConnection',return_value=connection):
            with self.assertRaises(AnkiError): Client('http://127.0.0.1:19123').call('addNote',note={})
        connection.request.assert_called_once()

    def test_permission_and_key_not_confused_with_metadata(self):
        for permission in ({'permission':'denied'}, {'permission':'granted','requireApiKey':True}, None):
            client=Client('http://127.0.0.1:19123')
            with patch.object(client,'call',return_value=permission) as call:
                with self.assertRaises(AnkiError): client.check()
                call.assert_called_once_with('requestPermission')
