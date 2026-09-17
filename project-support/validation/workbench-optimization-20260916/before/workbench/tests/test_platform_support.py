import ctypes
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from local_workbench import platform_support as platform


class PlatformTests(unittest.TestCase):
    def test_native_lock_excludes_another_process_and_releases(self):
        with tempfile.TemporaryDirectory(prefix='review space ') as temporary:
            lock = Path(temporary)/'材料'/'.writer.lock'
            script = '''import sys
from local_workbench.platform_support import exclusive_lock
try:
    with exclusive_lock(sys.argv[1]): pass
except BlockingIOError: sys.exit(17)
'''
            env = dict(os.environ, PYTHONPATH=str(Path(platform.__file__).parents[1]))
            def attempt():
                return subprocess.run([sys.executable, '-c', script, str(lock)], env=env, capture_output=True)
            with platform.exclusive_lock(lock):
                self.assertEqual(attempt().returncode, 17)
            self.assertEqual(attempt().returncode, 0)
            with self.assertRaisesRegex(ValueError, 'intentional'):
                with platform.exclusive_lock(lock): raise ValueError('intentional')
            self.assertEqual(attempt().returncode, 0)

    def test_windows_lock_is_byte_zero_and_busy_retry_is_bounded_per_attempt(self):
        msvcrt = Mock(LK_NBLCK=2, LK_UNLCK=0)
        with tempfile.TemporaryFile('w+b') as handle, patch.object(platform, 'IS_WINDOWS', True), patch.dict(sys.modules, msvcrt=msvcrt):
            platform.lock_file(handle)
            self.assertEqual(handle.tell(), 0)
            self.assertEqual(os.fstat(handle.fileno()).st_size, 1)
            msvcrt.locking.assert_called_with(handle.fileno(), 2, 1)
            msvcrt.locking.side_effect = PermissionError(errno.EACCES, 'busy')
            with self.assertRaises(BlockingIOError): platform.lock_file(handle)
            msvcrt.locking.side_effect = [PermissionError(errno.EACCES, 'busy'), None]
            with patch.object(platform.time, 'sleep') as sleep:
                platform.lock_file(handle, blocking=True)
                sleep.assert_called_once_with(.05)
            msvcrt.locking.side_effect = None
            platform.unlock_file(handle)
            msvcrt.locking.assert_called_with(handle.fileno(), 0, 1)

    def test_windows_process_query_never_uses_kill_and_closes_handle(self):
        from ctypes import wintypes
        kernel = Mock(); kernel.OpenProcess.return_value = 987
        def exited(handle, pointer):
            ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD)).contents.value = 0
            return True
        kernel.GetExitCodeProcess.side_effect = exited
        self.assertFalse(platform._windows_process_alive(22, kernel))
        kernel.CloseHandle.assert_called_once_with(987)
        kernel.OpenProcess.return_value = 0
        with patch.object(ctypes, 'get_last_error', return_value=87, create=True):
            self.assertFalse(platform._windows_process_alive(22, kernel))
        with patch.object(ctypes, 'get_last_error', return_value=5, create=True):
            self.assertTrue(platform._windows_process_alive(22, kernel))
        with patch.object(platform, 'IS_WINDOWS', True), patch.object(platform, '_windows_process_alive', return_value=True) as query, patch.object(platform.os, 'kill') as kill:
            self.assertTrue(platform.process_alive(22)); query.assert_called_once_with(22); kill.assert_not_called()

    def test_environment_process_and_memory_branches(self):
        with patch.object(platform, 'IS_WINDOWS', True), patch.object(platform, '_windows_peak_rss', return_value=4096):
            self.assertEqual(platform.venv_python(Path('component')).as_posix(), 'component/.venv/Scripts/python.exe')
            self.assertEqual(platform.detached_process_kwargs()['creationflags'], 0x208)
            self.assertNotIn('start_new_session', platform.detached_process_kwargs())
            self.assertEqual(platform.peak_rss_bytes(), 4096)
        with patch.object(platform, 'IS_WINDOWS', False):
            self.assertEqual(platform.venv_python(Path('component')).as_posix(), 'component/.venv/bin/python')
            self.assertEqual(platform.detached_process_kwargs(), {'start_new_session': True})
        self.assertTrue(platform.process_alive(os.getpid()))
        self.assertFalse(platform.process_alive(0))
        self.assertTrue(platform.peak_rss_bytes() is None or platform.peak_rss_bytes() > 0)

    def test_launcher_uses_actual_source_for_an_isolated_reviewer(self):
        from local_workbench import __main__ as launcher
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'离线 review'
            argv = ['workbench', '--root', str(root), '--reviewer', '--no-browser']
            with patch.object(sys, 'argv', argv), patch.object(launcher, 'running', side_effect=[None,'http://127.0.0.1:1/']), patch.object(launcher.subprocess, 'Popen') as popen, patch('builtins.print'):
                launcher.main()
            command = popen.call_args.args[0]
            self.assertIn('--reviewer', command)
            self.assertEqual(popen.call_args.kwargs['env']['PYTHONPATH'], str(Path(launcher.__file__).resolve().parents[1]))
            self.assertNotEqual(popen.call_args.kwargs['env']['PYTHONPATH'], str(root/'src'))
            with patch.object(sys, 'argv', argv+['--serve']), patch.object(launcher, 'serve') as serve:
                launcher.main()
                serve.assert_called_once_with(root.resolve(), None, None, reviewer=True)

    def test_launcher_does_not_swallow_service_io_failure_or_reuse_wrong_mode(self):
        from local_workbench import __main__ as launcher
        from io import BytesIO
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'runtime').mkdir()
            (root/'runtime/server.json').write_text(json.dumps({'port':1,'instance':'fixture'}))
            response = BytesIO(json.dumps({'root':str(root),'instance':'fixture','mode':'coordinator'}).encode())
            with patch.object(launcher.urllib.request, 'urlopen', return_value=response):
                with self.assertRaisesRegex(RuntimeError, 'different workbench mode'): launcher.running(root, reviewer=True)
            with patch.object(sys, 'argv', ['workbench','--serve','--root',str(root)]), patch.object(launcher, 'serve', side_effect=BlockingIOError('storage failure')):
                with self.assertRaisesRegex(BlockingIOError, 'storage failure'): launcher.main()
