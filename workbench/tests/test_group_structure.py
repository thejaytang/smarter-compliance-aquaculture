"""Unified groups: scope, source fidelity, references and explicit-save boundaries."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import threading
import unittest
import uuid
from backend.system3.requirements import Requirements
from backend.system3.requirement_structure import legacy, walk, validate, pending, edit
from backend.system3.requirement_delivery import Delivery
from backend.system3.interpretations import Interpretations, annotations, KEYS
from backend.shared.sqlite_support import connect

ACTOR='Weijie Tang'
TEXT='甲 shall inspect 设备 A; 乙 shall inspect 设备 B after a storm unless rope secured. 🐟\nBlå linje.'

class GroupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite'
  self.material=dict(id='a'*32,revision=1,source=dict(source_id='demo',snapshot_id='v1',content_hash='abc'),blocks=[dict(id='b',type='text',text=TEXT,source_refs=[{'page':1}])])
  self.c=SimpleNamespace(db=lambda:connect(self.path),lock=threading.RLock(),read_material=lambda a,i:deepcopy(self.material))
  self.c.app=SimpleNamespace(runtime=Path(self.tmp.name),collaboration=self.c)
  self.r=Requirements(self.c)
  self.doc=self.r.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=self.material['id'],material_revision=1,block_id='b'))['document']
  self.uid=next(iter(self.doc['units']))
 def tearDown(self):self.tmp.cleanup()
 def step(self,action,**args):
  request=dict(action=action,request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=self.doc['revision'],**args)
  result=self.r.apply(ACTOR,request);self.doc=result['document'];return result
 def edit(self,op,node=None,**args):
  return self.step('structure',unit_id=self.uid,node_id=node or self.tree()['id'],operation=op,**args)
 def tree(self):return self.doc['structure_views'][self.uid]
 def nodes(self,kind=None,role=None):return [n for n,_ in walk(self.tree()) if (kind is None or n['kind']==kind) and (role is None or n.get('role')==role)]
 def span(self,text):a=TEXT.index(text);return dict(start=a,end=a+len(text))
 def add(self,role,text,node=None):return self.edit('add',node,field=role,**self.span(text))
 def test_shared_condition_keeps_subject_action_object_pairs(self):
  for words,subject,obj in [('甲 shall inspect 设备 A','甲','设备 A'),('乙 shall inspect 设备 B','乙','设备 B')]:
   self.edit('add-group',**self.span(words));clause=self.nodes('clause')[-1]
   for field,text in [('Subject',subject),('Main Verb','inspect'),('Object',obj)]:
    start=TEXT.index(text,clause['span'][0]);self.edit('add',clause['id'],field=field,start=start,end=start+len(text))
  self.add('conditions','after a storm');members=self.nodes('group','requirements')[0]
  self.assertIsNone(members['quantity']);self.edit('quantity',members['id'],quantity=2)
  root=self.tree();self.assertEqual({n['role'] for n in root['children']},{'requirements','conditions'})
  clauses=self.nodes('clause')[1:]
  self.assertEqual([[c['children'][0]['text'] for c in n['children'] if c['role'] in ('Subject','Object')] for n in clauses],[['甲','设备 A'],['乙','设备 B']])
  self.assertFalse(pending(root));self.step('done',unit_id=self.uid)
  ctx=Interpretations(self.c).context(ACTOR,self.uid);self.assertEqual(ctx['structure'],root)
  projected=annotations(self.c,ACTOR,self.material['id'])['spans'];self.assertTrue(any(s['field']=='Object' and TEXT[s['start']:s['end']]=='设备 B' for s in projected))
 def test_retired_not_operation_is_rejected_without_new_history(self):
  self.add('conditions','unless rope secured');node=self.nodes('group','conditions')[0]
  before=deepcopy(self.r.read(ACTOR,self.doc['id']))
  for value in (True,False):
   with self.assertRaisesRegex(ValueError,'Explicit NOT editing is unavailable'):
    self.edit('not',node['id'],negated=value)
  self.assertEqual(self.r.read(ACTOR,self.doc['id']),before)
  self.assertEqual(self.nodes('fragment')[0]['text'],'unless rope secured')
  self.assertFalse(node['negated'])
 def test_nested_fields_and_unicode_offsets_are_exact(self):
  self.add('Object','🐟\nBlå linje');leaf=self.nodes('fragment')[0];self.edit('decompose',leaf['id'])
  node=self.nodes('group','Object')[-1];self.add('Object','🐟',node['id']);self.add('Object','Blå',node['id'])
  self.edit('quantity',node['id'],quantity=[1,2]);self.assertEqual([n['text'] for n in self.nodes('fragment')],['🐟','Blå'])
  with self.assertRaises(ValueError):self.add('Object','甲',node['id'])
  with self.assertRaises(ValueError):self.edit('quantity',node['id'],quantity=[1,3])
  with self.assertRaises(ValueError):self.edit('quantity',node['id'],quantity=True)
  self.assertEqual(Requirements(self.c).read(ACTOR,self.doc['id'])['structures'],self.doc['structures'])
 def test_preview_is_not_history_and_save_is_idempotent(self):
  revision=self.doc['revision'];request=dict(action='structure',request_id=str(uuid.uuid4()),unit_id=self.uid,node_id=self.tree()['id'],operation='add',field='Subject',**self.span('甲'))
  preview=dict(action='preview',request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=revision,steps=[request])
  out=self.r.apply(ACTOR,preview);self.assertIn('structures',out['document'])
  saved=self.r.read(ACTOR,self.doc['id']);self.assertNotIn('structures',saved);self.assertEqual(saved['revision'],revision)
  commit=dict(preview,action='save-draft',request_id=str(uuid.uuid4()));first=self.r.apply(ACTOR,commit);self.assertEqual(first,self.r.apply(ACTOR,commit))
  with self.c.db() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_steps').fetchone()[0],2)
   body=json.loads(db.execute('SELECT body FROM requirement_sessions').fetchone()[0]);self.assertNotIn('structure_views',body)
   self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
  conflict=self.r.apply(ACTOR,dict(commit,request_id=str(uuid.uuid4())));self.assertEqual(conflict['status'],'conflict')
 def test_legacy_projection_preserves_counts_negation_and_history_restore(self):
  self.step('assign',unit_id=self.uid,field='Subject',**self.span('甲'))
  self.step('extract',unit_id=self.uid,field='exceptions',**self.span('rope secured'))
  before=deepcopy(self.doc);tree=legacy(self.doc,self.uid)
  self.assertFalse(next(n for n in tree['children'] if n['role']=='exceptions')['negated'])
  self.add('Object','设备 A');self.step('restore',history_revision=before['revision']);self.assertNotIn('structures',self.doc)
  with self.c.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_structure_nodes').fetchone()[0],0)
 def test_unresolved_counts_block_completion_and_mixed_fields_cannot_get_qc(self):
  self.add('Subject','甲');self.add('Subject','乙')
  with self.assertRaises(ValueError):self.step('done',unit_id=self.uid)
  with self.assertRaises(ValueError):self.edit('quantity',quantity=2)
  node=self.nodes('group','Subject')[0];self.edit('quantity',node['id'],quantity=[1,2]);self.step('done',unit_id=self.uid)
 def test_reference_is_owned_and_cycles_are_rejected(self):
  other=self.r.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=self.material['id'],material_revision=1,block_id='b'))['document'];oid=next(iter(other['units']))
  self.edit('link',target_id=oid)
  with self.c.db() as db:
   self.assertEqual(db.execute('SELECT target_id FROM requirement_structure_nodes WHERE target_id IS NOT NULL').fetchone()[0],oid)
  with self.assertRaises(ValueError):self.r.apply(ACTOR,dict(action='structure',request_id=str(uuid.uuid4()),session_id=other['id'],expected_revision=other['revision'],unit_id=oid,node_id=other['structure_views'][oid]['id'],operation='link',target_id=self.uid))
  with self.assertRaises(ValueError):self.edit('link',target_id=str(uuid.uuid4()))
  with self.assertRaises(ValueError):self.r.read('Nabil',self.doc['id'])
 def test_delivery_contains_structure_and_rejects_source_or_count_tampering(self):
  self.add('Subject','甲');delivery=Delivery(self.c);bundle=delivery.capture()[0]['value'];delivery.validate(bundle)
  for key,value in [('text','invented'),('span',[0,900])]:
   altered=deepcopy(bundle)
   for d in [altered['sessions'][0]['document'],altered['sessions'][0]['steps'][-1]['document']]:
    leaf=next(n for n,_ in walk(d['structures'][self.uid]) if n['kind']=='fragment');leaf[key]=value
   with self.assertRaises(ValueError):delivery.validate(altered)
  altered=deepcopy(self.doc);altered['structures'][self.uid]['children'][0]['quantity']=2
  with self.assertRaises(ValueError):validate(altered)
 def test_ungroup_never_erases_not_or_nonall_meaning(self):
  self.add('conditions','after a storm');self.add('conditions','rope secured');group=self.nodes('group','conditions')[0]
  self.edit('group',group['id'],selected=[n['id'] for n in self.nodes('fragment')]);child=self.nodes('group','conditions')[-1]
  self.edit('quantity',child['id'],quantity=2)
  historical=deepcopy(self.doc)
  next(n for n,_ in walk(historical['structures'][self.uid]) if n['id']==child['id'])['negated']=True
  validate(historical)
  with self.assertRaises(ValueError):edit(historical,dict(unit_id=self.uid,node_id=child['id'],operation='ungroup'))
  self.assertTrue(next(n for n,_ in walk(historical['structures'][self.uid]) if n['id']==child['id'])['negated'])

 def test_saved_interpretation_and_full_delivery_keep_group_logic(self):
  self.add('conditions','unless rope secured')
  service=Interpretations(self.c);ctx=service.context(ACTOR,self.uid)
  fields={k:dict(value='',basis='unresolved',references=[],gaps=[]) for k in KEYS}
  saved=service.save(ACTOR,dict(request_id=str(uuid.uuid4()),unit_id=self.uid,expected_revision=0,context_fingerprint=ctx['fingerprint'],fields=fields))
  self.assertEqual(service.read(ACTOR,self.uid)['logic']['source_structure']['structure'],self.tree())
  delivery=Delivery(self.c);bundle=delivery.capture()[0]['value'];delivery.validate(bundle)
  root=Path(self.tmp.name)/'peer';root.mkdir();peer=SimpleNamespace(db=lambda:connect(root/'test.sqlite'),lock=threading.RLock(),read_material=lambda a,i:deepcopy(self.material));peer.app=SimpleNamespace(runtime=root,collaboration=peer)
  other=Delivery(peer);rid=str(uuid.uuid4());result=other.apply(bundle,rid);self.assertEqual(other.apply(bundle,rid),result)
  other.validate(other.capture()[0]['value'])
  restored=Requirements(peer).read(ACTOR,self.doc['id']);self.assertEqual(restored['structures'],self.doc['structures'])
  with peer.db() as db:self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

 def test_no_role_allows_not_and_exception_links_another_entry(self):
  self.add('Subject','甲');node=self.nodes('group','Subject')[0]
  with self.assertRaisesRegex(ValueError,'Explicit NOT editing is unavailable'):self.edit('not',node['id'],negated=True)
  self.add('conditions','after a storm');condition=self.nodes('group','conditions')[0]
  with self.assertRaisesRegex(ValueError,'Explicit NOT editing is unavailable'):self.edit('not',condition['id'],negated=True)
  with self.assertRaisesRegex(ValueError,'must link another'):self.edit('add-exception',**self.span('unless rope secured'))
  other=self.r.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=self.material['id'],material_revision=1,block_id='b'))['document'];oid=next(iter(other['units']))
  self.edit('link',field='exceptions',target_id=oid)
  exception=self.nodes('group','exceptions')[0];self.assertFalse(exception['negated'])
  self.assertEqual(exception['children'][0]['kind'],'reference');self.assertEqual(exception['children'][0]['target_id'],oid)
  bundle=Delivery(self.c).capture()[0]['value'];Delivery(self.c).validate(bundle)

 def test_links_reject_internal_items_and_keep_referenced_entry_when_unlinked(self):
  self.step('extract',unit_id=self.uid,field='conditions',**self.span('after a storm'))
  child=next(uid for uid in self.doc['units'] if uid!=self.uid)
  with self.assertRaisesRegex(ValueError,'another complete Requirement'):self.edit('link',field='exceptions',target_id=child)
  other=self.r.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=self.material['id'],material_revision=1,block_id='b'))['document'];oid=next(iter(other['units']))
  other=self.r.apply(ACTOR,dict(action='extract',request_id=str(uuid.uuid4()),session_id=other['id'],expected_revision=other['revision'],unit_id=oid,field='conditions',**self.span('after a storm')))['document']
  internal=next(uid for uid in other['units'] if uid!=oid)
  with self.assertRaisesRegex(ValueError,'another complete Requirement'):self.edit('link',field='subrequirement',target_id=internal)
  self.edit('link',field='subrequirement',target_id=oid);ref=self.nodes('reference','subrequirement')[0];self.edit('remove',ref['id'])
  self.assertEqual(self.r.read(ACTOR,other['id'])['revision'],other['revision'])

 def test_source_group_moves_marks_and_degroup_preserves_them(self):
  self.add('Subject','甲');self.add('Object','设备 A')
  before={n['id'] for n in self.nodes('fragment')}
  self.edit('add-group',**self.span('甲 shall inspect 设备 A'))
  clause=self.nodes('clause')[-1];self.assertEqual({c['role'] for c in clause['children']},{'Subject','Object'})
  self.assertEqual({n['id'] for n in self.nodes('fragment')},before)
  self.edit('degroup-range',clause['id'],**self.span('甲 shall inspect 设备 A'))
  self.assertEqual(len(self.nodes('clause')),1);self.assertEqual({n['id'] for n in self.nodes('fragment')},before)
 def test_clear_selected_marks_preserves_source_and_explicit_group(self):
  self.edit('add-group',**self.span('甲 shall inspect 设备 A'));clause=self.nodes('clause')[-1]
  self.add('Object','设备 A',clause['id']);self.edit('clear-range',clause['id'],**self.span('设备'))
  self.assertEqual([n['text'] for n in self.nodes('fragment')],[' A']);self.assertEqual(self.doc['units'][self.uid]['text'],TEXT)
  self.edit('clear-range',clause['id'],**self.span('设备 A'))
  self.assertEqual(len(self.nodes('fragment')),0);self.assertEqual(len(self.nodes('clause')),2)

 def test_clear_source_marks_also_updates_local_nested_units_without_erasing_history(self):
  self.step('assign',unit_id=self.uid,field='Main Verb',**self.span('inspect'))
  self.step('extract',unit_id=self.uid,field='subrequirement',**self.span('inspect 设备 A'))
  child=next(i for i in self.doc['units'] if i!=self.uid)
  self.step('assign',unit_id=child,field='Main Verb',start=0,end=7)
  count=len(self.doc['units']);self.edit('clear-range',**self.span('inspect'))
  self.assertEqual(len(self.doc['units']),count)
  self.assertFalse(any(n.get('role')=='Main Verb' and n['kind']=='fragment' for n,_ in walk(self.doc['structures'][child])))
  self.assertFalse(any(n.get('role')=='Main Verb' and n['kind']=='fragment' for n in self.nodes()))

 def test_degroup_can_remove_an_empty_condition_group_without_a_fake_qc(self):
  self.add('conditions','after a storm');leaf=self.nodes('fragment')[0];self.edit('decompose',leaf['id'])
  self.edit('degroup-range',leaf['id'],**self.span('after a storm'))
  self.assertEqual(self.tree()['children'],[])

 def test_remove_group_deletes_descendants_only_after_explicit_save(self):
  self.edit('add-group',**self.span('甲 shall inspect 设备 A'));branch=self.nodes('clause')[-1]
  self.add('Subject','甲',branch['id']);self.add('Object','设备 A',branch['id'])
  leaf=self.nodes('fragment','Object')[0];self.edit('decompose',leaf['id']);self.add('Object','设备',leaf['id'])
  self.add('conditions','after a storm')
  before=deepcopy(self.doc);removed={n['id'] for n,_ in walk(next(n for n in self.nodes() if n['id']==branch['id']))}
  request=dict(action='preview',request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=self.doc['revision'],steps=[dict(action='structure',request_id=str(uuid.uuid4()),unit_id=self.uid,node_id=branch['id'],operation='remove')])
  preview=self.r.apply(ACTOR,request)['document'];remaining={n['id'] for n,_ in walk(preview['structures'][self.uid])}
  self.assertFalse(removed & remaining);self.assertEqual(preview['text'],TEXT)
  self.assertEqual([n['text'] for n,_ in walk(preview['structures'][self.uid]) if n['kind']=='fragment'],['after a storm'])
  self.assertEqual(self.r.read(ACTOR,self.doc['id'])['revision'],before['revision'])
  self.assertEqual([n['role'] for n in preview['structures'][self.uid]['children']],['conditions'])
  self.doc=self.r.apply(ACTOR,dict(request,action='save-draft',request_id=str(uuid.uuid4())))['document']
  self.step('restore',history_revision=before['revision'])
  self.assertTrue(removed <= {n['id'] for n in self.nodes()})
