"""User-private, bounded local protocol. Never executes received commands."""
from .i18n import t
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import stat
import time
import tempfile
import uuid
from PySide6.QtCore import QObject, QLockFile, QTimer, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from .storage import UserError
from . import timings

MAX_FRAME = 160
STATUSES = {'queued', 'accepted', 'ignored', 'unavailable', 'shown', 'error'}


def frame(value):
    return json.dumps(value, separators=(',', ':')).encode('ascii') + b'\n'


def parse(data):
    if len(data) > MAX_FRAME or not data.endswith(b'\n') or data.count(b'\n') != 1:
        raise ValueError('Invalid frame')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=unique)
    if (not isinstance(value, dict) or type(value.get('v')) is not int or value['v'] != 1
            or not isinstance(value.get('id'), str) or not re.fullmatch('[0-9a-f]{32}', value['id'])):
        raise ValueError('Invalid identity')
    return value


def request(action, ident=None, *, diagnostics=False):
    if action not in ('capture', 'capture-copy', 'translator', 'phrase', 'show'):
        raise ValueError('Unknown action')
    value = {'v': 1, 'id': ident or uuid.uuid4().hex, 'action': action}
    if diagnostics:
        value['timings'] = True
    return value


def private_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise UserError((t('El directorio IPC debe ser privado, propio y sin enlace simbólico: ') + f'{path}'))
    return path


def endpoint(state):
    """One endpoint per user/state, with no normal-use dependency on /tmp."""
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    base = state
    if runtime and Path(runtime).is_absolute():
        candidate = Path(runtime)
        try:
            info = candidate.lstat()
            if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077:
                base = private_directory(candidate / 'naatik-next')
        except OSError:
            pass  # Restricted runtime: persistent private XDG state is the fallback.
    directory = private_directory(base / 'ipc')
    digest = hashlib.sha256(os.fsencode(state.resolve())).hexdigest()[:16]
    path = directory / (digest + '.sock')
    if len(os.fsencode(path)) > 100:
        # Only the transport moves; the selected config/data/state profile stays intact.
        directory = private_directory(Path('/tmp') / ('naatik-next-' + str(os.getuid())))
        path = directory / (digest + '.sock')
    return str(path)


def recorded_endpoint(state):
    """Read only an owner-published locator for this state profile, never arbitrary IPC."""
    record = state / 'application.endpoint'
    try:
        info = record.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_size > 1024):
        raise UserError(t('El localizador IPC no es un archivo privado válido; no se reemplazará.'))
    try:
        value = json.loads(record.read_text())
        if (not isinstance(value, dict) or set(value) != {'v', 'name', 'token'} or type(value['v']) is not int or value['v'] != 1
                or not isinstance(value['token'], str) or not re.fullmatch('[0-9a-f]{32}', value['token'])
                or not isinstance(value['name'], str)):
            raise ValueError()
        path = Path(value['name'])
        digest = hashlib.sha256(os.fsencode(state.resolve())).hexdigest()[:16]
        if not path.is_absolute() or path.name != digest + '.sock' or len(os.fsencode(path)) > 100:
            raise ValueError()
        parent = path.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise ValueError()
    except FileNotFoundError:
        return None  # The old runtime directory disappeared after the owner exited.
    except (ValueError, TypeError, OSError) as error:
        raise UserError(t('El localizador IPC no es válido; no se usará un canal ajeno.')) from error
    return str(path)


class LocalServer(QObject):
    def __init__(self, name, handler=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.handler = handler
        self.seen = {}
        self.pending = set()
        self.connections = {}
        self.deadlines = {}
        self.responding = set()
        self.closed = False
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.setMaxPendingConnections(16)
        self.server.newConnection.connect(self.accept)

    def listen(self):
        # Called ONLY by the holder of application.lock. Never unlink others' files.
        path = Path(self.name)
        if path.is_symlink():
            raise UserError(t('El socket IPC es un enlace simbólico; no se reemplazará.'))
        if path.exists():
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise UserError(t('La ruta IPC está ocupada por un archivo ajeno; no se reemplazará.'))
            probe = QLocalSocket()
            try:
                probe.connectToServer(self.name)
                if probe.state() == QLocalSocket.ConnectedState or probe.waitForConnected(100):
                    raise UserError(t('Hay un canal IPC activo; no se reemplazará ni se abrirá otra instancia.'))
                if probe.error() not in (QLocalSocket.ConnectionRefusedError, QLocalSocket.ServerNotFoundError):
                    raise UserError(t('No se pudo comprobar si el canal IPC está obsoleto; no se retirará.'))
            finally:
                probe.abort()
            if not QLocalServer.removeServer(self.name):
                raise UserError(t('No se pudo retirar el socket IPC obsoleto.'))
        if not self.server.listen(self.name):
            raise UserError(t('No se pudo abrir el canal local de Next: ') + self.server.errorString())

    def accept(self):
        while self.server.hasPendingConnections():
            self.attach(self.server.nextPendingConnection())

    def attach(self, socket):
        # Also usable with an inherited connected socket in transport tests.
        if self.closed or len(self.connections) >= 32:
            socket.abort()
            socket.deleteLater()
            return
        socket.setReadBufferSize(MAX_FRAME + 1)
        timer = QTimer(socket)
        timer.setSingleShot(True)
        # Register a Python-owned slot, never a dynamic native abort() method
        # on a socket whose wrapper can disappear during deferred destruction.
        timer.timeout.connect(self.expire)
        self.connections[socket] = bytearray()
        self.deadlines[socket] = timer
        socket.readyRead.connect(lambda: self.read(socket))
        socket.disconnected.connect(lambda: self.discard(socket))
        timer.start(3000)
        if socket.bytesAvailable():
            self.read(socket)

    @Slot()
    def expire(self):
        timer = self.sender()
        if timer is None:
            return
        socket = timer.parent()
        if self.deadlines.get(socket) is timer:
            socket.abort()
            self.discard(socket)

    def discard(self, socket):
        if socket not in self.connections:
            return
        self.connections.pop(socket)
        self.responding.discard(socket)
        timer = self.deadlines.pop(socket)
        timer.stop()
        socket.deleteLater()

    def set_handler(self, handler):
        self.handler = handler
        pending, self.pending = self.pending, set()
        for action in ('show', 'translator', 'phrase', 'capture-copy', 'capture'):
            if action in pending:
                handler(action)

    def dispatch(self, data):
        value = parse(data)
        if (set(value) not in ({'v', 'id', 'action'}, {'v', 'id', 'action', 'timings'})
                or ('timings' in value and value['timings'] is not True)) or value['action'] not in ('capture', 'capture-copy', 'translator', 'phrase', 'show'):
            raise ValueError('Unknown operation')
        if value.get('timings') is True:
            timings.enable()
        ident = value['id']
        timings.event('ipc_received', ident)
        if ident not in self.seen:
            if len(self.seen) >= 256:
                del self.seen[next(iter(self.seen))]
            # Remember BEFORE calling a handler that may open a nested modal loop.
            self.seen[ident] = 'queued'
            if self.handler is None:
                self.pending.add(value['action'])
                result = 'queued'
            else:
                try:
                    result = self.handler(value['action'])
                except Exception as error:
                    logging.error('La acción IPC %s falló (%s)', value['action'], type(error).__name__)
                    result = 'error'
            self.seen[ident] = result if result in STATUSES else 'error'
        return frame({'v': 1, 'id': ident, 'status': self.seen[ident]})

    def read(self, socket):
        if self.closed or socket not in self.connections or socket in self.responding:
            return
        data = self.connections[socket]
        data.extend(bytes(socket.readAll()))
        if len(data) <= MAX_FRAME and b'\n' not in data:
            return
        # One frame per connection; reject the whole frame before running its action.
        self.responding.add(socket)
        try:
            reply = self.dispatch(bytes(data))
        except (ValueError, TypeError, KeyError, RuntimeError):
            reply = b'{"error":"invalid-request"}\n'
        if self.closed or socket not in self.connections:
            return
        socket.write(reply)
        socket.flush()
        socket.disconnectFromServer()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.close()
        for socket in list(self.connections):
            socket.abort()
            self.discard(socket)


def send(name, value, timeout=1000):
    """Blocking only in the short-lived launcher, never in the running GUI."""
    deadline = time.monotonic() + timeout / 1000
    def remaining_ms():
        return max(1, int((deadline - time.monotonic()) * 1000))
    socket = QLocalSocket()
    socket.setReadBufferSize(MAX_FRAME + 1)
    try:
        socket.connectToServer(name)
        if socket.state() != QLocalSocket.ConnectedState and not socket.waitForConnected(remaining_ms()):
            return None
        socket.write(frame(value))
        if socket.bytesToWrite() and not socket.waitForBytesWritten(remaining_ms()):
            return None
        data = bytearray()
        while len(data) <= MAX_FRAME:
            data.extend(bytes(socket.readAll()))
            if b'\n' in data:
                try:
                    reply = parse(bytes(data))
                except (ValueError, TypeError) as e:
                    raise UserError(t('El canal local respondió con un protocolo incompatible.')) from e
                if (set(reply) != {'v', 'id', 'status'} or reply['id'] != value['id']
                        or not isinstance(reply['status'], str) or reply['status'] not in STATUSES):
                    raise UserError(t('El canal local respondió con un protocolo incompatible.'))
                return reply['status']
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0 or not socket.waitForReadyRead(remaining):
                return None
        raise UserError(t('La respuesta del canal local excede el límite permitido.'))
    finally:
        socket.abort()


class Instance:
    def __init__(self, state):
        self.lock = QLockFile(str(state / 'application.lock'))
        self.lock.setStaleLockTime(0)
        self.state = Path(state)
        self.name = endpoint(state)
        self.published = None
        self.server = None
        self.owner = False
        self.interrupted = lambda: False

    def acquire_or_forward(self, action, timeout=15000, *, diagnostics=False):
        value = request(action, diagnostics=diagnostics)
        deadline = time.monotonic() + timeout / 1000
        while True:
            if self.interrupted():
                return False
            if self.lock.tryLock(0):
                self.owner = True
                try:
                    self.name = recorded_endpoint(self.state) or self.name
                    self.server = LocalServer(self.name)
                    self.server.listen()
                    self.publish_endpoint()
                except Exception:
                    self.close()
                    raise
                return True
            self.name = recorded_endpoint(self.state) or self.name
            status = send(self.name, value, min(1000, max(1, int((deadline - time.monotonic()) * 1000))))
            if status is not None:
                if status in ('error', 'unavailable'):
                    raise UserError(t('Next no pudo iniciar la acción. Revisa sus recursos y la configuración.'))
                if status == 'ignored':
                    raise UserError(t('Next está ocupado o cerrándose; la acción no se inició. Vuelve a intentar.'))
                return False
            if time.monotonic() >= deadline:
                raise UserError(t('Next mantiene el bloqueo pero no respondió al canal local. Espera al arranque o revisa su ventana/log; no se abrió otra instancia.'))
            time.sleep(.05)

    def publish_endpoint(self):
        payload = json.dumps(dict(v=1, name=self.name, token=uuid.uuid4().hex)).encode()
        fd, temporary = tempfile.mkstemp(prefix='.endpoint-', dir=self.state)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.state / 'application.endpoint')
            self.published = payload
        finally:
            Path(temporary).unlink(missing_ok=True)

    def close(self):
        if self.server:
            self.server.close()
        if self.owner:
            record = self.state / 'application.endpoint'
            try:
                if self.published is not None and not record.is_symlink() and record.read_bytes() == self.published:
                    record.unlink()
            except FileNotFoundError:
                pass
            except OSError as error:
                logging.warning('No se pudo retirar el localizador IPC propio: %s', error)
            self.lock.unlock()
            self.owner = False
