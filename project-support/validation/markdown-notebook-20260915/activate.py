"""Controlled normal parent activation with immutable pre-restart store copies."""
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request
from http.cookiejar import CookieJar
from datetime import datetime,timezone
import hashlib,json,sqlite3,subprocess,time,os,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.collaboration import Collaboration
base='http://127.0.0.1:62742'
opener=build_opener(HTTPCookieProcessor(CookieJar()))
def call(path,body=None,csrf=None):
    headers={'Content-Type':'application/json','Origin':base}
    if csrf:headers['X-CSRF-Token']=csrf
    with opener.open(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=40) as r:return json.load(r)
def logical(path):
    result={}
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in tables:
            rows=list(db.execute('SELECT * FROM "'+table.replace('"','""')+'"'));rows.sort(key=repr)
            h=hashlib.sha256()
            for row in rows:h.update(repr(row).encode());h.update(b'\n')
            result[table]={'rows':len(rows),'sha256':h.hexdigest()}
    return result
health=call('/health');assert health['root']==str(ROOT/'workbench')
state=call('/api/state');csrf=state['csrf'];assert not any(r['status'] in ('queued','running','waiting') for r in state['requests'])
assert not call('/api/automation')['settings']['enabled']
call('/api/actor',{'name':'Weijie Tang'},csrf)
paths=[ROOT/'workbench/runtime/workbench.sqlite',ROOT/'system1/Code/runtime/governance.sqlite',Path(health['runtime_evidence']['system2_runtime'])/'workflow.sqlite']
with sqlite3.connect(paths[0]) as db:
    for (raw,) in db.execute("SELECT data FROM collaboration_objects WHERE kind='workspace'"):
        c=object.__new__(Collaboration);c.mode='coordinator';c.root=ROOT/'workbench/runtime/collaboration';paths.append(c.workspace_runtime(json.loads(raw))/'workflow.sqlite')
backup=OUT/'activation-backup';backup.mkdir(exist_ok=False);stores=[]
for i,path in enumerate(dict.fromkeys(paths)):
    if not path.exists():continue
    target=backup/f'{i}-{path.name}'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(target) as dst:src.backup(dst)
    stores.append(dict(path=str(path),backup=str(target),logical_before=logical(target)))
    print('Backed up',path.relative_to(ROOT),flush=True)
manifest=dict(prepared_at=datetime.now(timezone.utc).isoformat(),before_instance=health['instance'],url=base,stores=stores,automation_enabled_before=False)
(OUT/'activation-prepared.json').write_text(json.dumps(manifest,indent=2))
call('/api/stop',{},csrf)
for _ in range(200):
    if not (ROOT/'workbench/runtime/server.json').exists():break
    time.sleep(.1)
else:raise RuntimeError('Normal service did not release its metadata; copies remain intact.')
env=dict(os.environ,PYTHONPATH=str(ROOT/'workbench/src'))
subprocess.run([str(ROOT/'workbench/.venv/bin/python'),'-m','local_workbench','--no-browser','--root',str(ROOT/'workbench')],env=env,check=True)
after=call('/health');assert after['instance']!=health['instance'];assert not after['runtime_evidence']['parent_source_changes']
for entry in stores:
    entry['logical_after']=logical(Path(entry['path']))
    entry['changed_tables']=[k for k in entry['logical_before'].keys()|entry['logical_after'].keys() if entry['logical_before'].get(k)!=entry['logical_after'].get(k)]
    print('Store comparison',Path(entry['path']).name,entry['changed_tables'],flush=True)
manifest.update(after_instance=after['instance'],runtime_evidence=after['runtime_evidence'],automation_enabled_after=call('/api/automation')['settings']['enabled'])
(OUT/'activation.json').write_text(json.dumps(manifest,indent=2))
print('Activated',base,flush=True)
