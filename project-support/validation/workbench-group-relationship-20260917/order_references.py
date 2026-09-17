from pathlib import Path
import sys,json,uuid
sys.path.insert(0,'/private/tmp');from example_http import call
out=Path(__file__).parent;p=out/'example-update.json';saved=json.loads(p.read_text());doc=saved['after']['R1'];uid=next(iter(doc['units']));root=uid+'/structure'
def rid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'workbench-relationship-reference-order/'+label))
if 'reference-order' not in saved:
 live=call('/api/requirements/session?id='+doc['id']);assert live['revision']==doc['revision']==5
 group=next(n for n in live['structure_views'][uid]['children'] if n.get('role')=='subrequirement')
 targets=[next(iter(saved['after'][k]['units'])) for k in ['R3','R4']]
 steps=[dict(action='phase',request_id=rid('reopen'),phase='fields')]
 for target in targets:
  node=next(n for n in group['children'] if n['target_id']==target)
  steps.append(dict(action='structure',request_id=rid('remove/'+target),unit_id=uid,node_id=node['id'],operation='remove'))
 for target in targets:steps.append(dict(action='structure',request_id=rid('link/'+target),unit_id=uid,node_id=root,operation='link',field='subrequirement',target_id=target))
 steps.extend([dict(action='structure',request_id=rid('quantity'),unit_id=uid,node_id=group['id'],operation='quantity',quantity=3),dict(action='done',request_id=rid('done'),unit_id=uid),dict(action='phase',request_id=rid('complete'),phase='complete')])
 req=dict(action='save-draft',request_id=rid('save'),session_id=doc['id'],expected_revision=doc['revision'],steps=steps)
 call('/api/requirements/step',dict(req,action='preview',request_id=rid('preview')))
 saved['reference-order']=call('/api/requirements/step',req);p.write_text(json.dumps(saved,indent=2))
if 'R1-final-interpretation' not in saved:
 old=call('/api/interpretations?unit_id='+uid)
 saved['R1-final-interpretation']=call('/api/interpretations/save',dict(request_id=rid('interpretation'),unit_id=uid,expected_revision=old['revision'],context_fingerprint=old['context']['fingerprint'],linked_material_ids=[],fields=old['fields'],action='save'));p.write_text(json.dumps(saved,indent=2))
saved['after']['R1']=call('/api/requirements/session?id='+doc['id']);p.write_text(json.dumps(saved,indent=2))
print('R1 source-order links restored; All 3 retained.')
