"""Real isolated archive/inspection roundtrip with the existing deterministic parser."""
from copy import deepcopy
import json
from pathlib import Path
import uuid
from check_offline_collaboration import app, save, take, uid, ROOT, FIX, ACTOR, A
from local_workbench.collaboration import Collaboration
from local_workbench.material_queue import MaterialQueue

report=ROOT/'project-support/reports/offline-collaboration-20260912'
name='archive-inspection-'+uid()[:8]
a=app(name);c=a.collaboration;q=MaterialQueue(c)
m=c.material_action(ACTOR,'open',{'source_id':'TS001','request_id':uid()});mid=m['id']
c.material_action(ACTOR,'extract',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid()});c.tick()
m=c.read_material(ACTOR,mid);candidate=next(x for x in m['candidates'] if x['status'] in ('ready','partial'))
c.material_action(ACTOR,'adopt',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid(),'candidate_id':candidate['id'],'action':'adopt','reviewed_against_source':True})
assert q.listing(ACTOR,'archive')['total']==0
# Personal confirmation is not an accepted master archive.
m=c.read_material(ACTOR,mid)
c.material_action(ACTOR,'confirm',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid(),'explicit_confirmation':True,'checked_scope':[s['id'] for s in m['scope']],'association_reviewed':True})
assert q.listing(ACTOR,'archive')['total']==0
take(c,c.prepare_own(ACTOR,{'source_id':'TS001','material_id':mid}))
m=c.read_material(ACTOR,mid,view='master')
r=c.confirm_master(ACTOR,{'material_id':mid,'expected_revision':m['revision'],'request_id':uid(),'explicit_confirmation':True,'checked_scope':[s['id'] for s in m['scope']],'association_reviewed':True,'omissions_checked':True,'dependencies_checked':True})
archive=q.read_archive(ACTOR,mid);old=deepcopy(archive['blocks']);ar=archive['revision'];scope=[archive['scope'][0]['id']]
assert q.listing(ACTOR,'archive')['total']==1
assert q.listing(ACTOR,'pending')['total']==0
req={'material_id':mid,'archive_revision':ar,'request_id':uid(),'scope':scope,'assignee':ACTOR,'reason':'Isolated regression check of an accepted archive.'}
t=q.create(ACTOR,req)['inspection'];assert q.create(ACTOR,req)['inspection']['id']==t['id']
assert q.listing(ACTOR,'pending')['materials'][0]['queue']['inspection_only']
r=q.save(ACTOR,{'task_id':t['id'],'material_id':mid,'expected_revision':0,'request_id':uid(),'action':'save','note':'Partial isolated check saved.','checked_scope':[]})
q=MaterialQueue(Collaboration(a));t=q.detail(ACTOR,t['id'])['inspection'];assert t['revision']==1
passed=q.save(ACTOR,{'task_id':t['id'],'material_id':mid,'expected_revision':1,'request_id':uid(),'action':'pass','note':'Synthetic selected range matches preserved source.','checked_scope':scope,'explicit_confirmation':True})
assert q.listing(ACTOR,'pending')['total']==0
req['request_id']=uid();t=q.create(ACTOR,req)['inspection'];t=q.save(ACTOR,{'task_id':t['id'],'material_id':mid,'expected_revision':0,'request_id':uid(),'action':'finding','note':'Engineering-only revision exercise.','checked_scope':scope})['inspection']
try:c.confirm_master(ACTOR,{'material_id':mid});raise AssertionError('Open finding allowed confirmation')
except ValueError as e:assert 'inspection finding' in str(e)
m=c.read_material(ACTOR,mid);save(c,ACTOR,m,'ENGINEERING ARCHIVE REVISION')
take(c,c.prepare_own(ACTOR,{'source_id':'TS001','material_id':mid}))
assert q.read_archive(ACTOR,mid)['blocks']==old
current=c.read_material(ACTOR,mid,view='master')
resolved=q.save(ACTOR,{'task_id':t['id'],'material_id':mid,'expected_revision':t['revision'],'request_id':uid(),'action':'resolve','note':'Engineering revision rechecked across complete synthetic original.','checked_scope':[s['id'] for s in current['scope']],'expected_master_revision':current['revision'],'explicit_confirmation':True})
c.confirm_master(ACTOR,{'material_id':mid,'expected_revision':current['revision'],'request_id':uid(),'explicit_confirmation':True,'checked_scope':[s['id'] for s in current['scope']],'association_reviewed':True,'omissions_checked':True,'dependencies_checked':True})
assert q.read_archive(ACTOR,mid)['revision']>ar
assert q.read_archive(ACTOR,mid,ar)['blocks']==old
assert q.listing(ACTOR,'pending')['total']==0
# Retain one real task for browser-only inspection without new business decisions.
archive=q.read_archive(ACTOR,mid);req.update(request_id=uid(),archive_revision=archive['revision']);browser_task=q.create(ACTOR,req)['inspection']
result={'status':'PASS','root':str(a.root),'material_id':mid,'archived_revision':ar,'new_archive_revision':archive['revision'],'browser_task_id':browser_task['id'],'checks':['personal confirmation excluded from master archive','exact main acceptance archived','spot-check returns to Pending without removing archive','partial progress survives collaboration restart','passed check leaves Pending','finding blocks main acceptance','revision adoption retains preceding archive','explicit full-scope resolution and new archive','old accepted body retained in history'],'scope':'Synthetic isolated macOS data; no normal material decisions or Windows claim'}
(report/'archive-inspection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
