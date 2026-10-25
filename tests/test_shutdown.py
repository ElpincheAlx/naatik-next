"""Real Unix signals/Qt/QProcess, synthetic stages; isolated before application imports."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]

CHILD = r'''
import resource
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
import os
from pathlib import Path
from unittest.mock import patch
from naatik_next.app import Window, main
from naatik_next import timings
class Broker:
 def __init__(self, *args): self.server = self
 def acquire_or_forward(self, *args, **kwargs): return True
 def set_handler(self, *args): pass
 def close(self): Path(os.environ['FIXTURE_ROOT'], 'broker-closed').touch()
class Probe(Window):
 def __init__(self, **kwargs):
  with patch('naatik_next.app.QTimer.singleShot'): super().__init__(**kwargs)
  self.capture_trace = '1' * 32
  timings.event('request', self.capture_trace)
  phase = os.environ['FIXTURE_PHASE']
  self.capture_active = phase != 'idle'
  if phase == 'idle': timings.event('clipboard', self.capture_trace)
  task = {'load': self.manga_task, 'capture': self.capture_task,
          'inference': self.ocr_task, 'idle': self.detect_task}[phase]
  task.program = os.environ['FIXTURE_PROGRAM']
  # Main-thread readiness, after the actual worker/tool has reached its barrier.
  task.progress.connect(lambda _: Path(os.environ['FIXTURE_ROOT'], 'ready').touch())
  task.start({'action': 'fixture'})
with patch('naatik_next.app.Instance', Broker), patch('naatik_next.app.Window', Probe), \
     patch('sys.argv', ['launch', '--capture-copy', '--timings']):
 raise SystemExit(main())
'''

WORKER = r'''
import json, os, signal, sys
from contextlib import nullcontext
from pathlib import Path
from naatik_next.ocr import stop, run
from naatik_next.selection_timing import DragTimer
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, signal.SIG_IGN if os.environ.get('FIXTURE_STUBBORN') == '1' else stop)
d = Path(os.environ['FIXTURE_ROOT'])
(d / 'worker-pid').write_text(str(os.getpid()))
for line in sys.stdin:
 if os.environ['FIXTURE_PHASE'] == 'idle':
  print(json.dumps({'progress': 'barrier', 'result': []}), flush=True)
 else:
  # The tool announces readiness through stdout of the worker, not run's pipe.
  with (DragTimer('1' * 32) if os.environ['FIXTURE_PHASE'] == 'capture' else nullcontext()) as observer:
   if observer and observer.process: (d / 'observer-pid').write_text(str(observer.process.pid))
   run([sys.executable, str(d / 'tool.py')], timeout=120)
'''

TOOL = r'''
import os, signal, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
d = Path(os.environ['FIXTURE_ROOT'])
(d / 'tool-pid').write_text(str(os.getpid()))
# Parent worker stdout is a pipe into QProcess; inherit its fd via /proc.
with open('/proc/%s/fd/1' % os.getppid(), 'w') as stream:
 stream.write('{"progress":"barrier"}\n'); stream.flush()
stderr = os.open('/proc/%s/fd/2' % os.getppid(), os.O_WRONLY)
while True:
 os.write(stderr, b'fixture stderr pulse\n')
 time.sleep(.005)
'''


class ShutdownIntegrationTests(unittest.TestCase):
    def test_signals_at_each_stage(self):
        for phase in ('load', 'capture', 'inference', 'idle'):
            for first in (signal.SIGINT, signal.SIGTERM):
                with self.subTest(phase=phase, signal=first):
                    self.scenario(phase, first)

    def test_stuck_worker_and_tools_are_killed_as_a_group(self):
        self.scenario('capture', signal.SIGINT, stubborn=True)

    def scenario(self, phase, first, stubborn=False):
        with tempfile.TemporaryDirectory(prefix='next-shutdown-test-') as tmp:
            d = Path(tmp)
            (d/'worker.py').write_text('import sys; sys.path.insert(0, ' + repr(str(ROOT)) + ')\n' + WORKER)
            (d/'tool.py').write_text(TOOL)
            # Shell quoting retains interpreters/paths with spaces.
            import shlex
            program = d/'worker with spaces'
            program.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -u ' +
                               shlex.quote(str(d/'worker.py')) + '\n')
            program.chmod(0o700)
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONFAULTHANDLER='1',
                       PYTHONDONTWRITEBYTECODE='1', FIXTURE_ROOT=tmp, FIXTURE_PHASE=phase,
                       FIXTURE_PROGRAM=str(program), FIXTURE_STUBBORN='1' if stubborn else '0')
            for key in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
                env[key] = str(d/key)
            p = subprocess.Popen([sys.executable, '-c', CHILD], cwd=ROOT, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            descendants = []
            try:
                end = time.monotonic() + 10
                while not (d/'ready').exists() and p.poll() is None and time.monotonic() < end:
                    time.sleep(.01)
                self.assertTrue((d/'ready').exists(), 'stage not reached')
                descendants = [int(path.read_text()) for path in (d/'worker-pid',d/'tool-pid',d/'observer-pid') if path.exists()]
                # Includes terminal-style process group delivery, then mixed repeated signals.
                for sig in (first, first, signal.SIGTERM, signal.SIGINT):
                    if p.poll() is None:
                        os.killpg(p.pid, sig)
                    time.sleep(.03)
                out, err = p.communicate(timeout=8)
                self.assertEqual(p.returncode, 128 + first, err.decode(errors='replace'))
                for forbidden in (b'KeyboardInterrupt', b'Destroyed while process', b'Traceback',
                                  b'already deleted', b'Segmentation fault'):
                    self.assertNotIn(forbidden, err)
                self.assertTrue((d/'broker-closed').exists())
                for pid in descendants:
                    stat = Path(f'/proc/{pid}/stat')
                    self.assertTrue(not stat.exists() or stat.read_text().split()[2] == 'Z',
                                    f'live orphan {pid}')
                records = [json.loads(s) for s in (d/'XDG_STATE_HOME/naatik-next/capture-timings.jsonl').read_text().splitlines()]
                self.assertEqual(sum(e['stage']=='interrupted' for e in records), 1)
                from tools.capture_timings import captures
                self.assertEqual(captures(records)[0]['state'], 'copied' if phase == 'idle' else 'interrupted')
                if phase != 'idle': self.assertIsNone(captures(records)[0]['total_ms'])
            finally:
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGKILL)
                p.communicate()
                worker = d/'worker-pid'
                if worker.exists():
                    try: os.killpg(int(worker.read_text()), signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_interrupted_and_cancelled_samples_never_count_as_performance(self):
        from tools.capture_timings import captures
        for final in ('interrupted','cancelled','failed'):
            rows = [dict(stage=stage, trace='1'*32, at_ns=n*1000000, pid=1)
                    for n, stage in enumerate(('request','clipboard',final))]
            sample = captures(rows)[0]
            self.assertEqual(sample['state'], final)
            self.assertTrue(sample['clipboard_observed'])
            self.assertIsNone(sample['total_ms'])

    def test_signals_close_both_real_popup_lifecycles_and_their_workers(self):
        code=r'''
import os,json
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from naatik_next.app import Window,main
class Broker:
 def __init__(self,*a):self.server=self
 def acquire_or_forward(self,*a):return True
 def set_handler(self,*a):pass
 def close(self):pass
class Probe(Window):
 def __init__(self,**kw):
  super().__init__(**kw)
  self.probe=QTimer(self);self.probe.timeout.connect(self.ready);self.probe.start(10)
 def ready(self):
  mode=os.environ['POPUP_MODE']
  if mode not in self.popups:return
  p=self.popups[mode]
  if Path(p.phrase_task.program).exists() and (not p.phrase_task.process or not p.phrase_task.process.processId()):return
  pids=[int(t.process.processId()) for t in self.tasks+self.popup_tasks if t.process and t.process.processId()]
  if not pids:return
  assert not self.isVisible() and p.isVisible()
  self.probe.stop()
  temporary=Path(os.environ['PROBE_ROOT'],'ready.tmp');temporary.write_text(json.dumps(pids))
  temporary.replace(temporary.with_name('ready'))
class App(QApplication):
 def __init__(self,*a):
  super().__init__(*a);self.clipboard().setText('日本')
with patch('naatik_next.app.Instance',Broker),patch('naatik_next.app.Window',Probe),patch('naatik_next.app.QApplication',App),patch('sys.argv',['launch','--'+os.environ['POPUP_MODE']]):
 raise SystemExit(main())
'''
        for mode in ('translator','phrase'):
            for first in (signal.SIGINT,signal.SIGTERM):
                with self.subTest(mode=mode,signal=first),tempfile.TemporaryDirectory(prefix='next-popup-stop-') as tmp:
                    d=Path(tmp)
                    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1',
                             PYTHONFAULTHANDLER='1',POPUP_MODE=mode,PROBE_ROOT=tmp)
                    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
                        env[key]=str(d/key)
                    p=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,env=env,stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,start_new_session=True)
                    try:
                        deadline=time.monotonic()+8
                        while not (d/'ready').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                        self.assertTrue((d/'ready').exists(),'popup worker barrier not reached')
                        pids=json.loads((d/'ready').read_text())
                        for sig in (first,first,signal.SIGINT,signal.SIGTERM):
                            if p.poll() is None:os.killpg(p.pid,sig)
                            time.sleep(.02)
                        out,err=p.communicate(timeout=8)
                        self.assertEqual(p.returncode,128+first,err.decode(errors='replace'))
                        for bad in (b'Traceback',b'KeyboardInterrupt',b'No Wrapper',b'already deleted',b'Destroyed while process'):
                            self.assertNotIn(bad,err)
                        for pid in pids:
                            stat=Path(f'/proc/{pid}/stat')
                            self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')
                    finally:
                        if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
                        p.communicate()
