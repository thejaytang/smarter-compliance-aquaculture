"""Real snapshot journal + Requirement domain, with synthetic saved source text."""
import unittest,uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from copy import deepcopy
from local_workbench.collaboration import Collaboration
from local_workbench.full_snapshot import FullSnapshot
from local_workbench.snapshot_workspace import SnapshotWorkspace
from local_workbench.requirement_delivery import Delivery
from local_workbench.requirements import Requirements
from local_workbench.interpretations import Interpretations,KEYS

A='Weijie Tang';B='Ana Jokic'
class RequirementWorkspace(SnapshotWorkspace):
 def capture(self,actor):return Delivery(self.c).capture()

class SharedSnapshotTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name);self.peers=[]
  self.material=dict(id='a'*32,revision=1,source={'source_id':'fixture','content_hash':'v1'},blocks=[dict(id='b',type='text',text='Staff must check equipment.',source_refs=[{'page':1}])])
  for i in range(2):
   p=self.root/str(i);p.mkdir();app=SimpleNamespace(runtime=p,peer_sync=True,snapshot_time=0);c=Collaboration(app);app.collaboration=c
   c.read_material=lambda a,i:deepcopy(self.material)
   c.source=lambda sid:dict(source_id=sid,content_hash='v1')
   c.personal_adapter=lambda a,i:SimpleNamespace(call=lambda *a,**kw:dict(document_information={}))
   self.peers.append((c,FullSnapshot(c,RequirementWorkspace(c))))
 def tearDown(self):self.tmp.cleanup()
 def export(self,index,actor):
  s=self.peers[index][1];r=s.export(actor,{'request_id':str(uuid.uuid4())});return s.download(actor,r['id'])[0]
 def test_two_named_peers_return_shared_edits_and_resolve_conflicts(self):
  ca,a=self.peers[0];cb,b=self.peers[1];r=Requirements(ca)
  doc=r.apply(A,dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=1,block_id='b'))['document'];uid=next(iter(doc['units']))
  p=b.receive(B,self.export(0,A));self.assertFalse(p['conflicts']);b.apply(B,dict(id=p['id'],explicit_confirmation=True))
  rb=Requirements(cb);db=rb.read(B,doc['id']);rb.apply(B,dict(request_id=str(uuid.uuid4()),action='assign',session_id=db['id'],expected_revision=db['revision'],unit_id=uid,field='Object',start=17,end=26))
  req=dict(request_id=str(uuid.uuid4()),action='assign',session_id=doc['id'],expected_revision=doc['revision'],unit_id=uid,field='Subject',start=0,end=5);r.apply(A,req)
  raw=self.export(1,B);plan=a.receive(A,raw);self.assertEqual(len(plan['conflicts']),1)
  d=plan['conflicts'][0];plan=a.prepare(A,dict(id=plan['id'],decisions={d['pair']:{d['id']:{'action':'incoming'}}}));self.assertFalse(plan['conflicts'])
  a.apply(A,dict(id=plan['id'],explicit_confirmation=True))
  final=r.read(A,doc['id']);self.assertEqual(final['units'][uid]['Object'],'equipment');self.assertEqual(final['edited_by'],B)
  self.assertTrue(any(x['edited_by']==A for x in final['steps']))
  # Saved interpretation authored by B is now visible/editable as A after return.
  s=Interpretations(ca);fields={k:dict(value='',basis='unresolved',references=[],gaps=[]) for k in KEYS}
  s.save(A,dict(request_id=str(uuid.uuid4()),unit_id=uid,expected_revision=0,context_fingerprint=s.context(A,uid)['fingerprint'],fields=fields))
  returned=b.receive(B,self.export(0,A));self.assertFalse(returned['conflicts']);b.apply(B,dict(id=returned['id'],explicit_confirmation=True))
  self.assertEqual(Interpretations(cb).read(B,uid)['history'][0]['edited_by'],A)
  with cb.db() as db:self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
