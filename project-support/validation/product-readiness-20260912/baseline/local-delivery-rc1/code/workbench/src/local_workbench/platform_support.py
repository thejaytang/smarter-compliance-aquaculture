"""Component-local standard-library platform primitives; no global dependencies."""
from __future__ import annotations
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import subprocess
import sys
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


def _windows_process_alive(pid, kernel=None):
    """Query process state without os.kill, which can terminate Windows processes."""
    import ctypes
    from ctypes import wintypes
    kernel = kernel or ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        # Invalid PID means absent; access denied/unknown must conservatively block maintenance.
        return ctypes.get_last_error() != 87
    try:
        result = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(result)): return True
        return result.value == 259  # STILL_ACTIVE
    finally: kernel.CloseHandle(handle)


def process_alive(pid):
    pid = int(pid)
    if pid <= 0: return False
    if IS_WINDOWS: return _windows_process_alive(pid)
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    except PermissionError: return True
    return True


def detached_process_kwargs():
    if IS_WINDOWS:
        return {'creationflags': getattr(subprocess, 'DETACHED_PROCESS', 0x8) |
                getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200), 'close_fds': True}
    return {'start_new_session': True}


def _windows_peak_rss():
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return int(counters.PeakWorkingSetSize)


def peak_rss_bytes():
    if IS_WINDOWS:
        try: return _windows_peak_rss()
        except (OSError, AttributeError): return None
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
