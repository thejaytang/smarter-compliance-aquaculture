import unittest
from copy import deepcopy
from backend.system3.check_design import empty_design,validate_design,querybuilder_projection,set_handoff,FIELD_KEYS

class CheckDesignTests(unittest.TestCase):
 def design(self):
  d=empty_design();d['groups']['scope']={'id':'a','condition':'AND','rules':[{'id':'r','field':'component.installed','operator':'equal','value':True,'type':'boolean','interpretation_field':'scope'}]};return d
 def test_nested_or_and_negative_leaf_keep_exact_semantics(self):
  d=self.design();d['groups']['condition']={'id':'c','condition':'OR','rules':[{'id':'r2','field':'event.magnitude','operator':'greater_or_equal','value':4,'type':'double','interpretation_field':'condition'}, {'id':'r3','field':'component.region','operator':'not_equal','value':'north','type':'string','interpretation_field':'condition'}]}
  result=querybuilder_projection(d);self.assertEqual(result['condition']['condition'],'OR');self.assertEqual(result['condition']['rules'][0]['value'],4);self.assertNotIn('id',result['condition']['rules'][0]);self.assertEqual(validate_design(d),d)
 def test_invalid_mapping_types_operators_and_extra_sql_rejected(self):
  for changes in ({'field':'x;DROP TABLE source'},{'field':'db.table.column'},{'operator':'execute'},{'value':'true'},{'type':'sql'},{'interpretation_field':'made-up'},{'sql':'1=1'}):
   with self.subTest(changes=changes):
    d=self.design();d['groups']['scope']['rules'][0].update(changes)
    with self.assertRaises(ValueError):validate_design(d)
 def test_empty_duplicate_and_negated_groups_fail_closed(self):
  for changes in ({'rules':[]},{'condition':'NOT'},{'not':True}):
   d=self.design();d['groups']['scope'].update(changes)
   with self.assertRaises(ValueError):validate_design(d)
  d=self.design();d['groups']['scope']['rules'].append(deepcopy(d['groups']['scope']['rules'][0]))
  with self.assertRaises(ValueError):validate_design(d)
 def test_bounds_and_finite_numbers(self):
  for val in (float('nan'),float('inf')):
   d=self.design();d['groups']['scope']['rules'][0].update(type='double',value=val)
   with self.assertRaises(ValueError):validate_design(d)
  d=self.design();d['groups']['scope']['rules'][0].update(type='integer',operator='between',value=[8,4])
  with self.assertRaises(ValueError):validate_design(d)
 def test_unmapped_groups_are_not_true_filters(self):
  self.assertEqual(querybuilder_projection(None),{'scope':None,'condition':None,'demand':None})
 def test_set_handoff_preserves_unmapped_semantics_and_requires_current_confirmation(self):
  d=empty_design(2);d.update(object_type='Component',identity_field='component.id',assessment_context='The same storm event and assessment period')
  fields={k:dict(value=k,basis='interpretation',references=[],gaps=[]) for k in FIELD_KEYS}
  catalog=dict(revision=1,fields=[dict(field='component.id',type='string',operators=['equal'])])
  for key in d['groups']:
   d['groups'][key]=dict(id=key,condition='AND',rules=[dict(id=key+'r',field='component.id',type='string',operator='equal',value='s1',interpretation_field=key)])
  def confirm():d['based_on']=dict(fields={k:f['value'] for k,f in fields.items()},context_fingerprint='fp',catalog_revision=1,design=deepcopy({k:v for k,v in d.items() if k!='based_on'}))
  confirm();h=set_handoff(fields,d,'fp',catalog)
  self.assertEqual(h['mapping_status'],'ready_for_consumer_validation');self.assertFalse(h['executable'])
  self.assertEqual(h['sets']['B']['input'],'A');self.assertEqual(h['composition'],dict(operator='subset_of',left='B',right='C'))
  self.assertEqual(set_handoff(fields,d,'new context',catalog)['mapping_status'],'incomplete')
  self.assertEqual(set_handoff(fields,d,'fp',dict(catalog,revision=2))['mapping_status'],'incomplete')
  fields['scope']['value']='Changed scope';self.assertEqual(set_handoff(fields,d,'fp',catalog)['mapping_status'],'incomplete');confirm()
  d['groups']['scope']['rules'][0]['value']='s2';self.assertEqual(set_handoff(fields,d,'fp',catalog)['mapping_status'],'incomplete')
  d['groups']['demand']['condition']='OR';d['groups']['demand']['rules'].append(dict(id='predicate',expression='Integrity check or replacement for the same component after the event',interpretation_field='demand'))
  confirm();h=set_handoff(fields,d,'fp',catalog);self.assertIsNone(h['querybuilder']['demand']);self.assertIn('Integrity check',h['sets']['C']['rules']['rules'][1]['expression'])
  d['groups']['scope']['not']=True;self.assertIsNone(querybuilder_projection(d)['scope'])
 def test_concept_identity_references_and_semantic_handoff(self):
  d=empty_design(2);d['concepts']=[dict(id='anchor',label='Anchor line',kind='concept',status='proposed',references=[dict(id='b',quote='anchoring line')])]
  d['groups']['scope']=dict(id='g',condition='AND',rules=[dict(id='r',expression='partOf some Anchor Line',interpretation_field='scope',concept_ids=['anchor'])])
  self.assertEqual(validate_design(d,[dict(id='b',text='part of the anchoring line')]),d)
  with self.assertRaisesRegex(ValueError,'quotation'):validate_design(d,[dict(id='b',text='different source')])
  for ids in (['missing'],['anchor','anchor'],[{}]):
   bad=deepcopy(d);bad['groups']['scope']['rules'][0]['concept_ids']=ids
   with self.assertRaises(ValueError):validate_design(bad)
  f={k:dict(value='Previous explanation',basis='interpretation',references=[],gaps=[]) for k in FIELD_KEYS}
  handoff=set_handoff(f,d,'fp',{'fields':[]});self.assertEqual(handoff['sets']['A']['definition'],'(partOf some Anchor Line)')
  self.assertEqual(f['scope']['value'],'Previous explanation');self.assertEqual(handoff['concepts'],d['concepts']);self.assertIsNone(handoff['querybuilder']['scope'])
