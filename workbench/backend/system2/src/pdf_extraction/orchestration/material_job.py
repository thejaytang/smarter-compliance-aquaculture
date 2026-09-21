"""Pure candidate computation: immutable original in, isolated artifacts out.

Business-store writes belong to MaterialService.finish_job under the application
operation gate. This process never opens a business database.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import uuid


def compute(root, job):
    from ..contracts.source import Snapshot
    from .material_parser import parse_material
    root = Path(root).resolve()
    source = job['source']
    fingerprint = source['content_hash']
    suffix = '.' + source['file_format'].lower().lstrip('.')
    if len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
        raise ValueError('invalid_original_fingerprint')
    if suffix not in {'.pdf', '.html', '.htm', '.xlsx', '.xls'}:
        raise ValueError('material_format_not_supported_use_source_follow_up')
    # IDs and a fresh attempt directory are resolved here, not supplied as paths.
    material_id = str(uuid.UUID(job['material_id'])).replace('-', '')
    if material_id != job['material_id']:
        raise ValueError('Invalid material identity.')
    candidate_id = str(uuid.UUID(job['candidate_id']))
    if candidate_id != job['candidate_id']:
        raise ValueError('Invalid candidate identity.')
    # Personal workspace roots are already deep on Windows. Keep a full unique
    # attempt ID, with material/candidate identities in evidence rather than
    # three nested identifier directories. Earlier artifacts remain untouched.
    attempt_id = uuid.uuid4().hex
    output = root / 'material-artifacts' / attempt_id
    original = root / 'material-originals' / (fingerprint + suffix)
    copied = Snapshot(**dict(source, relative_path=original.name))
    try:
        parsed = parse_material(copied, original.parent, output)
    finally:
        if output.is_dir():
            with (output / 'attempt-binding.json').open('x', encoding='utf-8') as stream:
                json.dump({'schema':'material-attempt/1','attempt_id':attempt_id,**job}, stream, ensure_ascii=False, indent=2)
    return dict(parsed, artifact_directory=output.relative_to(root).as_posix(), attempt_id=attempt_id)


def main():
    envelope = json.load(sys.stdin)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = compute(envelope['root'], envelope['request'])
        reply = {'ok': True, 'data': result}
    except Exception as exc:
        # A failed extraction is retained candidate evidence, never a confirmation.
        reply = {'ok': True, 'data': {'blocks': [], 'status': 'failed', 'error': str(exc)}}
    print(json.dumps(reply, ensure_ascii=False))


if __name__ == '__main__':
    main()
