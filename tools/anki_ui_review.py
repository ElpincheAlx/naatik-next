"""Synthetic offscreen review; no HTTP, collections, models or normal Next profile."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    target=Path(__file__).resolve().parent.parent/'docs/evidence/anki-implementation'
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='next-anki-ui-') as root:
        with patch.dict(os.environ,{key:root+'/'+key for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME')}):
            from PySide6.QtWidgets import QApplication,QWidget,QTabWidget,QVBoxLayout
            from naatik_next.anki_ui import AnkiSection
            app=QApplication.instance() or QApplication([])
            owner=QWidget(); owner.settings={}; owner.tasks=[]; owner.closing=False
            owner.interrupted=lambda:False; owner.persist=lambda:None; owner.tabs=QTabWidget()
            layout=QVBoxLayout(owner); layout.addWidget(owner.tabs)
            section=AnkiSection(owner); section.parent_scroll=section; owner.tabs.addTab(section,'Anki')
            owner.resize(850,850); owner.show(); app.processEvents()
            owner.grab().save(str(target/'setup-synthetic.png'))
            # Injected metadata is deliberately synthetic; do not start the worker.
            section.run=lambda *args,**kwargs:None
            section.operation='check'; section.completed(dict(decks=['Mazo sintético de revisión'],models=['Tipo sintético']))
            section.deck.setCurrentIndex(1); section.model.setCurrentIndex(1)
            section.operation='fields'; section.completed(dict(fields=['Expresión de prueba','Contenido de prueba']))
            section.mapping['Expresión de prueba'].setCurrentIndex(section.mapping['Expresión de prueba'].findData('sentence'))
            section.save_config()
            section.open_draft(dict(sentence='日本を読む。',translation='Texto sintético · no inferencia real'))
            app.processEvents(); section.drafts[-1].grab().save(str(target/'preview-synthetic.png'))
            for draft in section.drafts: draft.close()
            for task in owner.tasks: task.close()
            owner.close()
    print(json.dumps(dict(review='synthetic offscreen',http_requests=0,collection_access=False,artifacts=str(target)),ensure_ascii=False))


if __name__=='__main__': main()
