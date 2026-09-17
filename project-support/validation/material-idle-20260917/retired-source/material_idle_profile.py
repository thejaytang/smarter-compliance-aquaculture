"""Measure real component startups against an isolated, empty material queue.

Run using this checkout's Workbench Python on macOS or Windows. This does not
open the live workspace, restore a seed, parse a source or call an AI service.
It measures idle scheduling only, not browser performance or Windows acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
WORKBENCH = ROOT / 'workbench'
for source in (WORKBENCH, WORKBENCH / 'backend/application'):
    sys.path.insert(0, str(source))

from backend.shared.platform_support import python_path, venv_python
from local_workbench.adapter import System2
from local_workbench.collaboration import Collaboration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=3, choices=range(1, 11))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Choose a new report path; existing files are never overwritten.')
    component = WORKBENCH / 'backend/system2'
    child_python = venv_python(component)
    if not child_python.is_file():
        parser.error('The existing System2 environment is required. No environment was changed.')
    calls = []
    with tempfile.TemporaryDirectory(prefix='wb-idle-') as temporary:
        runtime = Path(temporary) / 'personal'
        env = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=python_path(component / 'src'),
                   PYTHONPYCACHEPREFIX=str(Path(temporary) / 'bytecode'))
        subprocess.run([str(child_python), '-c',
                        'from pdf_extraction.review.materials import MaterialStore; '
                        'import sys; MaterialStore(sys.argv[1])', str(runtime)],
                       env=env, cwd=component, check=True, capture_output=True, timeout=60)
        adapter = System2(component, WORKBENCH / 'backend/system1', runtime=runtime)
        delegate = adapter.call
        def measured(command, **kwargs):
            start = time.perf_counter()
            try:
                return delegate(command, **kwargs)
            finally:
                calls.append({'command': command,
                              'round_trip_ms': round((time.perf_counter() - start) * 1000, 3)})
        adapter.call = measured
        scheduler = object.__new__(Collaboration)
        scheduler.all = lambda kind: [{'id': 'isolated-empty-workspace'}]
        scheduler.workspace_runtime = lambda workspace: runtime
        scheduler.adapter = lambda path: adapter
        timings = {}
        # The pre-change implementation unconditionally ran both commands per
        # personal workspace. Retain that exact sequence as the comparison.
        for mode in ('previous_idle_dispatch', 'guarded_idle_dispatch'):
            durations = []
            calls.clear()
            before = hashlib.sha256((runtime / 'workflow.sqlite').read_bytes()).hexdigest()
            for _ in range(args.rounds):
                start = time.perf_counter()
                if mode == 'previous_idle_dispatch':
                    assert adapter.call('material_tick')['status'] == 'idle'
                    adapter.call('material_repeat-resolution', request={})
                else:
                    assert scheduler.tick() == {'status': 'idle'}
                durations.append(round((time.perf_counter() - start) * 1000, 3))
            after = hashlib.sha256((runtime / 'workflow.sqlite').read_bytes()).hexdigest()
            timings[mode] = {'durations_ms': durations, 'median_ms': statistics.median(durations),
                             'component_calls': list(calls), 'database_unchanged': before == after}
            if mode == 'guarded_idle_dispatch':
                assert not calls and before == after
    report = {'platform': platform.system(), 'architecture': platform.machine(),
              'native_windows': sys.platform == 'win32', 'rounds': args.rounds,
              'scope': 'isolated idle scheduling; not material open or browser acceptance',
              'live_workspace_accessed': False, 'timings': timings}
    raw = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding='utf-8')
    print(raw)


if __name__ == '__main__':
    main()
