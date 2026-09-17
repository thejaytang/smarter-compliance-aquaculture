"""Source-specific explicit actions and task isolation, synthetic authority only."""
import uuid
from unittest.mock import patch
from test_collaboration_review import CollaborationReviewTests
from system1 import workbench_bridge as bridge
from system1.source_workflow import preview,reopen
import source_updater as u
import human_operations as h

class SourceWorkflowTests(CollaborationReviewTests):
 def test_missing_original_scores_remain_pending(self):
  cfg=u.read_config(self.config_path);wb=u.open_registry(cfg);ws=wb[cfg['sheet_name']];sh=u.workbook_headers(ws,2)
  ws.cell(3,sh['download_status'],'MISSING_FILE');ws.cell(3,sh['snapshot_status'],'MISSING')
  u.save_registry(wb,cfg,u.registry_revision(cfg));wb.close()
  request=self.request(note='Source reviewed; authorised file still needed.')
  p=preview(self.config_path,{'source_id':'PA001','expected_source_revision':request['expected_source_revision'],'source_review':request['review']})
  self.assertEqual(p['effective_selection'],'PENDING')
  result=self.apply(request);self.assertEqual(result['effective_selection'],'PENDING');self.assertEqual(result['status'],'saved_partial')
 def test_rereview_is_new_task_and_only_selected_task_closes(self):
  self.activate();before=bridge.read(self.config_path)['history'];ids=[]
  for note in ('Check source identity','Check current applicability'):
   source=self.source();req={'actor':'Weijie Tang','source_id':'PA001','expected_source_revision':source['source_revision'],'request_id':str(uuid.uuid4()),'note':note}
   a=reopen(self.config_path,req);self.assertEqual(reopen(self.config_path,req),a);ids.append(a['operation_id'])
  tasks=bridge.read(self.config_path)['tasks'];selected=next(t for t in tasks if t['operation_id']==ids[0])
  req=self.request(note='The selected source check was completed.',task_checks={selected['operation_id']:selected['revision']})
  self.assertEqual(self.apply(req)['status'],'applied')
  after=bridge.read(self.config_path);self.assertIn(ids[1],{t['operation_id'] for t in after['tasks']});self.assertNotIn(ids[0],{t['operation_id'] for t in after['tasks']})
  for old in before:self.assertIn(old,after['history'])
 def test_scoped_decision_does_not_execute_another_staged_task(self):
  self.activate();cfg=u.read_config(self.config_path);wb=u.open_registry(cfg);ops=wb[h.HUMAN_SHEET];oh=h.operation_headers(ops)
  for identity in ('SELECTED','UNRELATED'):
   h.append_operation(ops,oh,{'operation_id':identity,'operation_type':'NEW_SOURCE_CANDIDATE','decision':'REJECT','operator':'Weijie Tang','operator_note':'Synthetic rejection','program_status':'PENDING','payload_json':'{}'})
  u.save_registry(wb,cfg,u.registry_revision(cfg));wb.close()
  with patch('source_updater.run_updates',side_effect=AssertionError('Unexpected retrieval')):h.process_decisions(self.config_path,operation_ids={'SELECTED'})
  data=bridge.read(self.config_path);self.assertIn('UNRELATED',{t['operation_id'] for t in data['tasks']});self.assertIn('SELECTED',{t['operation_id'] for t in data['history']})

 def test_reported_problem_is_pending_and_replay_does_not_duplicate(self):
  self.activate();issue={'id':str(uuid.uuid4()),'note':'Synthetic applicability concern with specific source evidence.'}
  request=self.request(note='New problem for follow-up.',new_issues=[issue]);receipt=self.apply(request)
  self.assertEqual(receipt['status'],'saved_partial');self.assertEqual(self.apply(request),receipt)
  tasks=[t for t in bridge.read(self.config_path)['tasks'] if t['operation_id']=='REPORTED-'+issue['id']]
  self.assertEqual(len(tasks),1);self.assertEqual(tasks[0]['human_issue']['reported_by'],'Ana Jokic')
 def test_original_fingerprint_mismatch_cannot_be_included(self):
  self.activate();(self.authority/self.current_name).write_bytes(b'Changed engineering original')
  result=self.apply(self.request(note='Hash mismatch must stay pending.'))
  self.assertEqual(result['effective_selection'],'PENDING');self.assertEqual(result['status'],'saved_partial')

 def test_physically_missing_original_can_be_reviewed_without_false_include(self):
  self.activate();(self.authority/self.current_name).unlink()
  self.assertEqual(self.source()['effective_selection'],'PENDING')
  result=self.apply(self.request(note='Original unavailable; source review retained.'))
  self.assertEqual(result['effective_selection'],'PENDING')

 def test_intake_pending_replay_and_changed_identity(self):
  from system1.source_workflow import intake
  self.activate();before=bridge.read(self.config_path)['sources']
  req={'actor':'Weijie Tang','request_id':str(uuid.uuid4()),'source_title':'Synthetic new source','official_url':'https://example.org/new','issuer':'Synthetic'}
  result=intake(self.config_path,req)
  self.assertEqual(result['status'],'pending_review');self.assertEqual(intake(self.config_path,req),result)
  with self.assertRaisesRegex(ValueError,'identity conflict'):intake(self.config_path,{**req,'source_title':'Changed'})
  data=bridge.read(self.config_path);self.assertEqual(data['sources'],before)
  task=next(t for t in data['tasks'] if t['operation_id']==result['operation_id'])
  self.assertEqual(task['operation_type'],'NEW_SOURCE_CANDIDATE');self.assertEqual(task['decision'],'PENDING')
 def test_intake_duplicates_link_to_source_and_invalid_role_url_rejected(self):
  from system1.source_workflow import intake
  self.activate();source=self.source()
  req={'actor':'Weijie Tang','request_id':str(uuid.uuid4()),'source_title':'Synthetic new version','official_url':source['official_url'],'version':'2099'}
  result=intake(self.config_path,req);self.assertEqual(result['duplicate_source_id'],'PA001');self.assertEqual(result['version_of_source_id'],'PA001')
  for change in ({'actor':'Ana Jokic'},{'official_url':'file:///private/file'},{'source_title':'=FORMULA()'}):
   with self.assertRaises(ValueError):intake(self.config_path,{**req,**change,'request_id':str(uuid.uuid4())})
 def test_intake_upload_is_retained_without_replacing_original(self):
  from system1.source_workflow import intake
  import hashlib
  self.activate();source=self.source();original=(self.authority/self.current_name).read_bytes()
  root=self.runtime/'uploads';root.mkdir();file=root/'candidate.pdf';file.write_bytes(b'%PDF-1.4 synthetic retained candidate')
  req={'actor':'Weijie Tang','request_id':str(uuid.uuid4()),'source_title':'Synthetic replacement','official_url':source['official_url'],'upload_path':str(file),'upload_root':str(root),'upload_hash':hashlib.sha256(file.read_bytes()).hexdigest()}
  result=intake(self.config_path,req);task=next(t for t in bridge.read(self.config_path)['tasks'] if t['operation_id']==result['operation_id'])
  self.assertEqual(task['operation_type'],'MANUAL_FILE_REPLACEMENT');self.assertEqual((self.authority/self.current_name).read_bytes(),original)
  cfg=u.read_config(self.config_path);self.assertTrue((cfg['manual_intake_root']/task['intake_file']).is_file())
  with self.assertRaisesRegex(ValueError,'changed or is outside'):intake(self.config_path,{**req,'request_id':str(uuid.uuid4()),'upload_hash':'0'*64})
 def test_intake_duplicate_pending_and_original_binding(self):
  from system1.source_workflow import intake,intake_original
  import hashlib
  self.activate();root=self.runtime/'uploads';root.mkdir();file=root/'new.pdf';file.write_bytes(b'%PDF-1.4 synthetic file')
  req={'actor':'Weijie Tang','request_id':str(uuid.uuid4()),'source_title':'Synthetic original','upload_path':str(file),'upload_root':str(root),'upload_hash':hashlib.sha256(file.read_bytes()).hexdigest()}
  first=intake(self.config_path,req);second=intake(self.config_path,{**req,'request_id':str(uuid.uuid4())})
  self.assertTrue(second['existing_candidate']);self.assertEqual(first['operation_id'],second['operation_id'])
  result=intake_original(self.config_path,first['operation_id']);self.assertEqual(result['hash'],req['upload_hash'])
  from pathlib import Path
  Path(result['path']).write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'unavailable or changed'):intake_original(self.config_path,first['operation_id'])
  with self.assertRaisesRegex(ValueError,'Unknown intake'):intake_original(self.config_path,'../../file')
