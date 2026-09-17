"""Component-local standard-library platform primitives; no global dependencies."""
from __future__ import annotations
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import time

IS_WINDOWS = os.name == 'nt'


def venv_python(component_root):
    return Path(component_root) / '.venv' / ('Scripts/python.exe' if IS_WINDOWS else 'bin/python')


def lock_file(handle, *, blocking=False):
    """Lock byte zero on Windows, the file on POSIX. The handle must stay open."""
    if not IS_WINDOWS:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        return
    import msvcrt
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b'\0'); handle.flush()
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            if not blocking:
                raise BlockingIOError(errno.EAGAIN, 'Another local process holds the lock.') from None
            time.sleep(.05)


def unlock_file(handle):
    if IS_WINDOWS:
        import msvcrt
        handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def exclusive_lock(path, *, blocking=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        lock_file(handle, blocking=blocking)
        try: yield handle
        finally: unlock_file(handle)

