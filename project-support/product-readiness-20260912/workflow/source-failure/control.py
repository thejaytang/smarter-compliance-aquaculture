"""Reversible missing-original fault for isolated TS004; no business-store writes."""
from pathlib import Path
from hashlib import sha256
import json,sqlite3,sys,select,time
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[4];E=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'system2/src'))
from pdf_extraction.platform_support import lock_file,unlock_file
reading='--reading' in sys.argv
checkpoint='before-reader.sqlite' if reading else 'before.sqlite'
record='reader-manifest.json' if reading else 'manifest.json'
base=R/'workbench/runtime/product-readiness-20260912/ui-fault-fixture/workbench/runtime/collaboration/personal'
found=[]
for p in base.glob('*/workflow.sqlite'):
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  row=db.execute("select data from material_documents where source_id='TS004'").fetchone()
  if row:found.append((p,json.loads(row[0])))
assert len(found)==1, 'Exactly one isolated TS004 workspace required'
database,data=found[0];assert data['revision']==(8 if reading else 6) and data['id']=='64288fd5d09b988850ce7a31992b286b'
pin=database.parent/'material-originals'/(data['source']['content_hash']+'.html');held=pin.with_suffix('.html.engineering-held')
assert pin.is_file() and not held.exists();assert sha256(pin.read_bytes()).hexdigest()==data['source']['content_hash']
assert not (E/checkpoint).exists(), 'Do not overwrite a preceding checkpoint'
with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(E/checkpoint) as dst:
 src.backup(dst);assert dst.execute('pragma integrity_check').fetchone()[0]=='ok'
manifest={'scope':'Isolated TS004 pinned HTML only; no original bytes rewritten, no DB mutation by harness','database':str(database.relative_to(R)),'pin':str(pin.relative_to(R)),'held':str(held.relative_to(R)),'original_sha256':data['source']['content_hash'],'backup_sha256':sha256((E/checkpoint).read_bytes()).hexdigest(),'before_revision':data['revision'],'events':[]}
def event(action):
 manifest['events'].append({'action':action,'time':datetime.now(timezone.utc).isoformat()});(E/record).write_text(json.dumps(manifest,indent=2)+'\n');print(action,flush=True)
def restore():
 if held.exists():
  assert not pin.exists(),'Refuse to overwrite a concurrently restored original'
  held.rename(pin)
 assert sha256(pin.read_bytes()).hexdigest()==manifest['original_sha256'];event('original-restored-and-hash-verified')
with (database.parent/'.material-worker.lock').open('a+b') as handle:
 lock_file(handle);locked=True;event('worker-lock-held-original-still-readable')
 deadline=time.monotonic()+600
 try:
  while time.monotonic()<deadline:
   if not select.select([sys.stdin],[],[],min(10,max(0,deadline-time.monotonic())))[0]:continue
   command=sys.stdin.readline().strip()
   if not command:break
   if command=='hide':pin.rename(held);event('original-temporarily-unavailable')
   elif command=='release' and locked:unlock_file(handle);locked=False;event('worker-lock-released')
   elif command=='restore':restore()
   elif command=='finish':break
   else:print('Allowed: hide, release, restore, finish',flush=True)
 finally:
  restore()
  if locked:unlock_file(handle)
  event('fault-controller-finished')
