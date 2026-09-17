"""Update the existing English demonstration through the guarded application API."""
from pathlib import Path
import json,sys,uuid
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path.insert(0,'/private/tmp');from example_http import call
before=json.loads((OUT/'example-before.json').read_text());receipt=OUT/'example-update.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
def identity(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'workbench-group-relationship-20260917/'+label))
def record(key,value):saved[key]=value;receipt.write_text(json.dumps(saved,ensure_ascii=False,indent=2));return value
def once(key,path,body):
 if key not in saved:record(key,call(path,body))
 return saved[key]
def step(action,label,**kw):return dict(action=action,request_id=identity(label),**kw)
r2=before['R2'];uid=next(iter(r2['units']));root=uid+'/structure';wording=r2['text']
if 'R2' not in saved:
 live=call('/api/requirements/session?id='+r2['id']);assert live['revision']==r2['revision']==2
 group_request=identity('R2/group');owner=str(uuid.uuid5(uuid.UUID(group_request),'clause'));at=wording.index('including')
 steps=[step('phase','R2/reopen',phase='fields'),dict(action='structure',request_id=group_request,unit_id=uid,node_id=root,operation='add-group',start=0,end=len(wording)),step('structure','R2/relationship',unit_id=uid,node_id=owner,operation='relationship',start=at,end=at+len('including')),step('done','R2/done',unit_id=uid),step('phase','R2/complete',phase='complete')]
 req=dict(action='save-draft',request_id=identity('R2/save'),session_id=r2['id'],expected_revision=r2['revision'],steps=steps)
 preview=once('R2-preview','/api/requirements/step',dict(req,action='preview',request_id=identity('R2/preview')))['document'];assert preview['text']==wording
 once('R2','/api/requirements/step',req);print('R2 relationship saved',flush=True)
# Keep the explicit parent link current; unchanged references and their counts retain identity.
r1=before['R1'];u1=next(iter(r1['units']));root1=u1+'/structure'
if 'R1' not in saved:
 live=call('/api/requirements/session?id='+r1['id']);assert live['revision']==r1['revision']==4
 group=next(n for n in live['structure_views'][u1]['children'] if n.get('role')=='subrequirement')
 target=next(n for n in group['children'] if n.get('target_id')==uid)
 steps=[step('phase','R1/reopen',phase='fields'),step('structure','R1/remove-reference',unit_id=u1,node_id=target['id'],operation='remove'),step('structure','R1/relink',unit_id=u1,node_id=root1,operation='link',field='subrequirement',target_id=uid),step('structure','R1/quantity',unit_id=u1,node_id=group['id'],operation='quantity',quantity=3),step('done','R1/done',unit_id=u1),step('phase','R1/complete',phase='complete')]
 # Preserve displayed reference order by operation-independent source ordering in the UI.
 req=dict(action='save-draft',request_id=identity('R1/save'),session_id=r1['id'],expected_revision=r1['revision'],steps=steps)
 once('R1-preview','/api/requirements/step',dict(req,action='preview',request_id=identity('R1/preview')))
 once('R1','/api/requirements/step',req);print('R1 reference refreshed',flush=True)
# Refresh only the saved context binding; retain all six existing editable values verbatim.
for key in ['R1','R2']:
 if key+'-interpretation' in saved:continue
 ident=next(iter(before[key]['units']));old=call('/api/interpretations?unit_id='+ident)
 once(key+'-interpretation','/api/interpretations/save',dict(request_id=identity(key+'/interpretation'),unit_id=ident,expected_revision=old['revision'],context_fingerprint=old['context']['fingerprint'],linked_material_ids=[],fields=old['fields'],action='save'))
after={key:call('/api/requirements/session?id='+d['id']) for key,d in before.items()}
assert all(after[k]['text']==d['text'] and set(after[k]['units'])==set(d['units']) for k,d in before.items())
assert after['R3']==before['R3'] and after['R4']==before['R4']
record('after',after)
print(json.dumps({k:d['revision'] for k,d in after.items()}))
