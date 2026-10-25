"""Synthetic visual review in temporary HOME/XDG. Never starts processing workers."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    target=Path(__file__).resolve().parent.parent/'docs/evidence/appearance'
    target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='next-appearance-review-') as root:
        with patch.dict(os.environ,{key:root+'/'+key for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
            from PySide6.QtWidgets import QApplication
            from naatik_next.app import Window
            from naatik_next.processes import Task
            app=QApplication.instance() or QApplication([])
            with patch.object(Task,'start'),patch('naatik_next.app.QTimer.singleShot'):
                window=Window(background=True,popup_only=True)
                section=window.appearance_section
                window.resize(1100,1100)
                page=next(window.tabs.widget(i) for i in range(window.tabs.count()) if window.tabs.tabText(i)=='Apariencia')
                window.tabs.setCurrentWidget(page);window.show()
                for theme in ('light','dark'):
                    section.theme.setCurrentIndex(section.theme.findData(theme));section.save()
                    app.processEvents();window.grab().save(str(target/(theme+'-settings.png')))
                    for mode in ('translator','phrase'):
                        window.external_command(mode);popup=window.popups[mode]
                        popup.editor.setPlainText('日本語の文字を読みます。');popup.debounce.stop()
                        popup.translation.setPlainText('Muestra de traducción · contenido sintético')
                        popup.analysis_status.setText('Muestra visual · no se ejecutó análisis')
                        app.processEvents();popup.grab().save(str(target/(theme+'-'+mode+'.png')));popup.hide()
                window.close();app.processEvents()
    print('PASS: synthetic light/dark settings and both popups; temporary profile; no workers')


if __name__=='__main__':main()
