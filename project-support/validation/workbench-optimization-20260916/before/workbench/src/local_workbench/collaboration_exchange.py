"""Portable, bounded collaboration payloads, separate from the small manifest."""
from .collaboration_package import build_package, read_package, _load_json, _path
import json


def pack(kind, metadata, files):
    if 'review.json' in files:
        raise ValueError('Reserved collaboration payload name.')
    files = dict(files)
    files['review.json'] = json.dumps(metadata, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')
    return build_package(kind, {'id': metadata['id'], 'payload': 'review.json'}, files)


def unpack(blob):
    package = read_package(blob)
    manifest = package['metadata']
    if manifest != {'id': package['package_id'], 'payload': 'review.json'}:
        raise ValueError('Unsupported collaboration payload descriptor.')
    if 'review.json' not in package['files']:
        raise ValueError('Collaboration payload is missing.')
    metadata = _load_json(package['files'].pop('review.json'))
    if not isinstance(metadata, dict) or metadata.get('id') != package['package_id']:
        raise ValueError('Collaboration payload identity mismatch.')
    package['metadata'] = metadata
    return package


def segment(value):
    if not isinstance(value, str) or '/' in value:
        raise ValueError('Expected a single portable source filename.')
    _path(value)
    return value
