"""Translate Unix termination signals into one Qt event, never KeyboardInterrupt in a slot."""
import os
import signal
from PySide6.QtCore import QObject, QSocketNotifier


class ShutdownSignals(QObject):
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.received = None
        self.requested = False
        self.closed = False
        self.read_fd, self.write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        self.previous_handlers = {}
        self.previous_wakeup = signal.set_wakeup_fd(self.write_fd, warn_on_full_buffer=False)
        for signum in (signal.SIGINT, signal.SIGTERM):
            self.previous_handlers[signum] = signal.signal(signum, self._remember)
        self.notifier = QSocketNotifier(self.read_fd, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self._drain)

    def _remember(self, signum, frame):
        # No Qt calls, exception, teardown, IO or logging in the Python signal handler.
        if self.received is None:
            self.received = signum

    def _drain(self, *args):
        if self.closed or self.requested:
            return
        try:
            while os.read(self.read_fd, 4096):
                pass
        except BlockingIOError:
            pass
        if self.requested or self.closed or self.received is None:
            return
        self.requested = True
        self.notifier.setEnabled(False)
        self.callback(self.received)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.notifier.setEnabled(False)
        self.notifier.activated.disconnect(self._drain)
        signal.set_wakeup_fd(self.previous_wakeup)
        for signum, previous in self.previous_handlers.items():
            # Once terminating, repeated signals remain harmless through Qt/Python destruction.
            signal.signal(signum, signal.SIG_IGN if self.received is not None else previous)
        os.close(self.read_fd)
        os.close(self.write_fd)
        self.notifier.deleteLater()
