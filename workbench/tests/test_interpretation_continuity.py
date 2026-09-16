"""Working-copy recovery, absence semantics, typed catalogs and package round trips."""
import json
import uuid
import unittest
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import test_interpretations as fixture
from local_workbench.interpretation_continuity import Drafts, review_ready
from local_workbench.interpretations import Interpretations, checking_logic
from local_workbench.site_catalog import Catalog, mapping_issues
from local_workbench.requirement_delivery import Delivery, key_for
from local_workbench.requirements import Requirements
from local_workbench.check_design import empty_design
from local_workbench.sqlite_support import connect
from local_workbench.snapshot_graph import node, compare

A=fixture.ACTOR
class ContinuityTests(unittest.TestCase):
 setUp=fixture.InterpretationTests.setUp
 tearDown=fixture.InterpretationTests.tearDown
 request=fixture.InterpretationTests.request
 fields=fixture.InterpretationTests.fields
 step=fixture.InterpretationTests.step
 def other(self):
  root=self.root/'peer';root.mkdir(exist_ok=True)
  c=SimpleNamespace(db=lambda:connect(root/'test.sqlite'),lock=threading.RLock(),read_material=lambda a,i:deepcopy(self.material))
  c.app=SimpleNamespace(runtime=root,collaboration=c);return c
 def test_not_stated_review_does_not_create_unconditional_condition(self):
  fields=self.fields()
  for f in fields.values():f.update(state='not_stated',absence_reason='Not explicit in this reviewed passage.')
  req=self.request();req.update(fields=fields,action='review')
  self.s.save(A,req);saved=self.s.read(A,self.uid)
  self.assertTrue(saved['reviewed']);self.assertEqual(len(saved['logic']['gaps']),6)
  self.assertIn('Not explicitly stated',saved['logic']['steps'][1]['description'])
  self.assertFalse(saved['logic']['executable']);self.assertIsNone(saved['querybuilder']['condition'])
 def test_not_stated_needs_reason_and_cannot_hide_written_value(self):
  req=self.request();f=req['fields']['condition'];f.update(state='not_stated',absence_reason='')
  with self.assertRaises(ValueError):self.s.save(A,req)
  f.update(absence_reason='Not stated',value='always')
  with self.assertRaises(ValueError):self.s.save(A,req)
  self.assertFalse(review_ready(dict(value='',basis='unresolved',gaps=[])))
 def test_drafts_restart_conflict_idempotence_isolation_tombstone(self):
  drafts=Drafts(self.c);body=dict(fields=self.fields(),revision=0,material_id=self.material['id'],title='Storm check')
  req=dict(request_id=str(uuid.uuid4()),unit_id=self.uid,expected_revision=0,body=body)
  result=drafts.save(A,req);self.assertEqual(result,drafts.save(A,req))
  self.assertEqual(Drafts(self.c).listing(A,self.uid)['body'],body)
  self.assertEqual(Drafts(self.c).listing('Ana Jokic')['drafts'],[])
  with self.assertRaises(ValueError):drafts.save('Ana Jokic',req)
  self.assertEqual(drafts.save(A,dict(req,request_id=str(uuid.uuid4())))['status'],'conflict')
  self.assertEqual(self.s.read(A,self.uid)['revision'],0)
  clear=dict(req,request_id=str(uuid.uuid4()),expected_revision=1,body=None);drafts.save(A,clear)
  self.assertEqual(drafts.listing(A)['drafts'],[]);self.assertIsNone(drafts.listing(A,self.uid)['body'])
  self.assertEqual(drafts.listing(A,self.uid)['revision'],2)
 def test_impact_names_affected_fields_and_rule_ids(self):
  req=self.request();req['fields']['condition'].update(value='after a storm',basis='source',references=[dict(id=self.material['id']+':b',quote='after a storm')])
  design=empty_design();design['groups']['condition']={'id':'cg','condition':'AND','rules':[dict(id='cr',field='events.kind',operator='equal',type='string',value='storm',interpretation_field='condition')]};req['check_design']=design
  self.s.save(A,req);self.assertEqual(self.s.read(A,self.uid)['impact']['status'],'current')
  self.material['blocks'][0]['text']=fixture.TEXT.replace('storm','earthquake')
  item=self.s.read(A,self.uid)['impact']['items'][0]
  self.assertIn('condition',item['fields']);self.assertEqual(item['rules'],['cr']);self.assertEqual(item['before'],fixture.TEXT);self.assertIn('earthquake',item['after'])
 def test_catalog_no_defaults_versions_types_and_operators(self):
  catalog=Catalog(self.c);self.assertEqual(catalog.read()['fields'],[])
  field=dict(field='events.kind',label='Event kind',type='string',operators=['equal'],description='Fixture agreement only')
  catalog.save(A,dict(revision=0,fields=[field]));self.assertEqual(Catalog(self.c).read()['revision'],1)
  with self.assertRaises(ValueError):catalog.save(A,dict(revision=0,fields=[field]))
  with self.assertRaises(ValueError):catalog.save(A,dict(revision=1,fields=[dict(field,type='boolean',operators=['contains'])]))
  design=empty_design();design['groups']['scope']=dict(id='g',condition='AND',rules=[dict(id='r',field='events.kind',type='integer',operator='equal',value=1,interpretation_field='scope')])
  self.assertEqual(mapping_issues(design,catalog.read())[0]['rule_id'],'r')
 def test_catalog_revision_is_bound_on_formal_save(self):
  catalog=Catalog(self.c);catalog.save(A,dict(revision=0,fields=[]))
  req=self.request();req['catalog_revision']=0
  self.assertEqual(self.s.save(A,req)['status'],'conflict')
  req.update(request_id=str(uuid.uuid4()),catalog_revision=1);self.s.save(A,req)
  self.assertEqual(self.s.read(A,self.uid)['catalog_snapshot']['revision'],1)
 def test_delivery_round_trip_history_origin_and_no_draft_or_secret(self):
  req=self.request();req['fields']['condition'].update(value='after a storm',basis='source',references=[dict(id=self.material['id']+':b',quote='after a storm')]);self.s.save(A,req)
  delivery=Delivery(self.c);payload=list(delivery.capture())[0]['value'];delivery.validate(payload)
  self.assertNotIn('api_key',json.dumps(payload));self.assertNotIn('drafts',payload)
  peer=self.other();incoming=Delivery(peer);rid=str(uuid.uuid4());result=incoming.apply(payload,rid)
  self.assertEqual(incoming.apply(payload,rid),result)
  saved=Interpretations(peer).read(A,self.uid);self.assertEqual(saved['fields'],self.s.read(A,self.uid)['fields'])
  self.assertEqual(saved['lineage']['source']['source_id'],'fixture');self.assertEqual(saved['lineage']['fields'][0]['key'],'condition')
  next_payload=list(incoming.capture())[0]['value'];incoming.validate(next_payload)
  with peer.db() as db:self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
  with self.assertRaises(ValueError):Interpretations(peer).read('Ana Jokic',self.uid)
 def test_delivery_rejects_wrong_actor_dangling_links_and_changed_quotes(self):
  self.s.save(A,self.request());delivery=Delivery(self.c);payload=list(delivery.capture())[0]['value']
  bad=deepcopy(payload);bad['interpretations'][0]['history'][0]['document']['actor']='Ana Jokic'
  with self.assertRaises(ValueError):delivery.validate(bad)
  bad=deepcopy(payload);bad['interpretations'][0]['history'][0]['document']['fields']['condition'].update(value='one day',basis='source',references=[dict(id=self.material['id']+':b',quote='within one day')])
  with self.assertRaises(ValueError):delivery.validate(bad)
  bad=deepcopy(payload);d=bad['sessions'][0]['document'];d['units'][self.uid]['exceptions']=[1,str(uuid.uuid4())];bad['sessions'][0]['steps'][-1]['document']=deepcopy(d)
  with self.assertRaises(ValueError):delivery.validate(bad)
 def test_divergent_versions_retain_both_histories_and_require_choice(self):
  delivery=Delivery(self.c);payload=list(delivery.capture())[0]['value'];peer=self.other();other=Delivery(peer);other.apply(payload,str(uuid.uuid4()))
  self.step('assign',field='Subject',start=0,end=48)
  new=list(delivery.capture())[0]['value'];other.apply(new,str(uuid.uuid4()))
  other.validate(list(other.capture())[0]['value'])
  with peer.db() as db:
   self.assertGreater(db.execute('SELECT COUNT(*) FROM requirement_steps').fetchone()[0],len(new['sessions'][0]['steps']))
   self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_delivery_archives').fetchone()[0],2)
  base=node(key_for(A),payload);left=node(base['key'],new,[base['id']]);right=node(base['key'],dict(payload,candidates=[{'different':'branch'}]),[base['id']]);nodes={n['id']:n for n in (base,left,right)}
  self.assertEqual(compare(nodes,left['id'],right['id'])['status'],'conflict')
 def test_semantic_exception_quantity_reference_and_time_preserved(self):
  # User meeting example is synthetic, not attributed to a law. The product
  # must retain exact counts and exception ownership, never translate into OR.
  self.step('extract',field='conditions',start=65,end=len(fixture.TEXT))
  req=self.request();req['fields']['condition'].update(value='after a storm',basis='source',references=[dict(id=self.material['id']+':b',quote='after a storm')])
  self.s.save(A,req);saved=self.s.read(A,self.uid)
  self.assertEqual(saved['logic']['source_structure']['requirement']['conditions'],self.doc['units'][self.uid]['conditions'])
  self.assertNotIn('within one day',json.dumps(saved['logic']));self.assertNotIn('integrity',json.dumps(saved['logic']))
  self.assertEqual(saved['querybuilder']['condition'],None)

 def test_formal_save_atomically_retires_only_matching_working_copy(self):
  drafts=Drafts(self.c);body=dict(fields=self.fields(),revision=0,material_id=self.material['id'])
  drafts.save(A,dict(request_id=str(uuid.uuid4()),unit_id=self.uid,expected_revision=0,body=body))
  req=self.request();req['draft_revision']=0
  self.assertEqual(self.s.save(A,req)['status'],'conflict')
  self.assertEqual(self.s.read(A,self.uid)['revision'],0)
  req.update(request_id=str(uuid.uuid4()),draft_revision=1)
  result=self.s.save(A,req);self.assertEqual(result['draft_revision'],2)
  self.assertIsNone(drafts.listing(A,self.uid)['body']);self.assertEqual(self.s.save(A,req),result)

 def test_exact_and_range_counts_exceptions_and_cross_reference_survive_delivery(self):
  # Synthetic source explicitly distinguishes an exception and referenced chapters.
  text='Check the chain or replace it except when secured. See Chapter 2, Chapter 3 and Chapter 4.'
  self.material['blocks'][0]['text']=text
  self.doc=self.r.apply(A,dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=1,block_id='b'))['document'];self.uid=next(iter(self.doc['units']))
  for phrase in ('Check the chain','replace it'):
   start=text.index(phrase);self.step('extract',field='subrequirement',start=start,end=start+len(phrase))
  self.step('quantity',field='subrequirement',quantity=[1,2])
  phrase='except when secured';start=text.index(phrase);self.step('extract',field='exceptions',start=start,end=start+len(phrase))
  for phrase in ('Chapter 2','Chapter 3','Chapter 4'):
   start=text.index(phrase);self.step('extract',field='conditions',start=start,end=start+len(phrase))
  self.step('quantity',field='conditions',quantity=3)
  self.s.save(A,self.request());saved=self.s.read(A,self.uid)
  structure=saved['logic']['source_structure']['requirement']
  self.assertEqual(structure['subrequirement'][0],[1,2]);self.assertEqual(structure['conditions'][0],3)
  self.assertEqual(saved['logic']['exceptions'][0]['owner_id'],self.uid)
  delivery=Delivery(self.c);v=list(delivery.capture())[0]['value'];peer=Delivery(self.other());peer.apply(v,str(uuid.uuid4()));peer.validate(list(peer.capture())[0]['value'])
  received=Interpretations(peer.c).read(A,self.uid)
  self.assertEqual(received['logic']['source_structure'],saved['logic']['source_structure'])
  self.assertEqual(received['querybuilder']['condition'],None)
