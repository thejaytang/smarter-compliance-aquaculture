"""Read the existing System1 authority in its own environment; never apply decisions."""
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

from .registry import IntakeError, read_registry


def _version(path):
    stat = path.stat()
    return (stat.st_ino, stat.st_size, stat.st_mtime_ns, sha256(path.read_bytes()).hexdigest())


@dataclass
class System1Handoff:
    records: list[dict]
    registry_sha256: str
    source_root: Path
    evidence: dict
    versions: dict[Path, tuple]

    def assert_current(self):
        if any(_version(path) != version for path, version in self.versions.items()):
            raise IntakeError('system1_changed_during_handoff')


def read_system1(system_root: Path, config_path: Path | None = None) -> System1Handoff:
    code = system_root.resolve() / 'Code'
    config_path = config_path.resolve() if config_path else code / 'config/config.json'
    config_version = _version(config_path)
    config = json.loads(config_path.read_bytes())
    registry = (config_path.parent / config['workbook']).resolve()
    root = (config_path.parent / config['source_root']).resolve()
    registry_version = _version(registry)
    records, registry_hash = read_registry(registry)
    if registry_hash != registry_version[-1]:
        raise IntakeError('system1_changed_during_handoff')
    process = subprocess.run(
        [str(code / '.venv/bin/python'), '-m', 'system1.workbench_bridge'],
        input=json.dumps({'command': 'read', 'config': str(config_path)}),
        capture_output=True, text=True, cwd=code,
        env=dict(os.environ, PYTHONPATH=str(code / 'src'), PYTHONDONTWRITEBYTECODE='1'), timeout=60,
    )
    try:
        reply = json.loads(process.stdout)
        if process.returncode or reply.get('ok') is not True:
            raise ValueError('bridge_failed')
        data = reply['data']
        sources, revision = data['sources'], data['revision']
        if not isinstance(sources, list) or not isinstance(revision, str) or not revision:
            raise ValueError('bridge_shape')
        authority = {}
        for source in sources:
            sid = source['source_id']
            if sid in authority or source['effective_selection'] not in ('INCLUDE', 'PENDING', 'EXCLUDE'):
                raise ValueError('bridge_source_invalid')
            if not isinstance(source['source_revision'], str) or not source['source_revision']:
                raise ValueError('bridge_source_revision_missing')
            authority[sid] = source
        if set(authority) != {r['source_id'] for r in records}:
            raise ValueError('bridge_registry_identity_mismatch')
        # The authority computes selection. No scores or human history are reinterpreted here.
        records = [dict(row, selection_status=authority[row['source_id']]['effective_selection']) for row in records]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise IntakeError('system1_invalid_read_receipt') from exc
    handoff = System1Handoff(records, registry_hash, root, {
        'schema_version': 'system1-handoff/1', 'selection_authority': 'system1.workbench_bridge.read',
        'bridge_revision': revision, 'registry_sha256': registry_hash, 'config_sha256': config_version[-1],
        'sources': {sid: {'source_revision': s['source_revision'], 'effective_selection': s['effective_selection']}
                    for sid, s in authority.items()},
    }, {config_path: config_version, registry: registry_version})
    handoff.assert_current()
    return handoff
