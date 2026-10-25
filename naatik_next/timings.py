"""Opt-in numeric stage events. Never accepts text, images, paths or request payloads."""
import json
import os
import time
import uuid

PROCESS_START = time.monotonic_ns()
_announced = False
STAGES = {'process_start', 'ipc_received', 'request', 'selector_prepare', 'selector_ready',
          'selection_begin', 'selection_end', 'capture_complete', 'engine_prepare_begin',
          'engine_ready', 'inference_begin', 'inference_end', 'clipboard', 'cancelled', 'failed',
          'window_ready', 'selection_user_begin', 'selection_user_end', 'interrupted'}


def enabled():
    return os.environ.get('NAATIK_TIMINGS') == '1'


def enable():
    global _announced
    os.environ['NAATIK_TIMINGS'] = '1'
    if not _announced:
        event('process_start', at_ns=PROCESS_START)
        _announced = True


def identity():
    return uuid.uuid4().hex


def event(stage, trace=None, *, at_ns=None):
    if not enabled() or stage not in STAGES:
        return
    if trace is not None and (not isinstance(trace, str) or len(trace) != 32
                              or any(c not in '0123456789abcdef' for c in trace)):
        return
    record = dict(stage=stage, trace=trace, pid=os.getpid(), at_ns=at_ns or time.monotonic_ns())
    try:
        from .storage import paths
        target = paths()['state'] / 'capture-timings.jsonl'
        fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, (json.dumps(record, separators=(',', ':')) + '\n').encode())
        finally:
            os.close(fd)
    except OSError:
        pass  # Measurement must never break capture or expose an OCR error payload.
