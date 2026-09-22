from pathlib import Path
from copy import deepcopy
import zipfile,hashlib,json,uuid
from backend.shared.collaboration_exchange import unpack,pack
from local_workbench.snapshot_graph import validate_graph
root=Path.cwd();out=Path('/private/tmp/example-work-publication')
full=root/'workbench/workspace/packages/collaboration/ca55cfb6-f7b2-4524-8620-419ce18315c3.zip'
with zipfile.ZipFile(full) as z:p=unpack(z.read('logical-workspace.zip'))
m=p['metadata'];mid='f5e03bbd741dc49d6cf1e7541fe58593'
keys={'source:PE001','review:PE001','material:'+mid,'requirements:shared'}
scoped={**deepcopy(m),'id':str(uuid.uuid4()),'nodes':{k:v for k,v in m['nodes'].items() if v['key'] in keys},'heads':{k:v for k,v in m['heads'].items() if k in keys},'history':[]}
scoped['evidence']={k:v for k,v in m['evidence'].items() if k in scoped['nodes']}
validate_graph(scoped['nodes'],scoped['heads'])
assert set(scoped['heads'])==keys
req=scoped['nodes'][scoped['heads']['requirements:shared'][0]]['value']
assert all(s['document']['material_id']==mid for s in req['sessions'])
assert len(req['sessions'])==3 and len(req['interpretations'])==0
assert all(not s['document'].get('deleted') for s in req['sessions'])
digests=set()
for n in scoped['nodes'].values():
 v=n['value']
 if n['key']=='source:PE001':digests.add(v['content_hash'])
 if n['key'].startswith('material:'):digests.add(v['binding']['source']['content_hash'])
files={k:p['files'][k] for k in ['originals/'+h for h in sorted(digests)]}
assert len(files)==2
for name,raw in files.items():assert name=='originals/'+hashlib.sha256(raw).hexdigest()
blob=pack('collection',scoped,files)
(out/'example-work-20260918.zip').write_bytes(blob)
summary={'package_id':scoped['id'],'captured_at':scoped['at'],'source_id':'PE001','material_id':mid,'material_revision':12,'blocks':27,'requirements':[{'id':s['document']['id'],'revision':s['document']['revision'],'phase':s['document']['phase'],'history_versions':len(s['steps'])} for s in req['sessions']],'saved_interpretations':len(req['interpretations']),'originals':len(files),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'keys':sorted(keys)}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
