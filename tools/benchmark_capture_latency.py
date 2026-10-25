"""Real configured OCR, bundled image; offscreen selector/IPC injection. No user content output."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


def child(args):
    sys.path.insert(0, str(args.source_root))
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from naatik_next.app import Window
    from naatik_next.processes import Task
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    png = base64.b64encode((args.source_root / 'examples/nihon.png').read_bytes()).decode()
    state = {}
    failures = []
    started = int(os.environ['NAATIK_BENCH_STARTED_NS']) / 1e9
    original = Task.start
    def spin(predicate):
        deadline = time.monotonic() + 90
        while not predicate():
            app.processEvents()
            time.sleep(.001)
            if time.monotonic() > deadline:
                raise RuntimeError('Benchmark deadline; no content retained')
    def start(task, request, timeout=120000):
        if request['action'] == 'capture':
            state['selector'] = time.monotonic()
            def finish():
                state['selection_end'] = time.monotonic()
                task.result.emit(png)
            QTimer.singleShot(150, finish)
            return
        if request['action'] == 'ocr':
            state['inference'] = time.monotonic()
        return original(task, request, timeout)
    rows = []
    with patch.object(Task, 'start', start), patch.object(Window, 'fail', lambda self,msg:failures.append(True)), \
            patch.object(Window, 'notify_configuration', lambda self,msg:failures.append(True)):
        window = Window(background=args.scenario == 'cold')
        if args.scenario == 'open':
            window.show()
            spin(lambda: window.external_capture_ready() and bool(window.engines)
                 and not window.manga_task.busy and not window.detect_task.busy)
        for index in range(args.resident + 1):
            t0 = started if args.scenario == 'cold' and index == 0 else time.monotonic()
            state.clear()
            app.clipboard().setText('benchmark sentinel')
            window.external_command('capture-copy')
            spin(lambda: app.clipboard().text() == '日本' or bool(failures))
            if failures:
                raise RuntimeError('Benchmark failed; no OCR content logged')
            end = time.monotonic()
            rows.append(dict(scenario=args.scenario if index == 0 else 'resident-'+args.scenario,
                             total_ms=(end-t0)*1000, selector_ms=(state['selector']-t0)*1000,
                             selection_ms=(state['selection_end']-state['selector'])*1000,
                             ocr_roundtrip_ms=(end-state['inference'])*1000, text_matches=True))
        window.close()
    print(json.dumps(rows), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--resident', type=int, default=3)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--scenario', choices=('cold','open'), default='cold', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.source_root = args.source_root.resolve()
    if args.child:
        return child(args)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from naatik_next.storage import load_settings
    settings = load_settings()
    settings.update(setup_completed=True, capture_shortcut_enabled=False)
    rows = []
    for scenario in ('cold','open'):
        for run in range(args.runs):
            with tempfile.TemporaryDirectory(prefix='next-latency-') as tmp:
                env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1', NAATIK_TIMINGS='0')
                for key in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
                    env[key] = str(Path(tmp)/key)
                config = Path(env['XDG_CONFIG_HOME'])/'naatik-next'
                config.mkdir(parents=True)
                (config/'settings.json').write_text(json.dumps(settings))
                env['NAATIK_BENCH_STARTED_NS'] = str(time.monotonic_ns())
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', '--scenario', scenario,
                                         '--source-root', str(args.source_root), '--resident', str(args.resident)],
                                        cwd=args.source_root, env=env, capture_output=True, text=True, timeout=120)
                if result.returncode:
                    raise RuntimeError('Benchmark child failed (stderr withheld to avoid user content).')
                sample = json.loads(result.stdout.splitlines()[-1])
                rows.extend(dict(row, trial=run) for row in sample)
                print(f'{scenario} run {run+1}/{args.runs} completed', file=sys.stderr, flush=True)
    data = json.dumps(rows, indent=2)
    if args.output:
        args.output.write_text(data+'\n')
    else:
        print(data)


if __name__ == '__main__':
    main()
