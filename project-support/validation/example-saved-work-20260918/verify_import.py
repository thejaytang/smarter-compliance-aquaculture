from pathlib import Path
import json,shutil,uuid,hashlib
from local_workbench.application import Application
from local_workbench.full_snapshot import FullSnapshot
from backend.system3.requirements import Requirements
from backend.system3.requirement_delivery import Delivery
from backend.shared.collaboration_exchange import unpack
from backend.shared.workspace import Workspace
from workbench.deployment.restore_initial_data import restore
root=Path.cwd(); stage=Path('/private/tmp/example-work-publication/receiver')
for name in ('config.example.json','schedule.example.json'):
 dst=stage/'workbench/config/system1'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'workbench/config/system1'/name,dst)
seed=root/'workbench/initial-data/workspace-20260917.zip'
if not (stage/'workbench/runtime/state/layout.json').exists():restore(stage,seed,hashlib.sha256(seed.read_bytes()).hexdigest())
# The bundled seed carries an archived template under this relative directory.
(stage/'workbench/runtime/backups/system1/sources').mkdir(parents=True,exist_ok=True)
raw=Path('/private/tmp/example-work-publication/example-work-20260918.zip').read_bytes()
app=Application(stage/'workbench',code_root=root,start_workers=False)
actor='Ana Jokic';mid='f5e03bbd741dc49d6cf1e7541fe58593'
try:
 sync=FullSnapshot(app.collaboration);package=sync.load(raw)
 p=sync.receive(actor,raw)
 if p['conflicts']:
  decisions={}
  for d in p['conflicts']:decisions.setdefault(d['pair'],{})[d['id']]={'action':'incoming'}
  p=sync.prepare(actor,{'id':p['id'],'decisions':decisions})
 assert not p['conflicts'] and not p['validation_errors'],p
 result=sync.apply(actor,{'id':p['id'],'explicit_confirmation':True})
 assert result['status']=='applied',result
 m=app.collaboration.read_material(actor,mid)
 assert len(m['blocks'])==27
 current=Requirements(app.collaboration).listing(actor,mid)['sessions']
 imported={s['id']:s for s in current}
 meta=package['metadata'];req=meta['nodes'][meta['heads']['requirements:shared'][0]]['value']
 for s in req['sessions']:
  d=s['document'];r=Requirements(app.collaboration).read(actor,d['id'])
  for k in ('units','roots','structures','source_segments','text','source'):
   assert r.get(k)==d.get(k),(d['id'],k)
 assert set(imported)=={s['document']['id'] for s in req['sessions']}
 assert len(app.collaboration.source_records())==88
 again=sync.apply(actor,{'id':p['id'],'explicit_confirmation':True});assert again['status']=='applied'
 report={'status':'passed','import_actor':actor,'blocks':len(m['blocks']),'requirement_ids':sorted(imported),'source_count':88,'interpretations':0,'repeat_apply':'passed','preserved_fields':['units','roots','structures','source_segments','text','source']}
finally:app.close()
app=Application(stage/'workbench',code_root=root,start_workers=False)
try:
 assert len(Requirements(app.collaboration).listing(actor,mid)['sessions'])==3
 assert len(app.collaboration.read_material(actor,mid)['blocks'])==27
 report['restart_readback']='passed'
finally:app.close()
Path('/private/tmp/example-work-publication/verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
