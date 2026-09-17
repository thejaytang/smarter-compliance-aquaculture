"""Run local checks in their owning environments, without touching real data."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
WORKBENCH = ROOT / 'workbench'
BACKEND = WORKBENCH / 'backend'
TESTS = WORKBENCH / 'tests'


def python(component):
    return component / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', choices=['workbench', 'system1', 'system2', 'frontend', 'integration', 'all'], default='all', nargs='?')
    selected = parser.parse_args().suite
    checks = {
        'workbench': [(ROOT, [python(WORKBENCH), '-m', 'unittest', *[p.stem for p in sorted(TESTS.glob('test_*.py'))]], TESTS)],
        'system1': [(ROOT, [python(BACKEND/'system1'), '-m', 'unittest', 'discover', '-s', TESTS/'system1'], BACKEND/'system1/src', TESTS/'system1')],
        'system2': [(BACKEND/'system2', [python(BACKEND/'system2'), '-m', 'pytest', '-c', 'pyproject.toml'], BACKEND/'system2/src')],
        'frontend': [(ROOT, ['node', '--test', *sorted(TESTS.glob('test_*.mjs'))])],
        'integration': [(ROOT, [python(WORKBENCH), TESTS/'integration'/name], TESTS/'integration')
                        for name in ['architecture_migration.py', 'colleague_handoff.py']],
    }
    for name, commands in checks.items():
        if selected not in ('all', name): continue
        print('Checking ' + name, flush=True)
        for cwd, command, *sources in commands:
            env = dict(os.environ, PYTHONUTF8='1', PYTHONPYCACHEPREFIX=os.environ.get('PYTHONPYCACHEPREFIX',str(WORKBENCH/'runtime/cache/python')),
                       PYTHONPATH=os.pathsep.join(map(str, [WORKBENCH, BACKEND/'application', *sources])))
            subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)


if __name__ == '__main__':
    main()
