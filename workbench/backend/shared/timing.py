"""Opt-in local timings. Never record request payloads, source text or credentials."""
from contextlib import contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import threading
import time

_write_lock = threading.Lock()


@contextmanager
def span(label):
    folder = os.environ.get('WORKBENCH_TIMING_DIR')
    if not folder:
        yield
        return
    started = time.perf_counter()
    try:
        yield
    finally:
        record = {'label': label, 'pid': os.getpid(), 'thread': threading.get_ident(),
                  'start': started, 'seconds': time.perf_counter() - started}
        try:
            # One file per process; one append per record. Diagnostic failure must
            # never change the outcome of a business operation.
            with _write_lock, (Path(folder) / f'timing-{os.getpid()}.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record) + '\n')
        except OSError:
            pass


def measured(label):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(label):
                return function(*args, **kwargs)
        return wrapped
    return decorate
