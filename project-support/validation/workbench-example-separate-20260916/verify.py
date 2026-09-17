from pathlib import Path
import json,sys,uuid,hashlib
sys.path.insert(0,'/private/tmp');from example_http import call
out=Path(__file__).parent;p=json.loads((out/'population.json').read_text());mid='3069f79e2481e4c18f1e268c8344de9f'
# Finalize the parent against the post-retirement context; no old-result overwrite.
u=p['units']['R1'];x=call('/api/interpretations?unit_id='+u)
if x['stale']:
 r=call('/api/interpretations/save',dict(request_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'adf10-separate/final-parent/'+u)),unit_id=u,expected_revision=x['revision'],context_fingerprint=x['context']['fingerprint'],linked_material_ids=[],fields=x['fields'],action='save'));(out/'parent-final.json').write_text(json.dumps(r,indent=2))
def nodes(n):
 yield n
 for c in n.get('children',[]):yield from nodes(c)
m=call('/api/material?id='+mid);m=m.get('material',m);rows=call('/api/requirements?material_id='+mid);assert len(rows['sessions'])==4
report=[]
for i,s in enumerate(rows['sessions']):
 d=call('/api/requirements/session?id='+s['id']);u=p['units']['R'+str(i+1)];assert d['text']==m['blocks'][i]['text'];assert len(d['source_segments'])==1 and len(d['units'])==1;tree=d['structure_views'][u]
 for n in nodes(tree):
  if n['kind']=='fragment':assert d['text'][slice(*n['span'])]==n['text']
 if i==0:
  group=next(n for n in tree['children'] if n.get('role')=='subrequirement');assert group['quantity']==3;assert {n['target_id'] for n in group['children']}=={p['units'][k] for k in ('R2','R3','R4')}
 else:assert all(n.get('role') not in ('Subject','Modal Verb','Main Verb') for n in nodes(tree))
 if i in (1,3):
  count=2 if i==1 else 5;assert any(n.get('quantity')==[count,count] for n in nodes(tree))
 x=call('/api/interpretations?unit_id='+u);assert not x['stale'];report.append(dict(entry='R'+str(i+1),id=u,session=d['id'],text=d['text'],revision=d['revision'],interpretation_revision=x['revision']))
assert len(rows['deleted'])==3
(out/'verification.json').write_text(json.dumps(dict(entries=report,old_entries_recoverable=True),indent=2));print('Verified four one-passage Requirements, All 3 links, nested quantities, spans and four current interpretations.')
