"""Named peers edit one saved graph; provenance and source guards survive exchange."""
import json
import unittest
import uuid
from copy import deepcopy
import test_interpretation_continuity as fixture
from local_workbench.requirements import Requirements
from local_workbench.interpretations import Interpretations, annotations
from local_workbench.requirement_delivery import Delivery, SHARED_SCHEMA, SHARED_KEY

A='Weijie Tang'
B='Ana Jokic'
class SharedRequirementsTests(unittest.TestCase):
 tearDown=fixture.ContinuityTests.tearDown
 request=fixture.ContinuityTests.request
 fields=fixture.ContinuityTests.fields
 step=fixture.ContinuityTests.step
 other=fixture.ContinuityTests.other
 # Reuse fixture helpers, not the actor-isolation assertions of the legacy mode.
 def setUp(self):
  fixture.ContinuityTests.setUp(self);self.c.app.peer_sync=True
 def test_peer_can_read_edit_and_see_actual_history_author(self):
  self.assertEqual(len(self.r.listing(B,self.material['id'])['sessions']),1)
  self.assertEqual(self.r.search(B,'storm')['units'][0]['id'],self.uid)
  changed=self.r.apply(B,dict(request_id=str(uuid.uuid4()),action='assign',session_id=self.doc['id'],expected_revision=self.doc['revision'],unit_id=self.uid,field='Subject',start=0,end=48))
  saved=self.r.read(A,self.doc['id']);self.assertEqual(saved['steps'][0]['edited_by'],B)
  self.assertEqual(saved['created_by'],A)
  self.assertEqual(self.r.apply(A,dict(request_id=str(uuid.uuid4()),action='assign',session_id=self.doc['id'],expected_revision=self.doc['revision'],unit_id=self.uid,field='Subject',start=0,end=48))['status'],'conflict')
  with self.c.db() as db:self.assertEqual(db.execute('SELECT actor FROM requirement_units WHERE id=?',(self.uid,)).fetchone()[0],A)
  self.s.save(A,self.request());d=self.s.read(B,self.uid)
  self.assertEqual(d['impact']['status'],'current')
  req=dict(self.request(),expected_revision=1);req['fields']['verification']['value']='Shared evidence design'
  self.assertEqual(self.s.save(B,req)['revision'],2)
  d=self.s.read(A,self.uid);self.assertEqual(d['history'][0]['edited_by'],B)
  self.assertEqual(d['fields']['verification']['value'],'Shared evidence design')
  self.assertEqual(self.s.save(A,dict(req,request_id=str(uuid.uuid4())))['status'],'conflict')
  self.assertEqual(self.s.trace(B,self.uid)['status'],'saved')
 def test_cross_author_links_round_trip_and_edit(self):
  other=self.r.apply(B,dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=1,block_id='b'))['document'];target=next(iter(other['units']))
  self.step('structure',operation='link',node_id=self.uid+'/structure',field='subrequirement',target_id=target)
  self.s.save(B,self.request())
  payload=Delivery(self.c).capture()[0];self.assertEqual(payload['key'],SHARED_KEY)
  self.assertEqual(payload['value']['schema'],SHARED_SCHEMA)
  Delivery(self.c).validate(payload['value'])
  peer=self.other();peer.app.peer_sync=True;delivery=Delivery(peer)
  delivery.apply(payload['value'],str(uuid.uuid4()))
  rs=Requirements(peer);ips=Interpretations(peer)
  self.assertEqual(len(rs.listing(B,self.material['id'])['sessions']),2)
  self.assertEqual(ips.read(B,self.uid)['fields'],self.s.read(A,self.uid)['fields'])
  d=rs.read(B,self.doc['id']);rs.apply(B,dict(request_id=str(uuid.uuid4()),action='reopen',session_id=d['id'],expected_revision=d['revision'],unit_id=self.uid))
  delivery.validate(delivery.capture()[0]['value'])
  with peer.db() as db:self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
 def test_source_change_and_unauthenticated_actor_still_rejected(self):
  self.material['blocks'][0]['text']='changed'
  with self.assertRaisesRegex(ValueError,'source passage changed'):self.r.apply(B,dict(request_id=str(uuid.uuid4()),action='assign',session_id=self.doc['id'],expected_revision=self.doc['revision'],unit_id=self.uid,field='Subject',start=0,end=7))
  with self.assertRaises(ValueError):self.r.listing('Nobody',self.material['id'])
 def test_legacy_import_is_shared_without_rewriting_original_author(self):
  self.c.app.peer_sync=False;v=Delivery(self.c).capture()[0]['value']
  peer=self.other();peer.app.peer_sync=True;delivery=Delivery(peer);delivery.apply(v,str(uuid.uuid4()))
  rs=Requirements(peer);self.assertEqual(len(rs.listing(B,self.material['id'])['sessions']),1)
  self.assertEqual(rs.read(B,self.doc['id'])['created_by'],A)
  delivery.validate(delivery.capture()[0]['value'])

