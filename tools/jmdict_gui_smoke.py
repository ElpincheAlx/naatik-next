"""Real JMdict ZIP through offscreen GUI/processes, in isolated XDG data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import hashlib
import json
import tempfile
import time
from unittest.mock import patch
from PySide6.QtCore import QTimer
from tests.test_processes import APP, spin_until
from naatik_next.app import Window


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', required=True, type=Path, help='Explicit JMdict v3 ZIP fixture; never discovered automatically')
    source = parser.parse_args().dictionary.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='naatik-jmdict-gui-') as tmp:
        with patch.dict(os.environ, {**{key: str(Path(tmp) / key) for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME']},
              'ARGOS_PACKAGES_DIR': str(Path(tmp) / 'argos-packages')}):
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
            timer = QTimer()
            ticks = []
            timer.timeout.connect(lambda: ticks.append(time.monotonic()))
            timer.start(10)
            try:
                spin_until(lambda: not any(t.busy for t in w.tasks) and bool(w.engines), 120)
                before = len(ticks)
                w.import_task.start({'action': 'import', 'path': str(source)}, 600000)
                spin_until(lambda: not w.import_task.busy, 180)
                during_import = len(ticks) - before
                assert during_import > 10
                assert w.table.rowCount() == 1
                assert w.table.item(0, 2).text() == '513033'
                w.query.setText('日本')
                w.lookup()
                spin_until(lambda: not w.lookup_task.busy)
                text = w.definitions.toPlainText()
                assert all(value in text for value in ['Japan', 'にほん', 'にっぽん', 'Japan is to the east of China.', 'Diccionario:'])
                assert w.definitions.document().rootFrame().childFrames(), 'Missing rich table'
                assert not w.translation.toPlainText(), 'Dictionary lookup became phrase translation'
                assert not errors, errors
                w.tabs.setCurrentIndex(1)
                APP.processEvents()
                w.grab().save(str(Path(__file__).resolve().parent.parent / 'docs/jmdict-gui.png'))
                ident = w.store.list()[0]['id']
                w.dictionary_action_task.start({'action': 'remove', 'id': ident}, 120000)
                spin_until(lambda: not w.dictionary_action_task.busy, 60)
                assert w.table.rowCount() == 0
                # Actual ZIP import cancellation after at least 1 000 inserts.
                def cancel_on_progress(message):
                    w.import_task.cancel()
                w.import_task.progress.connect(cancel_on_progress)
                w.import_task.start({'action': 'import', 'path': str(source)}, 600000)
                spin_until(lambda: not w.import_task.busy, 60)
                assert errors and 'cancelada' in errors[-1]
                assert w.store.list() == []
                assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
                print(json.dumps({'real_gui_import': 513033, '日本_readings_and_examples_rendered': True,
                    'dictionary_separate_from_translation': True, 'async_remove': 'passed',
                    'real_import_cancel_rollback': 'passed', 'heartbeat_during_import': during_import,
                    'original_unchanged': True, 'scope': 'offscreen Qt and real ZIP; no interactive capture'}, ensure_ascii=False, indent=2))
            finally:
                timer.stop()
                w.close()


if __name__ == '__main__':
    main()
