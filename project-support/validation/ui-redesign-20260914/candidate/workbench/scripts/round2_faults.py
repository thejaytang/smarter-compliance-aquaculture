"""Bounded real fault exercise for isolated round-two stores only."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from round2_verify import Client, ROOT, FIXTURE

def projection():
    path=FIXTURE/'workbench/runtime/system2-workflow/workflow.sqlite'
    result={}
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        for table in ('material_documents','material_revisions','material_candidates','material_receipts','material_conflicts'):
            digest=hashlib.sha256();count=0
            for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):
                digest.update(json.dumps(row,ensure_ascii=False).encode());count+=1
            result[table]={'rows':count,'sha256':digest.hexdigest()}
    return result

def restart():
    client=Client();old=client.get('/health');before=projection();start=time.time()
    client.post('/api/stop',{})
    lock=FIXTURE/'workbench/runtime/service.lock'
    with lock.open('a') as guard:
        for _ in range(150):
            try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:time.sleep(.1)
        else:raise RuntimeError('Isolated service did not finish shutdown')
    with (FIXTURE/'restart-fault.log').open('a') as log:
        process=subprocess.Popen([str(ROOT/'workbench/.venv/bin/python'),str(ROOT/'workbench/scripts/serve_round2_fixture.py')],
            stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
    for _ in range(100):
        try:
            newclient=Client();new=newclient.get('/health')
            if new['instance']!=old['instance']:break
        except Exception:pass
        if process.poll() is not None:raise RuntimeError('Isolated restart did not launch')
        time.sleep(.1)
    else:raise RuntimeError('Isolated restart unavailable')
    after=projection()
    result={'scope':'isolated57737_only','started_at':start,'finished_at':time.time(),
        'old_instance':old['instance'],'new_instance':new['instance'],'same_origin':newclient.origin==client.origin,
        'old_parent_source_changes':old.get('runtime_evidence',{}).get('parent_source_changes'),
        'new_parent_source_changes':new.get('runtime_evidence',{}).get('parent_source_changes'),
        'before':before,'after':after,'all_material_tables_preserved':before==after}
    path=ROOT/'project-support/reports/human-led-round2-20260911/fault-evidence.json'
    evidence=json.loads(path.read_text()) if path.exists() else {}
    if 'service_restart' in evidence:
        evidence.setdefault('service_restart_history',[]).append(evidence['service_restart'])
    result['in_continuous_run']=(FIXTURE/'soak.jsonl').exists() and not (FIXTURE/'soak-result.json').exists()
    result['diagnostic_allocations']=os.environ.get('ROUNDTWO_TRACE_ALLOCATIONS')=='1'
    evidence['service_restart']=result;path.write_text(json.dumps(evidence,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':restart()
