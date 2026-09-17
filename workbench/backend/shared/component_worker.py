"""Pipe-only worker retaining imports, never service instances or business snapshots."""
import contextlib
import importlib
import io
import json
import os
import sys

from backend.shared.timing import span

ALLOWED = {'system1.workbench_bridge', 'pdf_extraction.orchestration.material_service',
           'pdf_extraction.orchestration.workflow'}


def main():
    module = sys.argv[1]
    if module not in ALLOWED:
        raise ValueError('Unsupported component module.')
    with span('component.import'):
        entry = importlib.import_module(module).main
    source, output = sys.stdin, sys.stdout
    if os.environ.get('WORKBENCH_COMPONENT_READY_PROTOCOL') == '1':
        output.write(json.dumps({'ready': module}) + '\n')
        output.flush()
    for line in source:
        message = json.loads(line)
        captured = io.StringIO()
        try:
            # Each existing CLI reconstructs its owning service and checks fresh
            # config, authority, source hashes and versions for every request.
            sys.stdin = io.StringIO(json.dumps(message['payload']))
            with contextlib.redirect_stdout(captured), span('component.execute'):
                try:
                    entry()
                except SystemExit as exc:
                    if exc.code not in (None, 0, 1):
                        raise
            reply = json.loads(captured.getvalue())
        except Exception:
            reply = {'ok': False, 'error': 'Component did not return a valid receipt. Check saved state before retrying the same request.'}
        finally:
            sys.stdin = source
        output.write(json.dumps({'id': message['id'], 'reply': reply}, ensure_ascii=False) + '\n')
        output.flush()


if __name__ == '__main__':
    main()
