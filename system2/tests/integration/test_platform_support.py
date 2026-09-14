import errno
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock
import pytest
from pdf_extraction import platform_support as platform


def test_worker_lock_excludes_other_process_and_releases(tmp_path):
    lock = tmp_path/'review 材料'/'.material-worker.lock'
    command = '''import sys
from pdf_extraction.platform_support import exclusive_lock
try:
    with exclusive_lock(sys.argv[1]): pass
except BlockingIOError: sys.exit(17)
'''
    env = dict(os.environ, PYTHONPATH=str(Path(platform.__file__).parents[1]))
    def probe(): return subprocess.run([sys.executable, '-c', command, str(lock)], env=env, capture_output=True).returncode
    with platform.exclusive_lock(lock): assert probe()==17
    assert probe()==0


def test_windows_worker_lock_and_interpreter(monkeypatch, tmp_path):
    msvcrt = Mock(LK_NBLCK=2, LK_UNLCK=0)
    monkeypatch.setitem(sys.modules, 'msvcrt', msvcrt)
    monkeypatch.setattr(platform, 'IS_WINDOWS', True)
    assert platform.venv_python(tmp_path)==tmp_path/'.venv/Scripts/python.exe'
    with (tmp_path/'.worker.lock').open('a+b') as handle:
        platform.lock_file(handle)
        assert handle.tell()==0
        assert os.fstat(handle.fileno()).st_size==1
        msvcrt.locking.assert_called_with(handle.fileno(), 2, 1)
        msvcrt.locking.side_effect = PermissionError(errno.EACCES, 'busy')
        with pytest.raises(BlockingIOError): platform.lock_file(handle)
        msvcrt.locking.side_effect = None
        platform.unlock_file(handle)
        msvcrt.locking.assert_called_with(handle.fileno(), 0, 1)
