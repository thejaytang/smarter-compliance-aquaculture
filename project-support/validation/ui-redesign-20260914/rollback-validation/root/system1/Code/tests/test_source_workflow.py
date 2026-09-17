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
