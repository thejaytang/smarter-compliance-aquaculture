"""Read-only comparison of durable review versions and replaceable Excel snapshots."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from local_workbench.sqlite_support import connect as connect_sqlite
import time


def read_status(runtime, worker=None):
    runtime = Path(runtime)
    result = {'status': 'pending', 'decisions': 'saved'}
    try:
        marker = runtime / 'workbook.json'
        if marker.is_file():
            result.update({k: v for k, v in json.loads(marker.read_text()).items() if k != 'path'})
        with connect_sqlite((runtime / 'workflow.sqlite').as_uri()+'?mode=ro', uri=True, timeout=.2) as db:
            db.execute('BEGIN')
            cursor = db.execute('SELECT COALESCE(MAX(sequence),0) FROM events').fetchone()[0]
            policy = db.execute('SELECT COALESCE(MAX(revision),0) FROM policies').fetchone()[0]
        result.update(saved_event_cursor=cursor, saved_policy_revision=policy)
        current = (result.get('event_cursor') == cursor and result.get('policy_revision') == policy)
        source=json.loads((runtime/'source-version.json').read_text())
        if (source.get('schema')!='system2-source-version/1' or source.get('status')!='checked'
                or not source.get('registry_sha256') or source.get('registry_kind') not in {'workbook','sqlite_snapshot'}):
            raise ValueError('The source authority has not been checked successfully')
        if time.time()-source.get('checked_at',0)>30:
            raise ValueError('The source check is older than 30 seconds; waiting for the local worker')
        result.update(saved_registry_sha256=source['registry_sha256'],saved_registry_kind=source['registry_kind'],
                      source_checked_at=source['checked_at'])
        source_changed=result.get('registry_sha256')!=source['registry_sha256'] or result.get('registry_kind')!=source['registry_kind']
        current=current and not source_changed
        if source_changed:result['message']='Source information changed; Excel synchronization is pending.'
        if marker.is_file():
            current = current and Path(json.loads(marker.read_text())['path']).is_file()
        worker = worker or {}
        if worker.get('status') in {'failed', 'pending_refresh'}:
            result.update(status='failed', message=worker.get('message', 'Excel sync failed; retry is scheduled.'))
        elif current:
            result['status'] = 'current'
        else:
            result['status'] = 'refreshing' if worker.get('status') == 'refreshing' else 'pending'
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        # Do not turn an unreadable version marker into a completed snapshot.
        result.update(status='unknown', message='Excel version could not be checked: '+str(exc))
    return result


def cached_snapshot(runtime):
    """Return only bytes matching the advertised immutable snapshot hash/version."""
    marker = Path(runtime) / 'workbook.json'
    for _ in range(2):
        try:
            raw = marker.read_bytes()
            meta = json.loads(raw)
            data = Path(meta['path']).read_bytes()
            if sha256(data).hexdigest() == meta['sha256'] and marker.read_bytes() == raw:
                return meta, data
        except (OSError, ValueError, KeyError):
            pass
    raise ValueError('The Excel snapshot is not ready or changed during download. Reviews remain saved; retry after synchronization.')
