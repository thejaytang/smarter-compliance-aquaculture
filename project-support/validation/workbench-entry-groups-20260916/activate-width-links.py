"""Controlled activation; preserves source/business rows and snapshots all owning stores."""
from pathlib import Path
from contextlib import closing
from urllib.request import build_opener, HTTPCookieProcessor, Request
from http.cookiejar import CookieJar
import hashlib,json,sqlite3,subprocess,time,os,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent / 'activation-width-links';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.recovery import layout,quiescent
base='http://127.0.0.1:62742';opener=build_opener(HTTPCookieProcessor(CookieJar()))
def call(path,body=None,csrf=None):
 headers={'Content-Type':'application/json','Origin':base}
 if csrf:headers['X-CSRF-Token']=csrf
 with opener.open(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=60) as r:return json.load(r)
def logical(path):
 out={}
 with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
  for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
   rows=sorted(db.execute('SELECT * FROM "'+name.replace('"','""')+'"').fetchall(),key=repr)
   out[name]={'rows':len(rows),'sha256':hashlib.sha256(repr(rows).encode()).hexdigest()}
 return out
health=call('/health');assert health['root']==str(ROOT/'workbench')
state=call('/api/state');csrf=state['csrf'];assert not any(r['status'] in ('queued','running','waiting') for r in state['requests'])
assert not call('/api/automation')['settings']['enabled']
call('/api/actor',{'name':'Weijie Tang'},csrf)
info=layout(ROOT);backup=OUT/'activation-backup';backup.mkdir(exist_ok=False)
call('/api/stop',{},csrf)
for _ in range(300):
 if not (ROOT/'workbench/runtime/server.json').exists():break
 time.sleep(.1)
else:raise RuntimeError('Service has not finished draining its workers.')
records=[]
try:
 with quiescent(ROOT,info):
  for i,path in enumerate(info['stores']):
   dest=backup/f'{i}-{path.name}'
   with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(dest)) as dst:src.backup(dst)
   records.append(dict(path=str(path.relative_to(ROOT)),backup=dest.name,before=logical(dest)))
 (backup/'manifest.json').write_text(json.dumps(records,indent=2))
finally:
 subprocess.run([str(ROOT/'workbench/.venv/bin/python'),'-m','local_workbench','--no-browser','--root',str(ROOT/'workbench')],env=dict(os.environ,PYTHONPATH=str(ROOT/'workbench/src')),check=True)
after=call('/health');assert health['instance']!=after['instance'];assert not after['runtime_evidence']['parent_source_changes']
state=call('/api/state');call('/api/actor',{'name':'Weijie Tang'},state['csrf'])
with closing(sqlite3.connect(ROOT/'workbench/runtime/workbench.sqlite')) as db:uid=db.execute('SELECT id FROM requirement_units WHERE actor=? LIMIT 1',('Weijie Tang',)).fetchone()
if uid:
 try:call('/api/interpretations?unit_id='+uid[0])
 except Exception as e:print('Context read boundary:',type(e).__name__)
for entry in records:
 entry['after']=logical(ROOT/entry['path'])
 entry['changed_existing_tables']=[k for k in entry['before'] if entry['before'][k]!=entry['after'].get(k)]
 entry['added_tables']=sorted(set(entry['after'])-set(entry['before']))
 entry['business_unchanged']=all(entry['before'].get(k)==entry['after'].get(k) for k in ('requirement_sessions','requirement_steps','requirement_units','requirement_interpretations','interpretation_history','material_documents') if k in entry['before'])
 with closing(sqlite3.connect(ROOT/entry['path'])) as db:entry['foreign_key_violations']=db.execute('PRAGMA foreign_key_check').fetchall()
assert all(r['business_unchanged'] and not r['foreign_key_violations'] for r in records)
assets={}
for name in ['markdown-content.js','markdown-content.css','quantity.js','requirement-structure.js','requirement-source.js','interpretations.js','requirements.js','requirements.css']:
 with opener.open(base+'/'+name) as r:assets[name]=r.read()==(ROOT/'workbench/ui'/name).read_bytes()
result=dict(url=base,health=after,stores=records,served_assets_match=assets,ai_status=call('/api/settings/ai')['status'],automation_enabled=call('/api/automation')['settings']['enabled'])
(OUT/'activation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(stores=len(records),business_unchanged=all(r['business_unchanged'] for r in records),assets_match=all(assets.values()),ai_status=result['ai_status'],automation_enabled=result['automation_enabled'])))
