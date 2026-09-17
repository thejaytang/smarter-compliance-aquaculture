"""Isolated peer round trips, stale previews and interruption recovery."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest,uuid
from local_workbench.collaboration import Collaboration
from local_workbench.full_snapshot import FullSnapshot
from local_workbench.snapshot_graph import node

A='Weijie Tang';B='Ana Jokic'
class Workspace:
 def __init__(self,c,value):self.c=c;self.value=value;self.base={'text':'base'};self.writes=0;self.fail=False
 def capture(self,actor):return [{'key':'review:TS001','value':self.value,'base':self.base,'branch':actor,'actor':actor}]
 def validate(self,m,files):pass
 def validate_value(self,key,value):pass
 def apply(self,actor,key,value,context):
  prior=self.c.get('fixture_receipt',context['request_id'])
  if prior:return prior
  self.writes+=1;self.value=value
  receipt={'status':'saved'};self.c.put('fixture_receipt',context['request_id'],receipt)
  if self.fail:self.fail=False;raise RuntimeError('crash after domain commit')
  return receipt
 def mark_observed(self,key,head,actor):self.c.put('sync_observed',key+':'+actor,{'head':head})
class FullSnapshotTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name);self.peers=[]
  for i in range(2):
   p=self.root/str(i);p.mkdir();c=Collaboration(SimpleNamespace(runtime=p,snapshot_time=1));w=Workspace(c,{'text':'base'});self.peers.append((FullSnapshot(c,w),w))
 def tearDown(self):self.tmp.cleanup()
 def export(self,index,actor):
  s,_=self.peers[index];r=s.export(actor,{'request_id':str(uuid.uuid4())});return s.download(actor,r['id'])[0]
 def test_full_round_trip_history_repeat_and_no_consumption(self):
  a,wa=self.peers[0];b,wb=self.peers[1];wa.value={'text':'A'}
  raw=self.export(0,A);p=b.receive(B,raw);self.assertFalse(p['conflicts']);b.apply(B,{'id':p['id'],'explicit_confirmation':True})
  self.assertEqual(wb.value,{'text':'A'});self.assertEqual(wb.writes,1)
  b.receive(B,raw);b.apply(B,{'id':p['id'],'explicit_confirmation':True});self.assertEqual(wb.writes,1)
  wb.value={'text':'B'};p=a.receive(A,self.export(1,B));a.apply(A,{'id':p['id'],'explicit_confirmation':True})
  self.assertEqual(wa.value,{'text':'B'});self.assertEqual(len(a.history()),2)
  self.assertEqual(len(a.load(self.export(0,A))['metadata']['history']),2)
 def test_changed_local_after_preview_blocks_apply(self):
  a,wa=self.peers[0];b,wb=self.peers[1];wa.value={'text':'A'}
  p=b.receive(B,self.export(0,A));wb.value={'text':'local later'}
  with self.assertRaisesRegex(ValueError,'changed after'):b.apply(B,{'id':p['id'],'explicit_confirmation':True})
  self.assertEqual(wb.writes,0)
 def test_concurrent_change_needs_resolution(self):
  a,wa=self.peers[0];b,wb=self.peers[1];wa.value={'text':'A'};wb.value={'text':'B'}
  p=b.receive(B,self.export(0,A));self.assertEqual(len(p['conflicts']),1)
  with self.assertRaisesRegex(ValueError,'conflict'):b.apply(B,{'id':p['id'],'explicit_confirmation':True})
  d=p['conflicts'][0];choices={d['pair']:{d['id']:{'action':'incoming'}}}
  p=b.prepare(B,{'id':p['id'],'decisions':choices});self.assertFalse(p['conflicts'])
  b.apply(B,{'id':p['id'],'explicit_confirmation':True});self.assertEqual(wb.value,{'text':'A'})
 def test_crash_after_commit_resumes_without_duplicate_write(self):
  a,wa=self.peers[0];b,wb=self.peers[1];wa.value={'text':'new'};wb.fail=True
  raw=self.export(0,A);p=b.receive(B,raw)
  with self.assertRaises(RuntimeError):b.apply(B,{'id':p['id'],'explicit_confirmation':True})
  self.assertEqual(b.receive(B,raw)['status'],'applying')
  b.apply(B,{'id':p['id'],'explicit_confirmation':True});self.assertEqual(wb.writes,1);self.assertEqual(len(b.history()),1)
 def test_permanent_domain_conflict_can_be_recompared(self):
  a,wa=self.peers[0];b,wb=self.peers[1];wa.value={'text':'incoming'}
  raw=self.export(0,A);p=b.receive(B,raw);original=wb.apply
  def stale(*args):raise ValueError('owning revision changed')
  wb.apply=stale
  with self.assertRaisesRegex(ValueError,'Refresh the comparison'):b.apply(B,{'id':p['id'],'explicit_confirmation':True})
  self.assertEqual(b.c.get('sync_plan',B+':'+p['id'])['status'],'needs_recomparison')
  wb.apply=original;updated=b.prepare(B,{'id':p['id']})
  self.assertNotEqual(updated['request_id'],p['request_id'])
  b.apply(B,{'id':p['id'],'explicit_confirmation':True});self.assertEqual(wb.value,{'text':'incoming'})
 def test_export_request_replay_is_identical(self):
  a,w=self.peers[0];req={'request_id':str(uuid.uuid4())};first=a.export(A,req);w.value={'text':'changed'}
  self.assertEqual(a.export(A,req),first)
if __name__=='__main__':unittest.main()
