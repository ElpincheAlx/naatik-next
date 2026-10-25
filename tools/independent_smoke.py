"""Run ONLY with a new explicit HOME/XDG; real host Tesseract, Qt offscreen."""
import hashlib
import json
import os
from pathlib import Path
import site
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from naatik_next.app import Window
from naatik_next.manga import defaults
from naatik_next.storage import load_settings, paths


def main():
    # Refuse an accidental test on the actual user profile.
    assert os.environ.get('NAATIK_ISOLATED_REVIEW') == '1'
    assert 'independent-install' in str(Path.home()) or '/Naatik-validation/public-install-' in str(Path.home())
    assert not site.ENABLE_USER_SITE
    assert sys.prefix != sys.base_prefix
    assert all('JapaneseMining' not in p for p in sys.path)
    assert not Path(defaults()['manga_model']).exists()
    app = QApplication([])
    beats = []
    timer = QTimer(); timer.timeout.connect(lambda: beats.append(time.monotonic())); timer.start(10)
    def wait(callback, seconds=60):
        until = time.monotonic() + seconds
        while not callback():
            app.processEvents()
            if time.monotonic() > until: raise TimeoutError('offscreen task')
            time.sleep(.01)
    w = Window(); errors=[]
    w.fail = errors.append
    w.show()
    wait(lambda: not any(t.busy for t in w.tasks) and bool(w.engines))
    assert w.tutorial_dialog.isVisible()
    w.tutorial_dialog.skip()
    w.show_setup()
    assert w.setup_dialog.isVisible()
    # An unused optional engine need not be probed on first launch.
    assert w.manga_status is None or w.manga_status['status']=='recursos faltantes', w.manga_status
    assert w.routes==[],w.routes
    assert w.store.list()==[]
    dialog=w.setup_dialog
    dialog.engine.setCurrentIndex(dialog.engine.findData('tesseract'))
    dialog.language.setCurrentIndex(dialog.language.findData('eng'))
    dialog.save()
    wait(lambda: not any(t.busy for t in w.tasks))
    assert load_settings()['setup_completed'] is True
    assert w.engine.currentData()=='tesseract'
    assert w.ocr_language.currentText()=='eng'
    w.set_image(QImage(str(Path(__file__).resolve().parent.parent/'examples/hello.png')), 'isolated synthetic sample')
    w.recognize()
    wait(lambda: not any(t.busy for t in w.tasks))
    assert 'Hello world' in w.raw_text,w.raw_text
    assert not errors,errors
    ocr=w.raw_text
    w.close(); app.processEvents()
    w2=Window();w2.show()
    wait(lambda:not any(t.busy for t in w2.tasks) and bool(w2.engines))
    assert not hasattr(w2,'setup_dialog')
    assert w2.settings['ocr_engine']=='tesseract' and w2.settings['ocr_language']=='eng'
    w2.close();app.processEvents()
    download = 'Not attempted: optional models require explicit preparation and confirmation.'
    report={'home':str(Path.home()),'prefix':sys.prefix,'user_site':site.ENABLE_USER_SITE,
        'xdg':{k:str(v) for k,v in paths().items()},'manga_defaults':defaults(),
        'first_run_dialog':True,'save_language_and_engine':True,'second_run':True,
        'no_argos_models':True,'no_dictionaries':True,'no_preloaded_manga_model':True,
        'actual_tesseract_result':ocr,'qt_event_beats':len(beats),'download_attempt':download,
        'qt':'offscreen; no actual capture/global shortcut/IPC validation',
        'host_executables_and_libraries_remain_dependencies':True}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
