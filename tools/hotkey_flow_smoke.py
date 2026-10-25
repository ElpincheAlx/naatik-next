"""Offscreen hotkey orchestration with injected capture and REAL Tesseract OCR.

Not a global-key registration test or interactive screen capture.
"""
import base64
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
from unittest.mock import patch
from naatik_next.app import Window
from naatik_next.ocr import Tesseract
from tests.test_processes import APP, spin_until


def main():
    with tempfile.TemporaryDirectory(prefix='naatik-hotkey-flow-') as tmp:
        with patch.dict(os.environ, {k: str(Path(tmp) / k) for k in
                        ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME')}):
            with patch('naatik_next.app.QTimer.singleShot'):
                w = Window()
            errors = []
            w.ocr_task.error.disconnect(w.fail)
            w.ocr_task.error.connect(errors.append)
            try:
                info = Tesseract().detect()
                assert info['status'] == 'listo', info
                w.detected([info])
                w.ocr_language.setCurrentText('jpn')
                assert w.ocr_language.currentText() == 'jpn'
                with patch.object(w, 'isActiveWindow', return_value=False):
                    w.shortcut.activated.emit()  # Injected activation; not a real global key.
                assert w.capture_active
                w.capture_delay.stop()
                image = Path(__file__).resolve().parents[1] / 'examples/nihon.png'
                w.capture_task.result.emit(base64.b64encode(image.read_bytes()).decode())
                assert w.ocr_task.busy
                spin_until(lambda: not w.ocr_task.busy)
                assert not errors, errors
                assert w.raw_text == '日本', w.raw_text
                assert w.editor.toPlainText() == '日本'
                assert not w.argos_task.busy and not w.translation.toPlainText()
                w.tabs.setCurrentWidget(w.integrations_tab)
                w.show()
                APP.processEvents()
                w.grab().save('/tmp/naatik-hotkey-integrations.png')
                print(json.dumps({'mode': 'Qt offscreen; activation/capture injected; real OCR',
                                  'engine': info['id'], 'probe': info['detail'], 'language': 'jpn',
                                  'raw_ocr': w.raw_text, 'editor': w.editor.toPlainText(),
                                  'translation_started': False,
                                  'global_registration_validated': False,
                                  'interactive_capture_validated': False}, ensure_ascii=False, indent=2))
            finally:
                w.close()


if __name__ == '__main__':
    main()
