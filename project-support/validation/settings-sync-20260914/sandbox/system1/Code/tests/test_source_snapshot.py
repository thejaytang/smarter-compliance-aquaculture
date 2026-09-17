import copy,json,uuid
from pathlib import Path
from unittest.mock import patch
from test_collaboration_review import CollaborationReviewTests
from system1.source_snapshot import apply
import source_updater as u

class SourceSnapshotTests(CollaborationReviewTests):
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
