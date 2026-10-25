#!/usr/bin/env python3
"""Isolated, synthetic offscreen UI comparison. Never starts legacy backends.

Only explicitly allowlisted presentation methods are extracted from a user
supplied review snapshot. No module top level, constructor of a legacy window,
worker, engine, launch command, network code or dictionary lookup is executed.
The production application never reads this reference.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path, help='Reviewed fuentes/JapaneseMining directory')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    # Establish isolation before importing any Qt/Next/Argos module.
    with tempfile.TemporaryDirectory(prefix='next-visual-review-') as tmp:
        for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR'):
            os.environ[key] = tmp+'/'+key; Path(os.environ[key]).mkdir(mode=0o700)
        os.environ['QT_QPA_PLATFORM']='offscreen'
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from PySide6 import QtCore, QtGui, QtWidgets
        from unittest.mock import patch
        from naatik_next.processes import Task
        from naatik_next.app import Window
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        namespace = {name:getattr(module,name) for module in (QtCore,QtGui,QtWidgets)
                     for name in dir(module) if name.startswith('Q') or name in ('Qt','Slot')}
        namespace['Any']=object
        hashes={}

        def extract(file, class_name, methods=None):
            source=args.reference/file; hashes[file]=hashlib.sha256(source.read_bytes()).hexdigest()
            tree=ast.parse(source.read_text())
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name)
            if methods is not None: cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in methods]
            module=ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[]))
            exec(compile(module, str(source)+' [UI-only allowlist]', 'exec'), namespace)
            return namespace[class_name]

        tf='translator_popup_qt.py'; pf='phrase_popup_qt.py'
        extract(tf,'Badge'); extract(tf,'ReadOnlyText'); extract(tf,'DraggableHeader')
        extract(pf,'SelectableLabel',{'__init__'})
        namespace['SelectableLabel'].open_context_menu=lambda *a:None
        card=extract(pf,'TokenCard',{'__init__'})
        def toggle_body(self,checked):
            self.toggle.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
            self.body.setVisible(checked)
        card.toggle_body=toggle_body
        originals={}
        tokens=[dict(surface='日本',base='日本',reading='にほん',hiragana='にほん',pos='名詞',start=0,end=2,unknown=False),
                dict(surface='語',base='語',reading='ご',hiragana='ご',pos='名詞',start=2,end=3,unknown=False),
                dict(surface='勉強',base='勉強',reading='べんきょう',hiragana='べんきょう',pos='名詞',start=4,end=6,unknown=False)]
        sentence='日本語を勉強しています。'
        for mode,file,clsname in [('translator',tf,'TranslatorPopupQt'),('phrase',pf,'PhrasePopupQt')]:
            cls=extract(file,clsname,{'build_interface','apply_qss','adjust_furigana_height'})
            # Bypass original __init__ entirely. All external actions are inert.
            cls.safe_text=staticmethod(lambda value:str(value or ''))
            for callback in ('copy_original','copy_text','send_selection_to_anki','send_full_phrase_to_anki'):
                setattr(cls,callback,lambda *a:None)
            cls.detect_jlpt_level=lambda self:''; cls.build_grammar_text=lambda *a:''
            old=cls(); old.data=dict(sentence=sentence,furigana_text='日本(にほん)語(ご)を勉強(べんきょう)しています。',
                                    translation='I am studying Japanese. [synthetic fixture]',tokens=tokens)
            old.resize(720,840); old.build_interface(); old.apply_qss()
            if mode=='translator':
                old.editor.setPlainText(sentence)
                old.furigana_text.setPlainText(old.data['furigana_text'])
                old.translation_text.setPlainText(old.data['translation'])
            else:
                first=old.findChildren(card)[0]
                first.status.setText('日本 · にほん\nSynthetic dictionary fixture: Japan.')
                first.toggle.setChecked(True); first.toggle_body(True)
            old.show(); app.processEvents(); originals[mode]=old
        def no_work(task,request,*a,**kw): task.busy=True
        with patch.object(Task,'start',autospec=True,side_effect=no_work), patch('naatik_next.app.QTimer.singleShot'):
            owner=Window(background=True,popup_only=True)
            for mode,old in originals.items():
                app.clipboard().setText(sentence); owner.external_command(mode); new=owner.popups[mode]
                new.debounce.stop(); new.route.blockSignals(True); new.route.addItem('ja → en',['ja','en']); new.route.blockSignals(False)
                new.show_analysis(dict(sentence=sentence,tokens=tokens,resource='Synthetic UI fixture; no inference'))
                new.analysis_status.setText('Lecturas de ejemplo · sin gramática/JLPT')
                new.translation.setPlainText(old.data['translation']); new.translation_status.setText('Traducción de ejemplo; sin inferencia neural')
                if mode=='phrase':
                    new.word_cards[0].toggle.click()
                    new.definitions.setPlainText('日本 · にほん\nSynthetic dictionary fixture: Japan.')
                    new.dictionary_status.setText('Diccionario sintético')
                new.resize(720,840); app.processEvents()
                old.grab().save(str(args.output/(mode+'-reference.png')))
                new.grab().save(str(args.output/(mode+'-next.png')))
                # Side by side at native logical size, identical platform/font/DPI.
                canvas=QtGui.QPixmap(1440,840); canvas.fill(QtCore.Qt.white)
                painter=QtGui.QPainter(canvas); painter.drawPixmap(0,0,old.grab()); painter.drawPixmap(720,0,new.grab()); painter.end()
                canvas.save(str(args.output/(mode+'-comparison.png')))
            owner.close()
        report=dict(kind='offscreen synthetic UI-only reference, not interactive legacy or desktop validation',
                    reference_sha256=hashes,qt=QtCore.qVersion(),logical_size=[720,840],
                    font=app.font().family(),logical_dpi=app.primaryScreen().logicalDotsPerInch(),screenshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.glob('*.png')})
        (args.output/'visual-review.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))


if __name__=='__main__': main()
