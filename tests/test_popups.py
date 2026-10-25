"""Popup behavior with injected model responses, plus real Next worker boundaries."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from naatik_next.app import Window
from naatik_next.processes import Task
from tests.test_processes import APP, spin_until


class PopupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='next-popup-ui-')
        self.env = patch.dict(os.environ, {k:self.tmp.name+'/'+k for k in
                            ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')})
        self.env.start()
        self.calls = []
        def start(task, request, *args, **kwargs):
            self.calls.append((task, request)); task.busy = True
        self.start = patch.object(Task, 'start', autospec=True, side_effect=start)
        self.start.start()
        with patch('naatik_next.app.QTimer.singleShot'):
            self.w = Window(background=True, popup_only=True)

    def tearDown(self):
        self.w.close()
        from PySide6.QtCore import QCoreApplication,QEvent
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        self.start.stop(); self.env.stop(); self.tmp.cleanup()

    def popup(self, mode='translator', text='日本'):
        APP.clipboard().setText(text)
        self.assertEqual(self.w.external_command(mode),'shown')
        p = self.w.popups[mode]
        p.debounce.stop()
        return p

    def answer(self, p, task, value):
        request = p.running[task]
        task.busy = False
        task.result.emit(dict(popup_generation=request['popup_generation'],value=value))
        return request

    def routes(self, p):
        self.answer(p,p.translate_task,dict(routes=[['ja','en']],errors=[],detail='fixture, no inference'))
        p.route.setCurrentIndex(p.route.findData(['ja','en']))
        p.debounce.stop()

    def test_anki_snapshot_is_owned_by_composer_and_never_sends_on_open(self):
        from unittest.mock import patch
        for mode in ('translator', 'phrase'):
            p = self.popup(mode)
            p.editor.setPlainText('日本を読む。'); p.debounce.stop()
            with patch.object(self.w.anki_section.task, 'start') as start:
                p.open_anki()
                draft = self.w.anki_section.drafts[-1]
                p.editor.setPlainText('別の文'); p.debounce.stop()
                self.assertEqual(draft.sources['sentence'], '日本を読む。')
                self.assertEqual(draft.sources['word'], '')
                start.assert_not_called()
                draft.close()

    def test_independent_clipboard_actions_reuse_each_popup_and_never_capture(self):
        for mode in ('translator','phrase'):
            p = self.popup(mode)
            self.assertFalse(self.w.isVisible())
            APP.clipboard().setText('次の文')
            self.w.external_command(mode)
            self.assertIs(self.w.popups[mode],p)
            self.assertEqual(p.editor.toPlainText(),'次の文')
            p.debounce.stop()
        self.assertEqual(len(self.w.popups),2)
        self.assertFalse(any(task in (self.w.capture_task,self.w.manga_task,self.w.ocr_task,self.w.detect_task,self.w.argos_task)
                             for task,_ in self.calls))
        self.assertFalse(self.w.capture_active)
        with patch.object(p.translate_task,'cancel') as popup_cancel:
            self.w.cancel()
            popup_cancel.assert_not_called()
        with patch.object(self.w.capture_task,'cancel') as capture_cancel:
            p.cancel()
            capture_cancel.assert_not_called()

    def test_empty_clipboard_has_editable_popup_without_old_ocr_fallback(self):
        self.w.raw_text = 'previous OCR'
        p = self.popup(text='')
        self.assertEqual(p.editor.toPlainText(),'')
        p.editor.insertPlainText('入力')
        self.assertEqual(p.editor.toPlainText(),'入力')
        self.assertNotIn('previous OCR', p.editor.toPlainText())

    def test_rapid_edit_coalesces_and_rejects_old_translation_and_error(self):
        p = self.popup(); self.routes(p)
        p.process()
        self.assertEqual(p.running[p.translate_task]['text'],'日本')
        p.editor.setPlainText('古い'); p.process()
        p.editor.setPlainText('最新'); p.process()
        self.answer(p,p.translate_task,dict(text='old result',route=['ja','en']))
        self.assertEqual(p.translation.toPlainText(),'')
        APP.processEvents()
        self.assertEqual(p.running[p.translate_task]['text'],'最新')
        self.answer(p,p.translate_task,dict(text='latest result',route=['ja','en']))
        self.assertEqual(p.translation.toPlainText(),'latest result')
        p.editor.setPlainText('changed'); p.process()
        p.cancel()
        p.translate_task.error.emit('late failure')
        self.assertNotIn('late failure',p.translation_status.text())
        self.assertEqual(APP.clipboard().text(),'日本')

    def test_cancel_and_close_invalidate_all_queued_results(self):
        p = self.popup(); self.routes(p); p.process()
        old = p.running[p.translate_task]['popup_generation']
        p.cancel()
        p.translate_task.result.emit(dict(popup_generation=old,value=dict(text='late',route=['ja','en'])))
        self.assertEqual(p.translation.toPlainText(),'')
        p.close()
        self.assertFalse(p.isVisible())
        self.w.external_command('translator')
        self.assertIs(p,self.w.popups['translator'])
        self.assertTrue(p.isVisible())

    def test_missing_resources_are_explicit_and_downloads_need_confirmation(self):
        p = self.popup('phrase')
        self.answer(p,p.translate_task,dict(routes=[],errors=[],detail='No local models'))
        p.phrase_task.program = '/missing/Next-owned-python'
        p.process()
        self.assertIn('Faltan recursos',p.analysis_status.text())
        self.assertIn('Faltan modelos',p.translation_status.text())
        self.assertEqual(p.translation.toPlainText(),'')
        from PySide6.QtWidgets import QMessageBox
        with patch('naatik_next.popups.QMessageBox.question',return_value=QMessageBox.No):
            p.prepare_phrase()
        self.assertFalse(p.resource_task.busy)
        self.assertFalse(any(req['action']=='prepare_phrase_runtime' for _,req in self.calls))

    def test_exact_lookup_and_safe_furigana_do_not_replace_translation(self):
        p = self.popup('phrase'); self.routes(p)
        data=dict(sentence='<日本>',resource='injected tokenizer', tokens=[dict(surface='<日本>',base='日本',
                  reading='にほん',pos='名詞',start=0,end=4,unknown=False)])
        p.show_analysis(data)
        self.assertIn('にほん',p.furigana.toPlainText())
        self.assertNotIn(p.lookup_task,p.running)
        p.word_cards[0].toggle.click()
        self.assertEqual(p.running[p.lookup_task]['term'],'日本')
        self.answer(p,p.lookup_task,dict(active=0,results=[]))
        self.assertIn('No hay diccionarios activos',p.dictionary_status.text())
        self.assertEqual(p.translation.toPlainText(),'')
        p.lookup('none')
        self.answer(p,p.lookup_task,dict(active=1,results=[]))
        self.assertIn('Sin coincidencias exactas',p.definitions.toPlainText())
        p.lookup('previous')
        old=p.running[p.lookup_task]['popup_generation']
        p.lookup('next')
        p.lookup_task.busy=False
        p.lookup_task.result.emit(dict(popup_generation=old,value=dict(active=0,results=[])))
        self.assertNotIn('Sin diccionarios activos',p.definitions.toPlainText())
        with patch.object(p,'lookup') as lookup:
            p.editor.setPlainText(' 日本 ');p.editor.selectAll();p.lookup_selection()
            lookup.assert_called_once_with(' 日本 ')

    def test_cancel_during_route_discovery_cannot_restart_processing(self):
        p=self.popup()
        request=p.running[p.translate_task]
        p.cancel()
        p.translate_task.result.emit(dict(popup_generation=request['popup_generation'],value=dict(routes=[['ja','en']],errors=[],detail='late metadata')))
        self.assertEqual(p.route.count(),0)
        self.assertFalse(p.debounce.isActive())

    def test_route_change_discards_translation_and_keeps_definition_separate(self):
        p=self.popup();self.routes(p)
        p.route.addItem('ja → es',['ja','es'])
        p.process()
        old=p.running[p.translate_task]
        p.route.setCurrentIndex(p.route.findData(['ja','es']))
        p.translate_task.busy=False
        p.translate_task.result.emit(dict(popup_generation=old['popup_generation'],value=dict(text='old English',route=['ja','en'])))
        self.assertEqual(p.translation.toPlainText(),'')
        self.assertEqual(self.w.settings['translator_route'],['ja','es'])
        self.assertEqual(self.w.settings.get('ocr_engine'),None)

    def test_capture_copy_after_popup_only_boot_prepares_ocr_on_demand(self):
        p=self.popup('translator')
        self.assertTrue(self.w.ocr_deferred)
        with patch.object(self.w,'prepare_selected') as prepare:
            self.w.external_command('capture-copy')
            prepare.assert_called_once()
        self.assertEqual(len(self.w.popups),1)
        self.assertIs(self.w.popups['translator'],p)
        self.assertTrue(self.w.pending_copy_capture)

    def test_escape_cancels_debounce_and_hides_without_quitting_owner(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        p=self.popup('phrase');p.editor.setPlainText('変更')
        QTest.keyClick(p,Qt.Key_Escape)
        self.assertFalse(p.isVisible())
        self.assertFalse(p.debounce.isActive())
        self.assertFalse(p.pending)
        self.assertFalse(self.w.closing)


    def test_source_layout_and_independent_reading_cards(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QPushButton
        for mode in ('translator','phrase'):
            p=self.popup(mode)
            self.assertEqual((p.width(),p.height()),(720,840))
            self.assertEqual((p.minimumWidth(),p.minimumHeight()),(520,560))
            self.assertTrue(p.windowFlags() & Qt.FramelessWindowHint)
            self.assertFalse(p.options.isVisible())
            self.assertFalse(p.editor.acceptRichText())
            self.assertTrue(p.translation.isReadOnly())
            self.assertEqual(sum(b.text() == 'Agregar a Anki' for b in p.findChildren(QPushButton)), 1)
            copy=next(b for b in p.findChildren(QPushButton) if b.text() in ('Copiar texto','Copiar frase'))
            p.editor.setPlainText('edited original'); copy.click()
            self.assertEqual(APP.clipboard().text(),'edited original')
            options=next(b for b in p.findChildren(QPushButton) if b.text()=='Opciones ▾')
            options.click(); self.assertTrue(p.options.isVisible())

    def test_word_expansion_stale_reply_and_replaced_cards(self):
        p=self.popup('phrase'); self.routes(p)
        data=dict(sentence='日本語',resource='fixture',tokens=[
            dict(surface='日本',base='日本',reading='にほん',pos='名詞',start=0,end=2),
            dict(surface='語',base='語',reading='ご',pos='名詞',start=2,end=3)])
        p.show_analysis(data)
        self.assertEqual(len(p.word_cards),2)
        self.assertFalse(any(card.body.isVisible() for card in p.word_cards))
        self.assertNotIn(p.lookup_task,p.running)
        first,second=p.word_cards
        first.toggle.click(); self.assertFalse(first.body.isHidden())
        second.toggle.click()
        self.answer(p,p.lookup_task,dict(active=1,results=[]))
        self.assertNotIn('Sin coincidencias',second.definitions.toPlainText())
        self.assertIn('Sin coincidencias',first.definitions.toPlainText())
        APP.processEvents()
        self.assertEqual(p.running[p.lookup_task]['term'],'語')
        self.answer(p,p.lookup_task,dict(active=1,results=[]))
        self.assertIn('Sin coincidencias',second.definitions.toPlainText())
        second.toggle.click(); self.assertFalse(second.body.isVisible())
        p.editor.setPlainText('replacement')
        self.assertEqual(p.word_cards,[])
        self.assertIs(p.definitions,p.selection_definitions)
        self.assertFalse(p.word_timer.isActive())
        many=dict(sentence='日'*100,resource='fixture',tokens=[
            dict(surface='日',base='日',reading='ひ',pos='名詞',start=i,end=i+1) for i in range(100)])
        p.show_analysis(many)
        self.assertEqual(len(p.word_cards),24)
        self.assertTrue(p.word_timer.isActive())
        p.cancel(); APP.processEvents()
        self.assertEqual(len(p.word_cards),24)
        self.assertFalse(p.word_queue)

    def test_selection_tooltip_and_cancel_remain_safe(self):
        from PySide6.QtCore import Qt
        p=self.popup(); self.routes(p)
        p.editor.selectAll(); p.lookup_selection(); p.selection_timer.stop()
        self.assertTrue(p.selection_box.isVisible())
        self.assertEqual(p.selection_box.windowType(),Qt.ToolTip)
        self.answer(p,p.lookup_task,dict(active=1,results=[]))
        self.assertIn('Sin coincidencias',p.selection_definitions.toPlainText())
        p.cancel(); self.assertFalse(p.selection_box.isVisible())
        self.assertFalse(p.word_timer.isActive())
        self.assertEqual(APP.clipboard().text(),'日本')


    def test_popup_keeps_installed_route_switching_without_install_controls(self):
        from PySide6.QtWidgets import QPushButton
        p = self.popup()
        self.answer(p, p.translate_task, dict(routes=[['ja','en'], ['en','es']], errors=[], detail='fixture'))
        labels = {button.text() for button in p.findChildren(QPushButton)}
        self.assertNotIn('Configurar traducción', labels)
        self.assertNotIn('Importar .argosmodel…', labels)
        self.assertNotIn('Revisar modelos', labels)
        for route in (['ja','en'], ['en','es']):
            p.route.setCurrentIndex(p.route.findData(route))
            self.assertEqual(self.w.settings['translator_route'], route)
        p.debounce.stop()

    def section_answer(self, value):
        section = self.w.translation_section
        section.task.busy = False
        section.task.result.emit(value)

    def empty_translation_report(self, **changes):
        value = dict(installed=[], routes=[], errors=[], detail='fixture', runtime_error='missing', catalogue=dict(items=[], sha256=None))
        value.update(changes)
        return value

    def test_translation_journey_confirmation_runtime_install_validate_and_return(self):
        from PySide6.QtWidgets import QMessageBox, QPushButton
        from naatik_next.translation_setup import normalize
        p = self.popup()
        self.answer(p, p.translate_task, dict(routes=[], errors=[], detail='Faltan modelos'))
        p.prepare_translation.click()
        section = self.w.translation_section
        self.assertIs(self.w.tabs.currentWidget(), self.w.translation_tab)
        self.section_answer(self.empty_translation_report())
        self.assertEqual(section.state.text(), 'Sin configurar')
        self.assertGreaterEqual(section.source.findData('hi'), 0)  # selectable before any catalogue/network
        section.primary.click()
        self.section_answer(self.empty_translation_report())
        self.assertEqual(self.calls[-1][1]['action'], 'translation_catalogue')
        catalogue = dict(items=normalize([
            dict(from_code='ja', to_code='en', package_version='1.0', links=['https://argos-net.com/ja_en.argosmodel']),
            dict(from_code='en', to_code='es', package_version='1.0', links=['https://argos-net.com/en_es.argosmodel'])]), sha256='fixture')
        self.section_answer(catalogue)
        self.assertEqual(self.calls[-1][1]['action'], 'translation_details')
        proposal = dict(items=[dict(i, bytes=123) for i in catalogue['items']], route=['ja','en','es'], sha256='fixture')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No): self.section_answer(proposal)
        self.assertFalse(any(req['action'] in ('translation_runtime','translation_download') for _, req in self.calls))
        section.flow = True
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes) as confirm:
            section.finished(section.serial, 'translation_details', proposal)
        self.assertIn('intermedio', confirm.call_args.args[2])
        self.assertIn('123 bytes', confirm.call_args.args[2])
        self.assertEqual(self.calls[-1][1]['action'], 'translation_runtime')
        self.section_answer(dict(detail='fixture runtime'))
        self.assertEqual(self.calls[-1][1]['action'], 'translation_download')
        self.assertTrue(self.calls[-1][1]['preserve_installed'])
        self.section_answer(dict(route=['ja','en','es'], input='fixture', output='simulated output', offline_checked=True, installed=[]))
        self.assertEqual(section.state.text(), 'Listo')
        self.assertEqual(self.w.settings['translation_route'], ['ja','en','es'])
        self.assertTrue(any(task is p.translate_task and req['action']=='routes' for task,req in self.calls))
        self.answer(p, p.translate_task, dict(routes=[['ja','en','es']], errors=[], detail='fixture'))
        self.assertFalse(p.prepare_translation.isVisible())
        p.close(); self.assertEqual(section.state.text(), 'Listo')
        labels = [b.text() for b in self.w.findChildren(QPushButton)]
        for removed in ('Revisar modelos', 'Revisar modelos Argos locales', 'Comprobar instalación', 'Preparar entorno…', 'Probar ruta sin conexión', 'Consultar catálogo oficial'):
            self.assertNotIn(removed, labels)
        self.assertEqual(labels.count('Importar modelo local'), 1)

    def test_translation_cancel_stale_result_error_and_retry(self):
        self.w.configure_translation(); section = self.w.translation_section
        serial = section.serial
        section.primary.click()
        self.assertEqual(section.state.text(), 'Sin configurar')
        section.finished(serial, 'translation_validate', dict(route=['ja','es'], output='stale', offline_checked=True))
        self.assertNotEqual(section.state.text(), 'Listo')
        section.activate()
        section.task.busy = False
        section.task.error.emit('fixture network failure')
        self.assertEqual(section.state.text(), 'Requiere atención')
        self.assertEqual(section.primary.text(), 'Reparar')
        section.primary.click()
        self.assertEqual(self.calls[-1][1]['action'], 'translation_status')
        self.assertEqual(section.primary.text(), 'Cancelar')

    def test_installed_resources_validate_without_download_and_preserve_default(self):
        self.w.settings['translation_route'] = ['ja','en','es']
        self.w.configure_translation(); section = self.w.translation_section
        self.section_answer(self.empty_translation_report(runtime_error='', installed=[dict(from_code='ja', to_code='es', version='1')], routes=[['ja','es']]))
        self.assertEqual(self.calls[-1][1], dict(action='translation_validate', route=['ja','es']))
        self.assertNotEqual(section.state.text(), 'Listo')
        self.section_answer(dict(route=['ja','es'], input='fixture', output='fixture', offline_checked=True))
        self.assertEqual(section.state.text(), 'Listo')
        self.assertEqual(self.w.settings['translation_route'], ['ja','en','es'])
        self.assertFalse(any(req['action'] in ('translation_catalogue','translation_download') for _,req in self.calls))

    def test_model_removal_refreshes_popup_automatically(self):
        p = self.popup()
        self.answer(p, p.translate_task, dict(routes=[['ja','es']], errors=[], detail='fixture'))
        p.debounce.stop()
        directory = Path(os.environ['XDG_DATA_HOME'])/'naatik-next/argos/packages/test'
        directory.mkdir(parents=True); metadata = directory/'metadata.json'; metadata.write_text('{}')
        p.check_models()
        self.assertEqual(self.calls[-1][1]['action'], 'routes')
        self.answer(p, p.translate_task, dict(routes=[], errors=[], detail='fixture'))
        p.debounce.stop(); metadata.unlink(); p.check_models()
        self.assertEqual(self.calls[-1][1]['action'], 'routes')
        self.assertTrue(p.prepare_translation.isVisible())


class PopupWorkerTests(unittest.TestCase):
    def test_real_worker_missing_argos_and_exact_dictionary_contract(self):
        with tempfile.TemporaryDirectory(prefix='next-popup-worker-') as tmp, patch.dict(os.environ,
                {k:tmp+'/'+k for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','ARGOS_PACKAGES_DIR','ARGOS_TRANSLATE_PACKAGE_DIR')}):
            # Inherited/global Argos locations must not be discovered by Next.
            foreign=Path(tmp)/'foreign-packages/broken'
            foreign.mkdir(parents=True)
            (foreign/'metadata.json').write_text('invalid external package')
            os.environ['ARGOS_PACKAGES_DIR']=str(foreign.parent)
            os.environ['ARGOS_TRANSLATE_PACKAGE_DIR']=str(foreign.parent)
            t=Task(persistent=True); answers=[]; errors=[]
            t.result.connect(answers.append);t.error.connect(errors.append)
            try:
                t.start(dict(action='routes',popup_generation='1'))
                spin_until(lambda: bool(answers) or bool(errors))
                self.assertFalse(errors)
                self.assertEqual(answers[-1]['popup_generation'],'1')
                self.assertEqual(answers[-1]['value']['routes'],[])
                t.start(dict(action='popup_lookup',term='日本',surface='日本',popup_generation='2'))
                spin_until(lambda: len(answers)==2 or bool(errors))
                self.assertEqual(answers[-1]['value'],dict(active=0,results=[]))
            finally:t.close()

    def test_owned_analyzer_real_when_prepared(self):
        program=Path(__file__).resolve().parents[1]/'.venv-phrase/bin/python'
        if not program.exists(): self.skipTest('Prepare the optional Next phrase environment for real analysis')
        with tempfile.TemporaryDirectory(prefix='next-real-phrase-') as tmp, patch.dict(os.environ,
                {k:tmp+'/'+k for k in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
            t=Task(persistent=True,program=str(program),module='naatik_next.phrase_worker')
            answers=[]; errors=[];t.result.connect(answers.append);t.error.connect(errors.append)
            try:
                for text in ('私は日本語を勉強しています。','未知語XYZ🦊','日本\n  日本語'):
                    count=len(answers)
                    t.start(dict(action='phrase',text=text,popup_generation=str(count)))
                    spin_until(lambda: len(answers)>count or bool(errors))
                    self.assertFalse(errors)
                    value=answers[-1]['value']
                    self.assertEqual(value['sentence'],text)
                    for token in value['tokens']:
                        self.assertEqual(text[token['start']:token['end']],token['surface'])
                        self.assertNotIn('jlpt',token)
                        if token['unknown']:self.assertEqual(token['reading'],'')
                    if count==0:
                        self.assertTrue(any(t['reading'] for t in value['tokens']))
                        pid=t.process.processId()
                    else:self.assertEqual(t.process.processId(),pid)
            finally:t.close()

    def test_real_offscreen_popup_boot_residency_and_later_main_window(self):
        import subprocess
        code=r'''
import os
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from naatik_next.app import Window,main
class Broker:
 def __init__(self,*args):self.server=self
 def acquire_or_forward(self,*args):return True
 def set_handler(self,*args):pass
 def close(self):pass
class Probe(Window):
 def __init__(self,**kwargs):
  super().__init__(**kwargs)
  self.test_timer=QTimer(self);self.test_timer.timeout.connect(self.check);self.test_timer.start(10)
  self.step=0
 def prepare_selected(self):
  assert self.isVisible(), 'Popup boot must not prepare OCR'
  self.ocr_deferred=False
 def redetect_argos(self):pass
 def check(self):
  mode=os.environ['POPUP_MODE']
  if mode not in self.popups:return
  p=self.popups[mode]
  if self.step==0:
   assert not self.isVisible() and p.isVisible()
   assert p.editor.toPlainText()=='日本'
   assert not self.capture_task.busy and not self.manga_task.busy
   p.close()
   assert not QApplication.instance().quitOnLastWindowClosed()
   assert not p.isVisible()
   QApplication.clipboard().setText('')
   self.external_command(mode)
   assert self.popups[mode] is p and p.editor.toPlainText()==''
   other='phrase' if mode=='translator' else 'translator'
   self.external_command(other)
   assert len(self.popups)==2 and not self.isVisible()
   self.external_command('show')
   assert self.isVisible()
   self.step=1
   print('popup-only boot, reuse, empty clipboard, residency and later GUI: PASS',flush=True)
   self.close()
 def closeEvent(self,event):
  super().closeEvent(event)
original=QApplication
class Application(QApplication):
 def __init__(self,*args):
  super().__init__(*args);self.clipboard().setText('日本')
  QTimer.singleShot(5000,self.quit)
with patch('naatik_next.app.Instance',Broker),patch('naatik_next.app.Window',Probe),patch('naatik_next.app.QApplication',Application),patch('sys.argv',['launch','--'+os.environ['POPUP_MODE']]):
 raise SystemExit(main())
'''
        for mode in ('translator','phrase'):
            with tempfile.TemporaryDirectory(prefix='next-cold-popup-') as tmp:
                env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1',POPUP_MODE=mode)
                for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
                    env[key]=tmp+'/'+key
                result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                                      env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('residency and later GUI: PASS',result.stdout)
                self.assertNotIn('Traceback',result.stderr)
                self.assertNotIn('Destroyed while process',result.stderr)

    def test_real_popup_dictionary_worker_respects_priority_and_activation(self):
        from naatik_next.storage import Store
        from tests.test_storage import ROW
        import zipfile
        with tempfile.TemporaryDirectory(prefix='next-popup-dictionaries-') as tmp,patch.dict(os.environ,
                {k:tmp+'/'+k for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
            store=Store()
            for title,priority in (('Low',1),('High',10)):
                path=Path(tmp)/(title+'.zip')
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('index.json',json.dumps(dict(format=3,title=title,revision='1')))
                    z.writestr('term_bank_1.json',json.dumps([ROW]))
                store.import_zip(path)
                ident=next(d['id'] for d in store.list() if d['title']==title)
                store.update(ident,True,priority)
            t=Task(persistent=True);answers=[];t.result.connect(answers.append)
            try:
                t.start(dict(action='popup_lookup',term='missing lemma',surface='日本',popup_generation='1'))
                spin_until(lambda:len(answers)==1)
                self.assertEqual([r['title'] for r in answers[-1]['value']['results']],['High','Low'])
                for d in store.list():store.update(d['id'],False,d['priority'])
                t.start(dict(action='popup_lookup',term='日本',surface='日本',popup_generation='2'))
                spin_until(lambda:len(answers)==2)
                self.assertEqual(answers[-1]['value'],dict(active=0,results=[]))
            finally:t.close();store.close()

    def test_local_argos_import_is_managed_deduplicated_and_rejects_traversal(self):
        import zipfile
        from naatik_next.translation import install_package
        from naatik_next.storage import UserError,paths
        with tempfile.TemporaryDirectory(prefix='next-model-import-') as tmp,patch.dict(os.environ,
                {k:tmp+'/'+k for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
            path=Path(tmp)/'synthetic.argosmodel'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('fixture/metadata.json',json.dumps(dict(from_code='ja',to_code='en')))
                z.writestr('fixture/model/config.json','{}')
                z.writestr('fixture/sentencepiece.model','fixture, not a real model')
            with patch('socket.socket.connect',side_effect=AssertionError('No network')):
                install_package(path)
                self.assertIn('ya está',install_package(path)['detail'])
            packages=paths()['data']/'argos/packages'
            self.assertEqual(len(list(packages.iterdir())),1)
            self.assertTrue(next(packages.glob('*/naatik-import.json')).exists())
            with zipfile.ZipFile(path,'w') as z:z.writestr('../outside','no')
            with self.assertRaises(UserError):install_package(path)
            self.assertFalse((Path(tmp)/'outside').exists())
            self.assertEqual(len(list(packages.iterdir())),1)

    def test_real_phrase_popup_analyzes_and_renders_imported_dictionary(self):
        from naatik_next.storage import Store
        from tests.test_storage import ROW
        import zipfile
        program=Path(__file__).resolve().parents[1]/'.venv-phrase/bin/python'
        if not program.exists():self.skipTest('Optional Next-owned phrase runtime absent')
        with tempfile.TemporaryDirectory(prefix='next-real-popup-') as tmp,patch.dict(os.environ,
                {k:tmp+'/'+k for k in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
            store=Store();path=Path(tmp)/'fixture.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('index.json',json.dumps(dict(format=3,title='Popup test dictionary',revision='1')))
                z.writestr('term_bank_1.json',json.dumps([ROW]))
            store.import_zip(path);store.close()
            w=Window(background=True,popup_only=True)
            try:
                APP.clipboard().setText('日本')
                w.external_command('phrase');p=w.popups['phrase']
                spin_until(lambda:bool(p.word_cards))
                p.word_cards[0].toggle.click()
                spin_until(lambda:'Popup test dictionary' in p.definitions.toPlainText())
                self.assertFalse(w.isVisible())
                self.assertTrue(any(token['reading'] for token in p.token_data))
                self.assertIn('Japan',p.definitions.toPlainText())
                self.assertEqual(p.translation.toPlainText(),'')
                self.assertFalse(w.capture_task.busy)
                self.assertFalse(w.manga_task.busy)
                self.assertIsNone(w.capture_task.process)
                self.assertEqual(APP.clipboard().text(),'日本')
                p.editor.setPlainText('猫')
                spin_until(lambda:bool(p.word_cards) and p.token_data[0]['surface']=='猫')
                p.word_cards[0].toggle.click()
                spin_until(lambda:'Sin coincidencias exactas' in p.definitions.toPlainText())
                self.assertEqual(p.editor.toPlainText(),'猫')
                self.assertEqual(APP.clipboard().text(),'日本')
            finally:w.close()

    def test_fresh_source_copy_without_optional_runtime_or_models(self):
        import subprocess
        from tools.public_install_validation import copy_source
        root=Path(__file__).resolve().parents[1]
        code=r'''
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from naatik_next.app import Window
from tests.test_processes import spin_until
app=QApplication.instance() or QApplication([])
w=Window(background=True,popup_only=True)
try:
 app.clipboard().setText('日本')
 w.external_command('phrase');p=w.popups['phrase']
 assert not Path(p.phrase_task.program).exists()
 spin_until(lambda:'Faltan recursos' in p.analysis_status.text() and 'No hay diccionarios activos' in p.dictionary_status.text())
 assert not w.isVisible() and p.isVisible()
 assert not p.route.count() and p.translation.toPlainText()==''
 assert not w.capture_task.busy and not w.manga_task.busy
 assert 'JapaneseMining' not in json.dumps(w.settings)
 print('fresh HOME/XDG/source: explicit missing resources, no OCR or legacy paths',flush=True)
finally:w.close()
'''
        with tempfile.TemporaryDirectory(prefix='next-source-clean-') as tmp:
            d=Path(tmp);source=d/'source';copy_source(root,source)
            self.assertFalse((source/'.venv-phrase').exists())
            self.assertTrue((source/'requirements-phrase.lock').is_file())
            env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1')
            for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
                env[key]=str(d/key)
            result=subprocess.run([sys.executable,'-c',code],cwd=source,env=env,
                                  capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('explicit missing resources',result.stdout)
