"""Isolated native portability smoke check. Never opens normal business stores."""
from __future__ import annotations
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]/'src'
sys.path.insert(0, str(SOURCE))
from local_workbench.platform_support import exclusive_lock, process_alive, venv_python, peak_rss_bytes


def main():
    with tempfile.TemporaryDirectory(prefix='aquaculture platform ') as temporary:
        root = Path(temporary)/'review 材料'; root.mkdir()
        lock = root/'writer.lock'
        script = '''import sys
from local_workbench.platform_support import exclusive_lock
try:
    with exclusive_lock(sys.argv[1]): pass
except BlockingIOError: sys.exit(17)
'''
        def probe():
            result = subprocess.run([sys.executable, '-c', script, str(lock)], capture_output=True,
                env=dict(os.environ, PYTHONPATH=str(SOURCE)))
            return result.returncode
        with exclusive_lock(lock): busy = probe()
        released = probe()
        checks = {'other_process_excluded': busy==17, 'lock_released': released==0,
            'current_process_alive': process_alive(os.getpid()), 'invalid_process_absent': not process_alive(0),
            'unicode_space_path': root.is_dir()}
        result = {'platform': platform.platform(), 'python': sys.version.split()[0],
            'platform_smoke': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
            'workbench_interpreter': str(venv_python(SOURCE.parent)),
            'peak_rss_bytes': peak_rss_bytes(),
            'windows_office_acceptance': 'PENDING_ACTUAL_WINDOWS',
            'scope': 'Temporary files and native process/lock checks only; no service or business data opened.'}
        print(json.dumps(result, indent=2))
        return 0 if all(checks.values()) else 1


if __name__=='__main__': raise SystemExit(main())
