"""Opt-in X11 drag observer in an isolated process, never a native daemon thread in Qt/Python teardown."""
import ctypes as C
import select
import signal
import subprocess
import sys
from . import timings


class DragTimer:
    def __init__(self, trace):
        self.trace = trace
        self.stopping = False
        self.process = None

    def __enter__(self):
        if timings.enabled():
            # Shares the capture worker's owned group; the supervisor also cleans
            # this process if the worker needs SIGKILL. No Qt or OCR imports here.
            try:
                self.process = subprocess.Popen([sys.executable, '-m', 'naatik_next.selection_timing',
                                                 self.trace or '-'], stdin=subprocess.PIPE,
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass  # Optional measurement must never prevent capture.
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        p = self.process
        if p is None:
            return
        self.process = None
        if p.stdin and not p.stdin.closed:
            p.stdin.close()  # EOF is the cooperative stop signal, also on exceptions.
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                p.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()

    def watch(self, readable=None):
        readable = readable or (lambda: bool(select.select([sys.stdin], [], [], .01)[0]))
        try:
            lib = C.CDLL('libX11.so.6')
            lib.XOpenDisplay.argtypes = [C.c_char_p]
            lib.XOpenDisplay.restype = C.c_void_p
            lib.XDefaultRootWindow.argtypes = [C.c_void_p]
            lib.XDefaultRootWindow.restype = C.c_ulong
            lib.XQueryPointer.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong),
                C.POINTER(C.c_ulong), C.POINTER(C.c_int), C.POINTER(C.c_int),
                C.POINTER(C.c_int), C.POINTER(C.c_int), C.POINTER(C.c_uint)]
            lib.XQueryPointer.restype = C.c_int
            lib.XCloseDisplay.argtypes = [C.c_void_p]
            display = lib.XOpenDisplay(None)
            if not display:
                return
            try:
                root = lib.XDefaultRootWindow(display)
                was_down = None
                while not self.stopping and not readable():
                    root_return, child = C.c_ulong(), C.c_ulong()
                    x, y, wx, wy, mask = C.c_int(), C.c_int(), C.c_int(), C.c_int(), C.c_uint()
                    if not lib.XQueryPointer(display, root, C.byref(root_return), C.byref(child),
                            C.byref(x), C.byref(y), C.byref(wx), C.byref(wy), C.byref(mask)):
                        continue
                    down = bool(mask.value & 256)
                    if down and was_down is False:
                        timings.event('selection_user_begin', self.trace)
                    if not down and was_down is True:
                        timings.event('selection_user_end', self.trace)
                    was_down = down
            finally:
                lib.XCloseDisplay(display)
        except (OSError, AttributeError):
            return


def main():
    timer = DragTimer(sys.argv[1] if len(sys.argv) == 2 and sys.argv[1] != '-' else None)
    def stop(signum, frame):
        timer.stopping = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    timer.watch()


if __name__ == '__main__':
    main()
