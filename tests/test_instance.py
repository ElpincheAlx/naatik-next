import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import socket as sockets
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QLockFile, QCoreApplication, QEvent
from PySide6.QtNetwork import QLocalSocket
from naatik_next.instance import Instance, LocalServer, endpoint, frame, parse, request, send
from naatik_next.storage import UserError
from tests.test_processes import APP, spin_until

ROOT = Path(__file__).resolve().parents[1]


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='next-ipc-')
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)})
        self.env.start()
        self.server = LocalServer(str(self.root / 'socket'), lambda action: 'accepted')
        self.clients = []

    def tearDown(self):
        self.server.close()
        for client in self.clients:
            client.abort()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.env.stop()
        self.tmp.cleanup()

    def exchange(self, payload):
        a, b = sockets.socketpair()
        client, peer = QLocalSocket(), QLocalSocket(self.server)
        self.clients.append(client)
        self.assertTrue(client.setSocketDescriptor(a.detach()))
        self.assertTrue(peer.setSocketDescriptor(b.detach()))
        response = bytearray()
        client.readyRead.connect(lambda: response.extend(bytes(client.readAll())))
        self.server.attach(peer)
        client.write(payload)
        client.flush()
        spin_until(lambda: bool(response))
        return bytes(response)

    def test_real_socketpair_frames_and_duplicate_ids(self):
        calls = []
        self.server.set_handler(lambda action: calls.append(action) or 'accepted')
        value = request('capture')
        reply = parse(self.exchange(frame(value)))
        self.assertEqual(reply['status'], 'accepted')
        self.assertEqual(parse(self.exchange(frame(value))), reply)
        self.assertEqual(calls, ['capture'])
        self.exchange(frame(request('show')))
        self.assertEqual(calls, ['capture', 'show'])

    def test_capture_copy_distinct_closed_action_and_duplicate_ids(self):
        calls = []
        self.server.set_handler(lambda action: calls.append(action) or 'accepted')
        value = request('capture-copy')
        self.assertEqual(parse(self.exchange(frame(value)))['status'], 'accepted')
        self.exchange(frame(value))
        self.exchange(frame(request('show')))
        self.assertEqual(calls, ['capture-copy', 'show'])
        self.server.handler = None
        for _ in range(3):
            self.exchange(frame(request('capture-copy')))
        self.server.set_handler(lambda action: calls.append(action) or 'accepted')
        self.assertEqual(calls, ['capture-copy', 'show', 'capture-copy'])

    def test_optional_diagnostics_flag_remains_closed_and_boolean(self):
        with patch('naatik_next.instance.timings.enable') as enable:
            self.assertEqual(parse(self.exchange(frame(request('capture-copy', diagnostics=True))))['status'], 'accepted')
            enable.assert_called_once()
            for flag in ('path', False, 1, None):
                self.assertIn(b'invalid-request', self.exchange(frame(dict(request('capture'), timings=flag))))
            self.assertEqual(enable.call_count, 1)

    def test_closed_protocol_invalid_extra_oversize_and_split_frame(self):
        calls = []
        self.server.set_handler(lambda action: calls.append(action) or 'accepted')
        for payload in (b'bad\n', b'x'*161, b'{}\n{}\n',
                frame(dict(request('capture'), action='shell')),
                frame(dict(request('capture'), command='touch /tmp/never')),
                frame(dict(request('capture'), v=True))):
            self.assertIn(b'invalid-request', self.exchange(payload))
        self.assertEqual(calls, [])
        a, b = sockets.socketpair()
        client, peer = QLocalSocket(), QLocalSocket(self.server)
        self.clients.append(client)
        client.setSocketDescriptor(a.detach())
        peer.setSocketDescriptor(b.detach())
        self.server.attach(peer)
        payload = frame(request('capture'))
        client.write(payload[:15])
        client.flush()
        APP.processEvents()
        self.assertEqual(calls, [])
        client.write(payload[15:])
        client.flush()
        spin_until(lambda: bool(calls))
        self.assertEqual(calls, ['capture'])

    def test_requests_before_handler_are_coalesced_not_lost(self):
        self.server.handler = None
        for _ in range(5):
            self.assertEqual(parse(self.exchange(frame(request('capture'))))['status'], 'queued')
        calls = []
        self.server.set_handler(lambda action: calls.append(action) or 'accepted')
        self.assertEqual(calls, ['capture'])

    def test_owner_open_closed_and_client_retries_same_id_during_startup(self):
        with patch.object(LocalServer, 'listen'):
            owner = Instance(self.root)
            self.assertTrue(owner.acquire_or_forward('capture'))
            client = Instance(self.root)
            with patch('naatik_next.instance.send', side_effect=[None, None, 'queued']) as forward:
                self.assertFalse(client.acquire_or_forward('capture', timeout=1000))
                ids = {call.args[1]['id'] for call in forward.call_args_list}
                self.assertEqual(len(ids), 1)
            client.close()
            owner.close()
            next_owner = Instance(self.root)
            self.assertTrue(next_owner.acquire_or_forward('capture'))
            next_owner.close()

    def test_timeout_never_starts_duplicate_and_bind_error_unlocks(self):
        lock = QLockFile(str(self.root / 'application.lock'))
        self.assertTrue(lock.tryLock(0))
        client = Instance(self.root)
        try:
            with patch('naatik_next.instance.send', return_value=None), patch.object(LocalServer, 'listen') as listen:
                with self.assertRaisesRegex(UserError, 'no respondió'):
                    client.acquire_or_forward('capture', timeout=1)
                listen.assert_not_called()
        finally:
            lock.unlock()
        with patch.object(LocalServer, 'listen', side_effect=UserError('bind failure')):
            with self.assertRaisesRegex(UserError, 'bind failure'):
                client.acquire_or_forward('capture')
        self.assertTrue(lock.tryLock(0))
        lock.unlock()

    def test_private_paths_and_existing_files_not_removed(self):
        name = endpoint(self.root)
        self.assertEqual(Path(name).parent.stat().st_mode & 0o777, 0o700)
        Path(self.server.name).write_text('not a socket')
        with self.assertRaisesRegex(UserError, 'archivo ajeno'):
            self.server.listen()
        self.assertEqual(Path(self.server.name).read_text(), 'not a socket')
        bad = self.root / 'public'
        bad.mkdir(mode=0o755)
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': ''}):
            (bad / 'ipc').mkdir(mode=0o755)
            with self.assertRaisesRegex(UserError, 'privado'):
                endpoint(bad)

    def test_real_client_server_exchange_in_separate_process_without_listen(self):
        # Sandbox forbids bind(), but permits inherited connected Unix sockets.
        a, b = sockets.socketpair()
        code = '''
import sys
from PySide6.QtCore import QCoreApplication,QTimer
from PySide6.QtNetwork import QLocalSocket
from naatik_next.instance import LocalServer
app=QCoreApplication([])
server=LocalServer('/unused', lambda action: 'accepted')
peer=QLocalSocket(server)
assert peer.setSocketDescriptor(int(sys.argv[1]))
server.attach(peer)
peer.disconnected.connect(app.quit)
QTimer.singleShot(5000,app.quit)
app.exec()
server.close()
'''
        child = subprocess.Popen([sys.executable, '-c', code, str(b.fileno())], pass_fds=(b.fileno(),), cwd=ROOT)
        b.close()
        fd = a.detach()
        class ConnectedSocket(QLocalSocket):
            def connectToServer(self, name):
                self.setSocketDescriptor(fd)
        try:
            with patch('naatik_next.instance.QLocalSocket', ConnectedSocket):
                self.assertEqual(send('/unused', request('capture'), timeout=3000), 'accepted')
            self.assertEqual(child.wait(timeout=5), 0)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()

    def test_real_simultaneous_lock_election_across_processes(self):
        code = '''
import sys,time
from pathlib import Path
from PySide6.QtCore import QCoreApplication,QLockFile
app=QCoreApplication([])
root=Path(sys.argv[1]); index=sys.argv[2]
lock=QLockFile(str(root/'election.lock')); lock.setStaleLockTime(0)
won=lock.tryLock(0)
(root/('result'+index)).write_text(str(won))
if won:
    deadline=time.monotonic()+10
    while not (root/'release').exists() and time.monotonic()<deadline:
        time.sleep(.01)
    lock.unlock()
'''
        children = [subprocess.Popen([sys.executable, '-c', code, str(self.root), str(i)]) for i in range(5)]
        try:
            spin_until(lambda: len(list(self.root.glob('result*'))) == 5, 10)
            self.assertEqual(sum(p.read_text() == 'True' for p in self.root.glob('result*')), 1)
        finally:
            (self.root / 'release').touch()
            for child in children:
                child.wait(timeout=5)

    def test_shutdown_during_ipc_wait_does_not_start_another_instance(self):
        broker = Instance(self.root)
        interrupted = False
        broker.interrupted = lambda: interrupted
        def receive_signal(*args):
            nonlocal interrupted
            interrupted = True
            return None
        with patch.object(broker.lock, 'tryLock', return_value=False), \
                patch('naatik_next.instance.send', side_effect=receive_signal) as forward, \
                patch('naatik_next.instance.time.sleep'), \
                patch('naatik_next.instance.LocalServer') as server:
            self.assertFalse(broker.acquire_or_forward('capture-copy'))
        forward.assert_called_once()
        server.assert_not_called()
        self.assertFalse(broker.owner)
        broker.close()

    def test_repeated_connections_and_deferred_cleanup_have_no_wrapper_warnings(self):
        import gc
        from PySide6.QtCore import qInstallMessageHandler
        messages = []
        previous = qInstallMessageHandler(lambda kind, context, message: messages.append(message))
        try:
            for _ in range(40):
                reply = parse(self.exchange(frame(request('capture-copy'))))
                self.assertEqual(reply['status'], 'accepted')
                APP.processEvents()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                gc.collect()
            self.assertEqual(self.server.connections, {})
            self.assertEqual(self.server.deadlines, {})
            self.assertEqual(self.server.responding, set())
            self.server.close()
            self.server.close()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            self.assertFalse(any('No Wrapper' in msg or 'addMetaMethod' in msg for msg in messages), messages)
        finally:
            qInstallMessageHandler(previous)

    def test_partial_connection_timeout_and_close_stop_owned_deadlines(self):
        for timeout in (True, False):
            a, b = sockets.socketpair()
            client, peer = QLocalSocket(), QLocalSocket(self.server)
            self.clients.append(client)
            self.assertTrue(client.setSocketDescriptor(a.detach()))
            self.assertTrue(peer.setSocketDescriptor(b.detach()))
            self.server.attach(peer)
            timer = self.server.deadlines[peer]
            client.write(b'{')
            client.flush()
            APP.processEvents()
            if timeout:
                timer.start(1)
                spin_until(lambda: peer not in self.server.connections)
            else:
                self.server.close()
                self.server.close()
            self.assertFalse(timer.isActive())
            self.assertNotIn(peer, self.server.deadlines)
            self.assertNotIn(peer, self.server.responding)

    def test_handler_closing_server_does_not_write_to_discarded_socket(self):
        a, b = sockets.socketpair()
        client, peer = QLocalSocket(), QLocalSocket(self.server)
        self.clients.append(client)
        client.setSocketDescriptor(a.detach())
        peer.setSocketDescriptor(b.detach())
        self.server.attach(peer)
        self.server.set_handler(lambda action: self.server.close() or 'accepted')
        client.write(frame(request('capture-copy')))
        client.flush()
        spin_until(lambda: self.server.closed)
        self.assertEqual(self.server.connections, {})
        self.assertEqual(self.server.deadlines, {})

    def test_popup_actions_are_closed_and_never_transport_clipboard_text(self):
        calls=[]
        self.server.set_handler(lambda action:calls.append(action) or 'shown')
        for action in ('translator','phrase'):
            value=request(action)
            self.assertEqual(set(value),{'v','id','action'})
            self.assertEqual(parse(self.exchange(frame(value)))['status'],'shown')
            self.exchange(frame(value))
            self.assertIn(b'invalid-request',self.exchange(frame(dict(request(action),text='untrusted payload'))))
        self.assertEqual(calls,['translator','phrase'])

    def test_long_profile_uses_private_short_transport_without_moving_profile(self):
        long = self.root / ('p'*80) / ('x'*70)
        long.mkdir(parents=True)
        runtime = self.root / ('r'*90); runtime.mkdir(mode=0o700)
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR':str(runtime)}):
            name = endpoint(long)
        self.assertLessEqual(len(os.fsencode(name)), 100)
        self.assertEqual(Path(name).parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(Path(name).name, __import__('hashlib').sha256(os.fsencode(long.resolve())).hexdigest()[:16]+'.sock')
        self.assertFalse((long/'settings.json').exists())

    def test_recorded_endpoint_routes_same_profile_across_runtime_environments(self):
        from naatik_next.instance import recorded_endpoint
        with patch.object(LocalServer, 'listen'):
            owner = Instance(self.root); self.assertTrue(owner.acquire_or_forward('show'))
            name = owner.name
            record = self.root/'application.endpoint'; payload = record.read_bytes()
            other_runtime = self.root/'other'; other_runtime.mkdir(mode=0o700)
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR':str(other_runtime)}):
                client = Instance(self.root)
                self.assertNotEqual(client.name, name)
                with patch('naatik_next.instance.send', return_value='shown') as forward:
                    self.assertFalse(client.acquire_or_forward('translator'))
                    self.assertEqual(forward.call_args.args[0], name)
                client.close()
            self.assertEqual(record.read_bytes(), payload)  # Client never removes the owner's record.
            self.assertEqual(recorded_endpoint(self.root), name)
            owner.close(); self.assertFalse(record.exists())

    def test_corrupt_or_foreign_record_is_not_followed_or_removed(self):
        record = self.root/'application.endpoint'; record.write_text('{}'); record.chmod(0o600)
        with patch.object(LocalServer,'listen') as listen:
            broker = Instance(self.root)
            with self.assertRaisesRegex(UserError,'localizador'): broker.acquire_or_forward('show')
            listen.assert_not_called()
            self.assertEqual(record.read_text(), '{}')
            broker.close()
        record.unlink(); target=self.root/'keep'; target.write_text('keep'); record.symlink_to(target)
        broker = Instance(self.root)
        with self.assertRaisesRegex(UserError,'localizador'): broker.acquire_or_forward('show')
        broker.close(); self.assertEqual(target.read_text(),'keep')

    def test_rejected_or_ignored_remote_action_is_an_error_for_the_client(self):
        with patch.object(LocalServer,'listen'):
            owner=Instance(self.root); owner.acquire_or_forward('show')
            try:
                for status in ('unavailable','ignored','error'):
                    client=Instance(self.root)
                    with patch('naatik_next.instance.send',return_value=status):
                        with self.assertRaises(UserError): client.acquire_or_forward('capture-copy')
                    client.close()
                self.assertTrue(owner.owner)
            finally: owner.close()

    def test_handler_exception_is_reported_and_not_executed_twice(self):
        handler=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=UserError('fixture'))
        self.server.set_handler(handler); value=request('translator')
        self.assertEqual(parse(self.exchange(frame(value)))['status'],'error')
        self.assertEqual(parse(self.exchange(frame(value)))['status'],'error')
        handler.assert_called_once()

    def test_live_existing_socket_never_removed_even_with_a_conflicting_lock(self):
        from unittest.mock import Mock
        # Simulated metadata/probe; this does not claim a real named-socket test.
        info=Mock(st_mode=__import__('stat').S_IFSOCK|0o600,st_uid=os.getuid())
        probe=Mock(); probe.state.return_value=QLocalSocket.ConnectedState
        with patch('naatik_next.instance.Path.exists',return_value=True), \
             patch('naatik_next.instance.Path.is_symlink',return_value=False), \
             patch('naatik_next.instance.Path.lstat',return_value=info), \
             patch('naatik_next.instance.QLocalSocket',return_value=probe) as socket_type, \
             patch('naatik_next.instance.QLocalServer.removeServer') as remove:
            socket_type.ConnectedState=QLocalSocket.ConnectedState
            with self.assertRaisesRegex(UserError,'activo'): self.server.listen()
            remove.assert_not_called()
        probe.abort.assert_called_once()
