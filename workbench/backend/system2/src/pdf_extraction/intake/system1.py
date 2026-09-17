"""Read the existing System1 authority in its own environment; never apply decisions."""
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from ..platform_support import venv_python
from backend.shared.platform_support import system1_code, python_path
import subprocess
from backend.shared.timing import measured
from backend.shared.component_process import ComponentPool

_bridge_pool = ComponentPool()

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
    database_guard: tuple | None = None

    def assert_current(self):
        if any(_version(path) != version for path, version in self.versions.items()):
            raise IntakeError('system1_changed_during_handoff')
        if self.database_guard:
            code, config_path, version = self.database_guard
            if _bridge(code, config_path, 'authority_version') != version:
                raise IntakeError('system1_changed_during_handoff')


@measured('source.bridge')
def _bridge(code, config_path, command='read'):
    try:
        reply = _bridge_pool.request(venv_python(code), 'system1.workbench_bridge', code,
            dict(os.environ, PYTHONPATH=python_path(code / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1'),
            {'command': command, 'config': str(config_path)}, timeout=60)
        if reply.get('ok') is not True: raise ValueError('bridge_failed')
        return reply['data']
    except (ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise IntakeError('system1_invalid_read_receipt') from exc


def _source_open_issues(tasks):
    """Keep human source reports independent of a legacy System2 document ID."""
    result = []
    for task in tasks:
        root_issue = task.get('human_issue')
        if task.get('is_open') is False or not isinstance(root_issue,dict) or not task.get('source_id'):
            continue
        for issue in [root_issue, *root_issue.get('related_reports',[])]:
            if not isinstance(issue,dict) or issue.get('resolved') is True or str(issue.get('status','')).lower() in {'resolved','closed','completed'}:
                continue
            if not any(str(issue.get(key) or '').strip() for key in ('reason','message','description','note','action')):
                continue
            result.append({'task_id':task.get('operation_id'), **issue, 'source_id':task['source_id']})
    return result


def read_system1(system_root: Path, config_path: Path | None = None) -> System1Handoff:
    code = system1_code(system_root)
    config_path = config_path.resolve() if config_path else code / 'config/config.json'
    config_version = _version(config_path)
    config = json.loads(config_path.read_bytes())
    registry = (config_path.parent / config['workbook']).resolve()
    root = (config_path.parent / config['source_root']).resolve()
    database = bool(config.get('governance_db'))
    registry_version = None if database else _version(registry)
    assessment_path = (config_path.parent / config.get('log_root','../runtime/logs') / 'source-assessments.sqlite').resolve()
    assessment_version = _version(assessment_path) if not database and assessment_path.exists() else None
    records, registry_hash = ([], '') if database else read_registry(registry)
    if not database and registry_hash != registry_version[-1]: raise IntakeError('system1_changed_during_handoff')
    data = _bridge(code, config_path)
    try:
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
        if database:
            owner = data['authority']
            if owner['kind'] != 'sqlite' or not isinstance(owner['version'],dict) or owner['version'].get('revision') != owner['revision']:
                raise ValueError('database_authority_missing')
            registry_hash = owner['state_sha256']
            if not isinstance(registry_hash,str) or len(registry_hash)!=64 or any(c not in '0123456789abcdef' for c in registry_hash):
                raise ValueError('database_snapshot_hash_missing')
            records = [dict(source,registry_kind='sqlite_snapshot') for source in sources]
        elif set(authority) != {r['source_id'] for r in records}:
            raise ValueError('bridge_registry_identity_mismatch')
        # The authority computes selection. No scores or human history are reinterpreted here.
        records = [dict(row, selection_status=authority[row['source_id']]['effective_selection'],
                        selection_origin=authority[row['source_id']].get('selection_origin','human'),
                        assessment_id=authority[row['source_id']].get('assessment_id')) for row in records]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise IntakeError('system1_invalid_read_receipt') from exc
    versions = {config_path: config_version}
    if registry_version is not None: versions[registry] = registry_version
    if assessment_version is not None:
        versions[assessment_path] = assessment_version
    handoff = System1Handoff(records, registry_hash, root, {
        'schema_version': 'system1-handoff/2' if database else 'system1-handoff/1', 'selection_authority': 'system1.workbench_bridge.read',
        'registry_kind': 'sqlite_snapshot' if database else 'workbook',
        'original_issues':[{'task_id':t['operation_id'],**issue,'source_id':t['source_id']} for t in data.get('tasks',[]) if t.get('human_issue') for issue in [t['human_issue'],*t['human_issue'].get('related_reports',[])] if issue.get('system2_document_id')],
        'source_open_issues': _source_open_issues(data.get('tasks',[])),
        'bridge_revision': revision, 'registry_sha256': registry_hash, 'config_sha256': config_version[-1],
        'sources': {sid: {'source_revision': s['source_revision'], 'effective_selection': s['effective_selection']}
                    for sid, s in authority.items()},
    }, versions, (code,config_path,data['authority']['version']) if database else None)
    handoff.assert_current()
    return handoff
