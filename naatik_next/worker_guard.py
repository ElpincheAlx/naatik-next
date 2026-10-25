"""Linux worker guardian: reap its family even if the Qt owner dies abruptly.

No models, Qt or user configuration are imported. The guardian and its child
have separate sessions so cleanup never targets the GUI/terminal process group.
"""
from .i18n import t
import os
import signal
import subprocess
import sys
import time


def main():
    if sys.platform != 'linux' or os.getpid() != os.getpgrp():
        print(t('El supervisor requiere su propia sesión Linux.'), file=sys.stderr)
        return 1
    try:
        owner = int(os.environ['NAATIK_OWNER_PID'])
    except (KeyError, ValueError):
        print(t('Falta el propietario del worker.'), file=sys.stderr)
        return 1
    if owner != os.getppid():
        return 1  # Owner died before we could start; never create an orphan.
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if not sys.argv[1:]:
        return 1
    child = subprocess.Popen(sys.argv[1:], start_new_session=True)
    def finished():
        # Do not reap yet: retain the leader PID until the whole group is gone.
        # This prevents PID reuse between observing exit and cleaning its family.
        return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    def family(signum):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass
    try:
        while not finished() and not stopping and os.getppid() == owner:
            time.sleep(.05)
        if not finished():
            family(signal.SIGTERM)
            deadline = time.monotonic() + 1.5
            while not finished() and time.monotonic() < deadline:
                time.sleep(.02)
    finally:
        family(signal.SIGKILL)
        code = child.wait()
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except OSError as error:
        print(t('No se pudo iniciar el worker: ')+str(error), file=sys.stderr)
        raise SystemExit(1)
