"""Explicit recovery of one proven truncated import payload through its owning store.

Run with System1's environment and the Workbench service stopped. No source,
original, or historical row is removed. The previous value remains in history.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from contextlib import closing
from urllib.request import urlopen

import human_operations as h
import source_updater as u
from system1.governance_store import GovernanceStore, set_business_value
from system1.workbook_guard import exclusive_process_lock


def main():
    root = Path(__file__).resolve().parents[2]
    workbench = root / 'workbench'
    state = json.loads((workbench / 'runtime/state/listen-port.json').read_text())
    try:
        with urlopen(f"http://127.0.0.1:{state['port']}/health", timeout=2):
            pass
    except OSError:
        pass
    else:
        raise RuntimeError('Stop Workbench before the explicit recovery.')
    rid = '7bf55632-249e-5039-9bc3-a03452b19ee9'
    opid = 'SYNC-' + rid
    with closing(sqlite3.connect((workbench / 'workspace/databases/system2.sqlite').as_uri() + '?mode=ro', uri=True)) as db:
        request = json.loads(db.execute(
            "SELECT data FROM collaboration_objects WHERE kind='sync_source_pending' AND key=?", (rid,)
        ).fetchone()[0])
    assert request['expected_source_revision'] is None
    assert request['source']['source_id'] == 'PE001'
    assert request['package_id'] == '8ca47f11-7bd3-4539-b7ea-4dbee796cd6c'
    receipt = dict(status='synchronized', source_id='PE001', operation_id=opid,
                   actor=request['actor'], request_id=rid)
    digest = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    payload = json.dumps(dict(request_digest=digest, receipt=receipt, before=None,
                             incoming=request['source'], source_evidence=request['evidence'],
                             snapshot_id=request['package_id']), sort_keys=True, ensure_ascii=False, default=str)
    cfg = u.read_config(workbench / 'runtime/settings/system1/config.json')
    store = GovernanceStore(cfg['governance_db'])
    with exclusive_process_lock(cfg['log_root'] / '.system1-run.lock'), u.registry_lock(cfg, 12):
        wb = u.open_registry(cfg)
        try:
            ops = wb[h.human_sheet_name(cfg)]
            headers = h.operation_headers(ops)
            row = h.operation_index(ops, headers)[opid]
            record = h.operation_record(ops, row, headers)
            if record['payload_json'] == payload:
                print(json.dumps({'status': 'already_repaired', 'operation_id': opid}))
                return
            assert record['source_id'] == 'PE001' and record['operator'] == request['actor']
            assert record['program_status'] == 'APPLIED'
            assert len(record['payload_json']) == 32767
            assert record['payload_json'] == payload[:32767]
            backup = workbench / 'runtime/backups/collaboration-20261009/system1-before-payload-repair.sqlite'
            store.backup(backup)
            revision = wb._governance_revision
            wb._governance_actor = request['actor']
            set_business_value(ops.cell(row, headers['payload_json']), payload)
            u.save_registry(wb, cfg, revision)
        finally:
            wb.close()
    saved = next(x['record'] for x in store.snapshot()['operations'] if x['id'] == opid)
    assert saved['payload_json'] == payload
    print(json.dumps({'status': 'repaired', 'operation_id': opid, 'characters': len(payload),
                      'backup': str(backup.relative_to(root)), 'revision': store.revision()}))


if __name__ == '__main__':
    main()
