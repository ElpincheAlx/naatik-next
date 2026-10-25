"""Qt process supervisor. Callbacks run on the GUI thread; each worker owns a process group."""
from .i18n import t
import json
import logging
import os
import signal
import sys
from . import timings
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


class Task(QObject):
    progress = Signal(str)
    result = Signal(object)
    error = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent=None, persistent=False, program=None, module="naatik_next.worker"):
        super().__init__(parent)
        self.persistent = persistent
        self.program = program or sys.executable
        self.module = module
        self.process = None
        self.group = None
        self.cancel_process = None
        self.busy = False
        self.closing = False
        self.interrupted = lambda: False
        self.buffer = b''
        self.stderr = b''
        self.answer = None
        self.failure = None
        self.cancel_reason = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.cancel(t('Se agotó el tiempo de espera.')))
        # Owned/cancellable timer: never retain a naked lambda with a deleted QProcess.
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self._kill_cancelled)

    def start(self, request, timeout=120000):
        if self.closing or self.interrupted():
            return
        if self.busy:
            self.error.emit(t('Ya hay una operación en curso.'))
            return
        self.busy = True
        self.answer = self.failure = self.cancel_reason = None
        self.buffer = b''
        self.stderr = b''
        self.busy_changed.emit(True)
        if self.closing or self.interrupted():  # A synchronous receiver may have closed the owner.
            return
        self.timer.start(timeout)
        if timings.enabled():
            request = dict(request, timings=True)
        from .i18n import language
        request = dict(request, ui_language=language())
        payload = (json.dumps(request, ensure_ascii=False) + '\n').encode()
        if self.process and self.process.state() == QProcess.Running:
            self.process.write(payload)
            return
        if self.process is not None:
            self.process.blockSignals(True)
            self.process.deleteLater()
        p = QProcess(self)
        self.process = p
        self.group = None
        if sys.platform == 'linux':
            p.setUnixProcessParameters(QProcess.UnixProcessFlag.CreateNewSession)
        p.setWorkingDirectory(str(__import__('pathlib').Path(__file__).resolve().parent.parent))
        arguments = ['-m', self.module] + (['--persistent'] if self.persistent else [])
        if sys.platform == 'linux':
            p.setProgram(sys.executable)
            p.setArguments(['-m', 'naatik_next.worker_guard', self.program, *arguments])
        else:
            p.setProgram(self.program)
            p.setArguments(arguments)
        env = QProcessEnvironment.systemEnvironment()
        from .i18n import language
        env.insert('NAATIK_NEXT_UI_LANGUAGE', language())
        env.insert('PYTHONDONTWRITEBYTECODE', '1')
        env.insert('PYTHONNOUSERSITE', '1')
        env.insert('NAATIK_SUPERVISED', '1')
        env.insert('NAATIK_OWNER_PID', str(os.getpid()))
        env.remove('PYTHONPATH')
        env.remove('PYTHONHOME')
        p.setProcessEnvironment(env)
        # Capture the emitting process, not a mutable self.process belonging to a later job.
        p.readyReadStandardOutput.connect(lambda: self._read(p))
        p.readyReadStandardError.connect(lambda: self._stderr(p))
        p.finished.connect(lambda code, status: self._finished(code, status, p))
        p.errorOccurred.connect(lambda error: self._process_error(error, p))
        p.started.connect(lambda: self._started(p, payload))
        p.start()

    def _current(self, p):
        return not self.closing and not self.interrupted() and p is self.process

    def _started(self, p, payload):
        if not self._current(p):
            return
        if sys.platform == 'linux':
            self.group = int(p.processId())
        if self.cancel_reason:
            self._signal(signal.SIGTERM)
        else:
            p.write(payload)

    def _stderr(self, p=None):
        p = self.process if p is None else p
        if self._current(p) and p is not None:
            self.stderr = (self.stderr + bytes(p.readAllStandardError()))[-8000:]

    def _read(self, p=None):
        p = self.process if p is None else p
        if p is None or not self._current(p):
            return
        self.buffer += bytes(p.readAllStandardOutput())
        if len(self.buffer) > 64 * 1024 * 1024:
            self.cancel(t('La respuesta excedió el límite de seguridad.'))
            return
        while b'\n' in self.buffer and self._current(p):
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                message = json.loads(line)
            except ValueError:
                logging.warning('Worker emitted non-protocol output')
                continue
            if 'progress' in message:
                self.progress.emit(message['progress'])
            if not self._current(p):
                return
            if 'error' in message:
                self.failure = message['error']
            if 'result' in message:
                self.answer = message['result']
            if self.persistent and not self.cancel_reason and ('error' in message or 'result' in message):
                self._complete()

    def _process_error(self, error, p=None):
        p = self.process if p is None else p
        if p is not None and self._current(p) and error == QProcess.FailedToStart:
            self.failure = t('No se pudo iniciar el proceso de trabajo: ') + p.errorString()
            self._complete()

    def _finished(self, code, status, p=None):
        p = self.process if p is None else p
        if p is None or not self._current(p):
            return
        was_busy = self.busy
        self._read(p)
        self._stderr(p)
        if not self._current(p):
            return
        self.kill_timer.stop()
        self.cancel_process = None
        # Also remove descendants left by a failed/cancelled worker before accepting another job.
        self._signal(signal.SIGKILL)
        self.group = None
        if self.busy:
            if self.answer is None and self.failure is None:
                self.failure = t('El proceso terminó sin resultado. ') + self.stderr.decode(errors='replace')[-1200:]
            self._complete()
        if self.persistent and not self.closing and not self.cancel_reason and (not was_busy or self.answer is not None):
            self.error.emit(t('El worker persistente terminó. Vuelve a detectar/probar el motor antes de usarlo.'))

    def _complete(self):
        if not self.busy or self.closing or self.interrupted():
            return
        self.timer.stop()
        self.kill_timer.stop()
        self.cancel_process = None
        answer, failure = self.answer, self.cancel_reason or self.failure
        self.busy = False
        self.busy_changed.emit(False)
        if self.closing or self.interrupted():
            return
        if failure:
            self.error.emit(failure)
        else:
            self.result.emit(answer)

    def _signal(self, signum):
        if sys.platform == 'linux' and self.group and self.group != os.getpgrp():
            try:
                os.killpg(self.group, signum)
            except ProcessLookupError:
                pass
        elif self.process and self.process.state() != QProcess.NotRunning:
            self.process.kill() if signum == signal.SIGKILL else self.process.terminate()

    def cancel(self, reason=None):
        if self.closing or not self.busy or self.cancel_reason is not None:
            return
        self.cancel_reason = t('Operación cancelada.') if reason is None else reason
        p = self.process
        if p and p.state() != QProcess.NotRunning:
            self.cancel_process = p
            self._signal(signal.SIGTERM)
            self.kill_timer.start(2500)
        else:
            self._complete()

    def _kill_cancelled(self):
        if not self.closing and self.busy and self.cancel_reason and self.cancel_process is self.process:
            self._signal(signal.SIGKILL)

    def begin_close(self):
        if self.closing:
            return
        self.closing = True
        self.busy = False
        self.timer.stop()
        self.kill_timer.stop()
        self.cancel_process = None
        p = self.process
        if p is not None:
            # waitForFinished can dispatch QProcess signals: disconnect their Python path first.
            p.blockSignals(True)
            if p.state() == QProcess.Starting:
                p.waitForStarted(500)
            if sys.platform == 'linux' and p.processId():
                self.group = int(p.processId())
            self._signal(signal.SIGTERM)

    def close(self, timeout_ms=3000):
        self.begin_close()
        p = self.process
        if p is not None and p.state() != QProcess.NotRunning:
            if not p.waitForFinished(timeout_ms):
                self._signal(signal.SIGKILL)
                p.waitForFinished(1000)
        self._signal(signal.SIGKILL)
        self.group = None

    def reopen(self):
        """Only an explicit live-owner runtime change may reuse a closed supervisor."""
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            raise RuntimeError(t('El worker anterior aún no terminó.'))
        self.closing = False
