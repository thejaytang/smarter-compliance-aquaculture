from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import uuid
from local_workbench.collaboration import Collaboration, fingerprint
from local_workbench.source_workflow import SourceWorkflow
from local_workbench.collaboration_collection import Collection
from local_workbench.collaboration_exchange import pack,unpack

A='Weijie Tang';B='Ana Jokic'
class SourceWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.fail=False;self.applied=0
  self.task={'operation_id':'candidate-1','operation_type':'NEW_SOURCE_CANDIDATE','revision':'a'*64,'source_revision':'','source_id':None,'is_open':True}
  def call(cmd,**kwargs):
   if cmd=='read':return {'sources':[],'tasks':[self.task],'history':[]}
   if cmd=='workflow_apply':
    self.applied+=1
    if self.fail:self.fail=False;raise RuntimeError('Ambiguous interrupted response')
    return {'status':'applied','message':'Candidate decision recorded'}
   raise AssertionError(cmd)
  self.app=SimpleNamespace(runtime=Path(self.temp.name),adapter=SimpleNamespace(call=call),snapshot_time=0)
  self.c=Collaboration(self.app);self.service=SourceWorkflow(self.c)
 def tearDown(self):self.temp.cleanup()
 def test_applied_source_review_is_an_action_even_when_task_stays_open(self):
  self.c.put('merge','m',{'source_id':'S1','source_review':{'selection':'PENDING'}})
  self.c.put('adoption_receipt','r',{'request_id':'r','merge_id':'m','actor':A,'at':'2026-09-14','source_receipt':{'effective_selection':'PENDING'},'source_status':'saved_partial'})
  self.c.put('adoption_receipt','material-only',{'request_id':'material-only','merge_id':'m','source_receipt':None})
  rows=self.service.snapshot(A)['history'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['result'],'PENDING');self.assertEqual(rows[0]['action'],'APPLY_SOURCE_REVIEW')
  self.assertEqual(len(self.service.snapshot(A)['tasks']),1)
 def request(self):return {'request_id':str(uuid.uuid4()),'task_id':'candidate-1','revision':'a'*64,'source_revision':'','action':'candidate_reject','note':'Engineering candidate rejected','explicit_confirmation':True}
 def test_explicit_confirmation_before_durable_proposal(self):
  req=self.request();req['explicit_confirmation']=False
  with self.assertRaises(ValueError):self.service.task(A,req,True)
  self.assertEqual(self.c.all('source_task_draft'),[]);self.assertEqual(self.applied,0)
 def test_owner_failure_resumes_original_proposal_and_replay(self):
  req=self.request();self.fail=True
  with self.assertRaises(RuntimeError):self.service.task(A,req,True)
  self.assertEqual(self.c.all('source_task_draft')[0]['revision'],1)
  # A changed live task must not prevent resuming the already bound owner request.
  self.task['revision']='b'*64
  result=self.service.task(A,req,True);self.assertEqual(self.service.task(A,req,True),result)
  self.assertEqual(self.c.all('source_task_draft')[0]['revision'],1);self.assertEqual(self.applied,2)
  req['note']='Different'
  with self.assertRaises(ValueError):self.service.task(A,req,True)
 def test_task_collection_has_known_baseline_and_separate_adoption(self):
  req=self.request();proposal=self.service.task(B,req)['proposal'];base=proposal['base_task'];metadata={'id':str(uuid.uuid4()),'actor':B,'item_type':'source_task_submission','base':base,'base_digest':fingerprint(base),'proposal':proposal}
  self.c.put('task_baseline',fingerprint(base),base)
  raw=pack('submission',metadata,{});identity=str(uuid.uuid4());collection=pack('collection',{'id':identity,'actor':B,'collection_version':2,'direction':'submission','items':[{'id':metadata['id'],'kind':'submission','path':'task.zip'}]},{'task.zip':raw})
  self.c.import_package(A,collection);self.assertEqual(self.applied,0)
  service=Collection(self.c);preview=service.preview(A,{'item_id':metadata['id']});adopt={'item_id':metadata['id'],'expected_current_digest':preview['current_digest'],'request_id':str(uuid.uuid4()),'choice':'incoming','explicit_confirmation':True}
  self.fail=True
  with self.assertRaises(RuntimeError):service.adopt(A,adopt)
  result=service.adopt(A,adopt);self.assertEqual(result['status'],'adopted');self.assertEqual(result['contributor'],B)
  self.assertEqual(service.adopt(A,adopt),result);self.assertEqual(self.c.all('source_task_draft')[1]['revision'],1)
 def test_work_direction_cannot_smuggle_a_return_task(self):
  req=self.request();proposal=self.service.task(B,req)['proposal'];m={'id':str(uuid.uuid4()),'actor':B,'item_type':'source_task_submission','base':proposal['base_task'],'base_digest':fingerprint(proposal['base_task']),'proposal':proposal}
  with self.assertRaisesRegex(ValueError,'direction'):Collection(self.c).validate_item(unpack(pack('work',m,{})))

 def test_changed_inspection_assignment_preserves_original_baseline_and_local_work(self):
  service=Collection(self.c);base={'id':'check-1','revision':0,'note':'Assigned original'}
  assignment={'id':str(uuid.uuid4()),'task':base,'base_digest':fingerprint(base)}
  self.assertEqual(service.receive_inspection_assignment(assignment),'imported_for_review')
  local={**base,'revision':1,'note':'Personal progress'};self.c.put('material_inspection','check-1',local)
  changed={**assignment,'id':str(uuid.uuid4()),'task':{**base,'revision':2,'note':'Changed assignment'}};changed['base_digest']=fingerprint(changed['task'])
  self.assertEqual(service.receive_inspection_assignment(changed),'assignment_changed')
  self.assertEqual(self.c.get('inspection_assigned','check-1'),assignment)
  self.assertEqual(self.c.get('material_inspection','check-1'),local)
  self.assertEqual(self.c.get('inspection_assignment_pending',changed['id'])['base_digest'],changed['base_digest'])
  self.assertEqual(service.receive_inspection_assignment(assignment),'imported_for_review')
  self.assertEqual(self.c.get('material_inspection','check-1'),local)

 def test_last_check_comes_from_persisted_checks_not_source_publication(self):
  original={'source_id':'S1','version':'2020-01-01','last_attempt_at':'2026-09-12T13:00:00'}
  self.app.adapter.call=lambda *a,**k:{'sources':[deepcopy(original)],'tasks':[],'history':[]}
  self.c.put('source_url_check','finished',{'finished_at':'2026-09-13T15:00:00Z','results':[{'source_id':'S1','status':'unchanged','checked_at':'2026-09-13T14:58:00Z'}]})
  self.c.put('source_url_check','skipped',{'finished_at':'2026-09-14T15:00:00Z','results':[{'source_id':'S1','status':'skipped'}]})
  first=self.service.snapshot(A)['sources'][0]
  self.assertEqual(first['last_checked_at'],'2026-09-13T14:58:00+00:00')
  self.assertEqual(first['version'],original['version']);self.assertEqual(self.service.snapshot(A)['sources'][0]['last_checked_at'],first['last_checked_at'])
  self.c.put('source_url_check','new',{'results':[{'source_id':'S1','status':'changed','checked_at':'2026-09-14T12:30:00Z'}]})
  self.assertEqual(self.service.snapshot(A)['sources'][0]['last_checked_at'],'2026-09-14T12:30:00+00:00')

 def test_last_check_compares_actual_times_and_preserves_system_timezone(self):
  from local_workbench.source_workflow import latest_check_time
  self.assertEqual(latest_check_time(['2026-09-14T00:15:00+02:00','2026-09-13T23:15:00Z'],'Europe/Oslo'),'2026-09-14T01:15:00+02:00')
  self.assertEqual(latest_check_time([None,'invalid']), '')
