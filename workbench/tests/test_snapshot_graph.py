from copy import deepcopy
import unittest
from local_workbench.snapshot_graph import node, compare, preview, validate_graph

class SnapshotGraphTests(unittest.TestCase):
 def setUp(self):
  self.base=node('material:x',{'blocks':[{'id':'a','text':'one'},{'id':'b','text':'two'}]})
  self.nodes={self.base['id']:self.base}
 def add(self,value,parent=None,actor='Ana Jokic'):
  n=node('material:x',value,[parent or self.base['id']],actor,'2026-09-14T10:00:00+00:00');self.nodes[n['id']]=n;return n['id']
 def test_parallel_edits_survive_and_repeat_is_noop(self):
  left=self.add({'blocks':[{'id':'a','text':'ONE'},{'id':'b','text':'two'}]})
  right=self.add({'blocks':[{'id':'a','text':'one'},{'id':'b','text':'TWO'}]})
  r=compare(self.nodes,left,right);self.assertEqual(r['status'],'merged')
  self.assertEqual([b['text'] for b in self.nodes[r['head']]['value']['blocks']],['ONE','TWO'])
  self.assertEqual(compare(self.nodes,r['head'],right)['head'],r['head'])
 def test_overlap_requires_explicit_choice_and_preserves_both_nodes(self):
  a=self.add({'blocks':[{'id':'a','text':'A'},{'id':'b','text':'two'}]})
  b=self.add({'blocks':[{'id':'a','text':'B'},{'id':'b','text':'two'}]})
  r=compare(self.nodes,a,b);self.assertTrue(r['unresolved'])
  choices={r['pair']:{r['unresolved'][0]:{'action':'incoming'}}}
  done=compare(self.nodes,a,b,choices);self.assertFalse(done['unresolved']);self.assertIn(a,self.nodes);self.assertIn(b,self.nodes)
 def test_old_snapshot_never_wins_due_to_timestamp(self):
  newer=self.add({'blocks':[]});r=compare(self.nodes,newer,self.base['id'])
  self.assertEqual(r['head'],newer)
 def test_missing_record_is_not_a_deletion(self):
  r=preview(self.nodes,{'material:x':[self.base['id']]},{},{})
  self.assertEqual(r['heads']['material:x'],[self.base['id']])
 def test_unrelated_documents_are_explicit_conflict(self):
  n=node('material:x',{'blocks':[]});self.nodes[n['id']]=n
  self.assertEqual(compare(self.nodes,self.base['id'],n['id'])['status'],'conflict')
 def test_tampered_content_missing_parents_cross_record_rejected(self):
  n=self.add({'blocks':[]})
  bad=deepcopy(self.nodes);bad[n]['value']['blocks']=['tampered']
  with self.assertRaises(ValueError):validate_graph(bad,{'material:x':[n]})
  bad={n:self.nodes[n]}
  with self.assertRaises(ValueError):validate_graph(bad,{'material:x':[n]})
  with self.assertRaises(ValueError):validate_graph(self.nodes,{'material:other':[n]})
 def test_multiple_heads_keep_conflict_until_resolved(self):
  a=self.add({'blocks':[]});b=self.add({'blocks':[{'id':'a','text':'changed'},{'id':'b','text':'two'}]})
  r=preview(self.nodes,{'material:x':[a]},self.nodes,{'material:x':[b]})
  self.assertTrue(r['conflicts']);self.assertEqual(set(r['heads']['material:x']),{a,b})
if __name__=='__main__':unittest.main()
