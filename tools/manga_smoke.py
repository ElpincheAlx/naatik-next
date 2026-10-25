"""Offscreen Qt supervision with REAL MangaOCR load/inference/cancel/reload/close."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import json
import tempfile
import time
from unittest.mock import patch
from PySide6.QtCore import QTimer, QProcess
from PySide6.QtGui import QImage
from tests.test_processes import APP, spin_until
from naatik_next.app import Window
from naatik_next.storage import load_settings


def main():
    with tempfile.TemporaryDirectory(prefix='naatik-manga-smoke-') as tmp:
        with patch.dict(os.environ, {key: str(Path(tmp) / key) for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME']}):
            w = Window()
            errors = []
            for task in w.tasks:
                if task is w.capture_task:
                    task.error.disconnect(w.capture_failed)
                elif task is w.import_task:
                    task.error.disconnect(w.import_failed)
                elif task is w.inspect_task:
                    task.error.disconnect(w.inspection_failed)
                elif task is not w.selection_task:
                    task.error.disconnect(w.fail)
                task.error.connect(errors.append)
            w.show()
            beats = []
            timer = QTimer()
            timer.timeout.connect(lambda: beats.append(time.monotonic()))
            timer.start(10)
            try:
                spin_until(lambda: not any(t.busy for t in w.tasks) and bool(w.engines), 120)
                status = next(e for e in w.engines if e['id'] == 'mangaocr')
                assert status['status'] == 'listo', status
                assert next(e for e in w.engines if e['id'] == 'paddleocr')['status'] == 'incompatible'
                assert not errors, errors
                w.engine.setCurrentIndex(w.engine.findData('mangaocr'))
                assert not w.ocr_language.isEnabled()
                assert load_settings()['ocr_engine'] == 'mangaocr'
                image_path = Path(__file__).resolve().parent.parent / 'examples/nihon.png'
                w.set_image(QImage(str(image_path)), 'Prueba MangaOCR real 日本')
                pid = w.manga_task.process.processId()
                w.recognize()
                spin_until(lambda: not w.manga_task.busy, 60)
                assert w.raw_text == '日本', w.raw_text
                assert w.editor.toPlainText() == '日本'
                assert w.manga_task.process.processId() == pid, 'Model was needlessly reloaded'
                # Real process cancellation immediately after starting a second inference.
                w.recognize()
                w.manga_task.cancel()
                spin_until(lambda: not w.manga_task.busy, 15)
                assert errors and 'cancelada' in errors[-1], errors
                assert w.engine.currentData() == 'mangaocr', 'Silent fallback'
                assert w.manga_status['status'] == 'error'
                assert w.manga_task.process.state() == QProcess.NotRunning
                errors.clear()
                w.redetect()
                spin_until(lambda: not any(t.busy for t in w.tasks), 120)
                assert w.manga_status['status'] == 'listo', w.manga_status
                assert w.engine.currentData() == 'mangaocr'
                w.recognize()
                spin_until(lambda: not w.manga_task.busy, 60)
                assert w.raw_text == '日本'
                assert not errors, errors
                assert len(beats) > 10
                print(json.dumps({'engine': status, 'real_inference': w.raw_text,
                    'persistent_worker_pid_reused': True, 'cancel_and_reload': 'passed',
                    'no_fallback': True, 'heartbeat_ticks': len(beats),
                    'scope': 'Qt offscreen and real MangaOCR; no interactive screen capture'}, ensure_ascii=False, indent=2))
            finally:
                timer.stop()
                w.close()
                assert all(not t.process or t.process.state() == QProcess.NotRunning for t in w.tasks)


if __name__ == '__main__':
    main()
