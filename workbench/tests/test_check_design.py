import unittest
from copy import deepcopy
from backend.system3.check_design import empty_design,validate_design,querybuilder_projection

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
