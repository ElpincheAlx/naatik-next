"""Fresh subprocess profiles before imports; real launches/signals, explicit IPC gates."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/bin/python'


def environment(root):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    for key in list(env):
        if key.startswith(('ARGOS_', 'NAATIK_')) or key in ('PYTHONPATH','PYTHONHOME'):
            env.pop(key)
    for index, key in enumerate(('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_RUNTIME_DIR')):
        folder = root/str(index); folder.mkdir(mode=0o700, parents=True, exist_ok=True); env[key] = str(folder)
    return env


def wait_for(predicate, timeout=8):
    deadline = time.monotonic()+timeout
    while not predicate():
        if time.monotonic()>deadline: raise AssertionError('fixture deadline')
        time.sleep(.02)


def running(pid):
    try: return Path('/proc', str(pid), 'stat').read_text().split(') ')[1][0] != 'Z'
    except FileNotFoundError: return False


class FreshLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='nl-'); self.root = Path(self.tmp.name)
        self.env = environment(self.root)

    def tearDown(self): self.tmp.cleanup()

    def test_real_commands_fail_promptly_and_clearly_if_bind_is_forbidden(self):
        probe = socket.socket(socket.AF_UNIX)
        try:
            probe.bind(str(self.root/'probe'))
        except PermissionError:
            pass
        else:
            self.skipTest('Named sockets allowed: use the real broker gate and desktop lifecycle review')
        finally: probe.close()
        for action in ([], ['--capture-copy'], ['--translator'], ['--phrase']):
            result = subprocess.run([str(ROOT/'launch'), *action], cwd='/', env=self.env,
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('No se pudo abrir el canal local', result.stderr)
            self.assertFalse(list(self.root.rglob('application.lock')))
            self.assertFalse(list(self.root.rglob('application.endpoint')))

    def test_real_lock_and_locator_recover_after_sigkill_bind_stubbed(self):
        # Only listen is stubbed. QLockFile/PID death, disk record and cleanup are real.
        code = '''
import os,time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from naatik_next.instance import Instance,LocalServer
from naatik_next.storage import paths
app=QCoreApplication([])
with patch.object(LocalServer,'listen'):
 broker=Instance(paths()['state']); assert broker.acquire_or_forward('show')
 Path(os.environ['HOME'],'ready').write_text('ready')
 if os.environ.get('RECOVER')=='1': broker.close()
 else:
  while True: time.sleep(.1)
'''
        first = subprocess.Popen([str(PYTHON), '-c', code], cwd=ROOT, env=self.env)
        marker = Path(self.env['HOME'])/'ready'
        try:
            wait_for(marker.exists)
            record = Path(self.env['XDG_STATE_HOME'])/'naatik-next/application.endpoint'
            self.assertTrue(record.exists())
            first.kill(); first.wait(timeout=3); marker.unlink()
            self.assertTrue(record.exists())  # Crash leaves a stale locator and lock.
            result = subprocess.run([str(PYTHON), '-c', code], cwd=ROOT,
                                    env=dict(self.env, RECOVER='1'), capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(record.exists())
            self.assertFalse(record.with_name('application.lock').exists())
        finally:
            if first.poll() is None: first.kill(); first.wait()

    def test_owner_sigkill_reaps_busy_worker_family(self):
        import shlex
        worker = self.root/'busy.py'
        worker.write_text('''import os,signal,subprocess,sys,time
from pathlib import Path
root=Path(os.environ['HOME'])
signal.signal(signal.SIGTERM,signal.SIG_IGN)
(root/'worker').write_text(str(os.getpid()))
subprocess.Popen([sys.executable,'-c',"import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path(os.environ['HOME'],'tool').write_text(str(os.getpid())); time.sleep(120)"])
while True: time.sleep(.1)
''')
        wrapper=self.root/"worker ' with spaces"; wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(str(PYTHON))+' '+shlex.quote(str(worker))+'\n'); wrapper.chmod(0o700)
        code='''import os
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from naatik_next.processes import Task
app=QCoreApplication([])
task=Task(program=os.environ['BUSY_PROGRAM']);task.start({'action':'fixture'},120000)
task.process.started.connect(lambda: Path(os.environ['HOME'],'guardian').write_text(str(task.process.processId())))
app.exec()
'''
        parent=subprocess.Popen([str(PYTHON),'-c',code],cwd=ROOT,env=dict(self.env,BUSY_PROGRAM=str(wrapper)), start_new_session=True)
        home=Path(self.env['HOME']); pids=[]
        try:
            wait_for(lambda: all((home/name).exists() for name in ('worker','tool','guardian')))
            pids=[int((home/name).read_text()) for name in ('worker','tool','guardian')]
            parent.kill();parent.wait(timeout=3)
            wait_for(lambda:not any(running(pid) for pid in pids),5)
        finally:
            if parent.poll() is None:parent.kill();parent.wait()
            for pid in pids:
                if running(pid):
                    try:os.killpg(pid,signal.SIGKILL)
                    except ProcessLookupError:pass

    def test_qt_window_popup_hide_exit_and_receive_clipboard_tray_availability_injected(self):
        code='''from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from naatik_next.app import Window
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
with patch('naatik_next.app.QTimer.singleShot'):
 w=Window(background=True,popup_only=True)
w.show()
for action in ('translator','phrase'):
 for text in ('最初','新しい本文'):
  app.clipboard().setText(text);assert w.external_command(action)=='shown'
  p=w.popups[action];p.debounce.stop();assert p.editor.toPlainText()==text
  p.close();assert not w.closing
with patch.object(w,'ensure_tray',return_value=False),patch.object(w,'fail') as fail:
 assert not w.hide_to_tray();assert w.isVisible();fail.assert_called_once()
with patch.object(w,'ensure_tray',return_value=True):
 assert w.hide_to_tray();assert not w.isVisible();assert not w.closing
w.close();assert w.closing;assert not any(t.busy for t in w.tasks+w.popup_tasks)
'''
        result=subprocess.run([str(PYTHON),'-c',code],cwd=ROOT,env=self.env,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_named_broker_real_cold_forward_restart_when_transport_is_available(self):
        probe=socket.socket(socket.AF_UNIX)
        try:probe.bind(str(self.root/'probe'))
        except PermissionError as error:self.skipTest('Real named IPC unavailable: '+str(error))
        finally:probe.close()
        code='''import os,json
from pathlib import Path
from PySide6.QtCore import QCoreApplication,QTimer
from naatik_next.instance import Instance
from naatik_next.storage import paths
from naatik_next.shutdown_signals import ShutdownSignals
app=QCoreApplication([]);broker=Instance(paths()['state'])
signals=ShutdownSignals(lambda signum: app.quit())
action=os.environ['BROKER_ACTION']
if not broker.acquire_or_forward(action):raise SystemExit(0)
root=Path(os.environ['HOME']);(root/'owner').write_text(str(os.getpid()))
def receive(action):
 with (root/'received').open('a') as stream:stream.write(action+'\\n')
 return 'accepted'
broker.server.set_handler(receive);QTimer.singleShot(15000,app.quit)
try:app.exec()
finally:broker.close();signals.close()
'''
        for turn in range(2):
            marker=Path(self.env['HOME'])/'owner'; marker.unlink(missing_ok=True)
            received_path=Path(self.env['HOME'])/'received'; received_path.unlink(missing_ok=True)
            owner=subprocess.Popen([str(PYTHON),'-c',code],cwd=ROOT,env=dict(self.env,BROKER_ACTION='show'))
            clients=[]
            try:
                wait_for(marker.exists)
                clients=[subprocess.Popen([str(PYTHON),'-c',code],cwd=ROOT,env=dict(self.env,BROKER_ACTION=action))
                         for action in ('show','capture-copy','translator','phrase')]
                for client in clients:self.assertEqual(client.wait(timeout=5),0)
                self.assertCountEqual(received_path.read_text().splitlines(),['show','capture-copy','translator','phrase'])
            finally:
                owner.send_signal(signal.SIGTERM if turn==0 else signal.SIGINT);owner.wait(timeout=5)
                for client in clients:
                    if client.poll() is None:client.kill();client.wait()
            self.assertFalse(list(self.root.rglob('application.lock')))
            self.assertFalse(list(self.root.rglob('application.endpoint')))
