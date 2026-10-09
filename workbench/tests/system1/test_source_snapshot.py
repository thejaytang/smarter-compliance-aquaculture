import copy,json,uuid
from pathlib import Path
from unittest.mock import patch
from test_collaboration_review import CollaborationReviewTests
from system1.source_snapshot import apply
import source_updater as u

class SourceSnapshotTests(CollaborationReviewTests):
 def test_long_original_name_import_preserves_bytes_and_replays(self):
  from backend.shared.filesystem import temporary_directory
  self.activate();source=self.source();cfg=u.read_config(self.config_path)
  original=cfg['source_root']/source['folder_code']/source['stored_filename']
  raw=original.read_bytes()
  with temporary_directory(prefix='snapshot-long-') as staging:
   target=staging/('x'*90)/('y'*90)
   config=json.loads(self.config_path.read_text());config['source_root']=str(target)
   self.config_path.write_text(json.dumps(config))
   incoming=copy.deepcopy(source);incoming['stored_filename']='PA001-001_'+('long_original_'*14)+'.html'
   destination=target/incoming['folder_code']/incoming['stored_filename']
   self.assertGreater(len(str(destination)),260)
   request={'request_id':str(uuid.uuid4()),'actor':'Ana Jokic','source':incoming,
    'expected_source_revision':source['source_revision'],'original_path':str(original),
    'original_root':str(cfg['source_root']),'evidence':{}}
   result=apply(self.config_path,request)
   self.assertEqual(apply(self.config_path,request),result)
   self.assertEqual(destination.read_bytes(),raw)
   self.assertEqual(original.read_bytes(),raw)
   self.assertEqual(list(destination.parent.iterdir()),[destination])
   self.assertNotIn('\\\\?\\',self.source()['stored_filename'])
   self.assertEqual(self.source()['effective_selection'],'INCLUDE')
   from system1.workbench_bridge import artifact
   self.assertEqual(artifact(self.config_path,source['source_id'])['path'],str(destination))

 def test_large_snapshot_evidence_roundtrips_without_excel_truncation(self):
  store=self.activate();source=self.source();cfg=u.read_config(self.config_path)
  original=cfg['source_root']/source['folder_code']/source['stored_filename']
  evidence={'history':[{'note':'retained original history '*2500}]}
  request={'request_id':str(uuid.uuid4()),'actor':'Ana Jokic','source':source,
   'expected_source_revision':source['source_revision'],'original_path':str(original),
   'original_root':str(cfg['source_root']),'evidence':evidence}
  first=apply(self.config_path,request)
  self.assertEqual(apply(self.config_path,request),first)
  operation=store.snapshot()['operations'][-1]['record']
  self.assertEqual(json.loads(operation['payload_json'])['source_evidence'],evidence)
  self.assertEqual(self.source()['source_id'],source['source_id'])
  wb=u.open_registry(cfg)
  u.save_registry(wb,cfg,u.registry_revision(cfg));wb.close()
  self.assertEqual(store.snapshot()['operations'][-1]['record']['payload_json'],operation['payload_json'])

 def test_peer_snapshot_preserves_original_history_and_replays(self):
  store=self.activate();source=self.source();cfg=u.read_config(self.config_path)
  original=cfg['source_root']/source['folder_code']/source['stored_filename'];raw=original.read_bytes()
  incoming=copy.deepcopy(source);incoming['issuer']='Synchronized issuer'
  req={'request_id':str(uuid.uuid4()),'actor':'Ana Jokic','source':incoming,
   'expected_source_revision':source['source_revision'],'original_path':str(original),'original_root':str(cfg['source_root']),
   'evidence':{'history':[{'actor':'Daniel Restad','note':'Retained peer history'}]}}
  before=store.snapshot()
  with patch('source_updater.run_updates',side_effect=AssertionError('No retrieval during sync')):
   first=apply(self.config_path,req);self.assertEqual(apply(self.config_path,req),first)
  self.assertEqual(self.source()['issuer'],'Synchronized issuer');self.assertEqual(original.read_bytes(),raw)
  after=store.snapshot();self.assertEqual(len(after['operations']),len(before['operations'])+1)
  self.assertEqual(after['operations'][-1]['record']['operator'],'Ana Jokic')
 def test_stale_source_snapshot_rejected_without_overwrite(self):
  self.activate();source=self.source();req={'request_id':str(uuid.uuid4()),'actor':'Ana Jokic','source':source,'expected_source_revision':'stale'}
  with self.assertRaisesRegex(ValueError,'changed after'):apply(self.config_path,req)
  self.assertEqual(self.source(),source)
