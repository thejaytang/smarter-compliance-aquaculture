"""Controlled local parent restart; no business review or schedule change."""
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request
from http.cookiejar import CookieJar
import hashlib
import json
import sqlite3
import subprocess
import time
import os
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
base='http://127.0.0.1:62742'
opener=build_opener(HTTPCookieProcessor(CookieJar()))
def call(path,body=None,csrf=None):
    headers={'Content-Type':'application/json','Origin':base}
    if csrf:headers['X-CSRF-Token']=csrf
    with opener.open(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=40) as response:
        return json.load(response)
health=call('/health')
assert health['root']==str(ROOT/'workbench')
state=call('/api/state');csrf=state['csrf']
assert not any(r['status'] in ('queued','running','waiting') for r in state['requests'])
automation=call('/api/automation')
assert not automation['settings']['enabled'], 'Preserve currently running schedules; restart requires a separate check.'
call('/api/actor',{'name':'Weijie Tang'},csrf)
paths=[ROOT/'workbench/runtime/workbench.sqlite',ROOT/'system1/Code/runtime/governance.sqlite',Path(health['runtime_evidence']['system2_runtime'])/'workflow.sqlite']
# Include the actual saved personal material stores, not fixture runtimes.
with sqlite3.connect(paths[0]) as db:
    for (raw,) in db.execute("SELECT data FROM collaboration_objects WHERE kind='workspace'"):
        workspace=json.loads(raw)
        from local_workbench.collaboration import Collaboration
        c=object.__new__(Collaboration);c.mode='coordinator';c.root=ROOT/'workbench/runtime/collaboration'
        paths.append(c.workspace_runtime(workspace)/'workflow.sqlite')
backup=OUT/'activation-backup';backup.mkdir(exist_ok=True)
manifest=[]
for i,path in enumerate(dict.fromkeys(paths)):
    if not path.exists():continue
    target=backup/f'{i}-{path.name}'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as destination:
        source.backup(destination)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.append({'path':str(path),'backup':str(target),'before_sha256':digest})
    print('Backed up:',path.relative_to(ROOT),flush=True)
call('/api/stop',{},csrf)
for _ in range(100):
    try:call('/health')
    except OSError:break
    time.sleep(.1)
env=dict(os.environ,PYTHONPATH=str(ROOT/'workbench/src'))
subprocess.run([str(ROOT/'workbench/.venv/bin/python'),'-m','local_workbench','--no-browser','--root',str(ROOT/'workbench')],env=env,check=True)
after=call('/health');assert after['instance']!=health['instance']
assert not after['runtime_evidence']['parent_source_changes']
assert after['runtime_evidence']['parent_startup_sources']['requirements.py']==hashlib.sha256((ROOT/'workbench/src/local_workbench/requirements.py').read_bytes()).hexdigest()
for entry in manifest:
    entry['after_sha256']=hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()
    entry['unchanged']=entry['before_sha256']==entry['after_sha256']
(OUT/'activation.json').write_text(json.dumps({'before_instance':health['instance'],'after_instance':after['instance'],'url':base,'runtime_evidence':after['runtime_evidence'],'stores':manifest,'automation_enabled_before':False,'automation_enabled_after':call('/api/automation')['settings']['enabled']},indent=2))
print('Activated',base,'with',len(manifest),'database backups.',flush=True)
print('Unchanged stores:',all(x['unchanged'] for x in manifest),flush=True)
