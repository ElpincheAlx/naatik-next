"""Render synthetic ES/EN screens in temporary profiles; never prepares resources."""
import argparse
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from PySide6.QtWidgets import QApplication
    from naatik_next.app import Window
    from naatik_next.processes import Task
    from naatik_next.storage import save_settings
    from naatik_next.i18n import choose_language
    app=QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    for code in ('es','en'):
        with tempfile.TemporaryDirectory(prefix='next-bilingual-review-') as root:
            with patch.dict(os.environ,{key:root+'/'+key for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME')}):
                save_settings({'ui_language':code,'tutorial':{'status':'pending','step':0}})
                with patch.object(Task,'start'),patch('naatik_next.app.QTimer.singleShot'):
                    window=Window(startup_action='capture');window.resize(1250,1000);window.show()
                    for index in range(window.tabs.count()):
                        window.tabs.setCurrentIndex(index);app.processEvents()
                        window.grab().save(str(args.output/f'{code}-tab-{index}.png'))
                    window.tabs.setCurrentIndex(0)
                    window.show_tutorial();dialog=window.tutorial_dialog
                    for step in range(6):
                        dialog.step=step;dialog.render();app.processEvents()
                        dialog.grab().save(str(args.output/f'{code}-tutorial-{step}.png'))
                    dialog.close()
                    window.show_setup();app.processEvents()
                    window.setup_dialog.grab().save(str(args.output/f'{code}-ocr-setup.png'))
                    window.setup_dialog.hide()
                    from PySide6.QtWidgets import QDialog
                    def review_language(dialog):
                        dialog.show();app.processEvents()
                        dialog.grab().save(str(args.output/f'{code}-language.png'))
                        dialog.hide()
                        return QDialog.Rejected
                    with patch.object(QDialog,'exec',review_language):
                        choose_language(window,code)
                    for mode in ('translator','phrase'):
                        window.external_command(mode);popup=window.popups[mode]
                        popup.editor.setPlainText('日本語の文字を読みます。');popup.debounce.stop()
                        app.processEvents();popup.grab().save(str(args.output/f'{code}-{mode}.png'));popup.hide()
                    window.shutdown();window.close();app.processEvents()
    print('Rendered ES/EN offscreen screens. Workers suppressed; no capture or shortcut qualification.')


if __name__=='__main__':main()
