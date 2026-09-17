from copy import deepcopy
import unittest
from backend.shared.collaboration_merge import merge_documents


def block(identity,text): return {'id':identity,'type':'text','text':text}
def document(*blocks): return {'blocks':list(blocks),'issues':[],'source_review':{}}


class CollaborationMergeTests(unittest.TestCase):
    def test_disjoint_fields_and_unchanged_candidate_keep_human_text(self):
        base=document(block('a','base'),block('b','base'))
        current=deepcopy(base);current['blocks'][0]['text']='human correction'
        incoming=deepcopy(base);incoming['blocks'][1]['text']='reviewer addition'
        result=merge_documents(base,current,incoming)
        self.assertEqual([b['text'] for b in result['merged']['blocks']],['human correction','reviewer addition'])
        self.assertFalse(result['unresolved'])
        self.assertEqual(base['blocks'][0]['text'],'base')
        self.assertEqual(result['differences'][0]['resolution'],'auto_current')

    def test_same_field_conflict_defaults_current_and_accepts_explicit_edit(self):
        base=document(block('a/b~c','base'));current=deepcopy(base);incoming=deepcopy(base)
        current['blocks'][0]['text']='ours';incoming['blocks'][0]['text']='theirs'
        preview=merge_documents(base,current,incoming);diff=preview['differences'][0]
        self.assertEqual(diff['path'],'/blocks/a~1b~0c/text')
        self.assertEqual(preview['merged'],current)
        self.assertEqual(preview['unresolved'],[diff['id']])
        result=merge_documents(base,current,incoming,{diff['id']:{'action':'edit','value':'human combined'}})
        self.assertFalse(result['unresolved']);self.assertEqual(result['merged']['blocks'][0]['text'],'human combined')
        self.assertEqual(merge_documents(base,current,incoming)['differences'][0]['id'],diff['id'])

    def test_same_shape_tables_merge_distinct_cells_and_conflict_on_same_cell(self):
        base=document({'id':'t','type':'table','table':{'rows':[['A','B'],['C','D']],'merges':[]}})
        current=deepcopy(base);incoming=deepcopy(base)
        current['blocks'][0]['table']['rows'][0][0]='ours';incoming['blocks'][0]['table']['rows'][1][1]='theirs'
        result=merge_documents(base,current,incoming)
        self.assertFalse(result['unresolved']);self.assertEqual(result['merged']['blocks'][0]['table']['rows'],[['ours','B'],['C','theirs']])
        incoming['blocks'][0]['table']['rows'][0][0]='conflict'
        result=merge_documents(base,current,incoming)
        self.assertEqual(len(result['unresolved']),1)
        self.assertEqual(next(d['path'] for d in result['differences'] if d['conflict']),'/blocks/t/table/rows/0/0')

    def test_table_shape_and_merge_layout_require_whole_table_review(self):
        base=document({'id':'t','type':'table','table':{'rows':[['A','B']],'merges':[]}})
        for mutate in (lambda t:t['rows'].append(['C','D']),lambda t:t['merges'].append({'row':0,'col':0,'rowspan':1,'colspan':2})):
            incoming=deepcopy(base);mutate(incoming['blocks'][0]['table'])
            result=merge_documents(base,base,incoming)
            self.assertEqual(result['merged'],base)
            self.assertEqual(result['differences'][0]['path'],'/blocks/t/table')
            self.assertEqual(result['differences'][0]['kind'],'table_structure')
            self.assertEqual(len(result['unresolved']),1)

    def test_delete_versus_edit_is_conflict_but_delete_unchanged_is_safe(self):
        base=document(block('a','base'));deleted=document();edited=document(block('a','changed'))
        result=merge_documents(base,deleted,edited)
        self.assertEqual(result['merged'],deleted);self.assertEqual(len(result['unresolved']),1)
        diff=result['differences'][0];self.assertFalse(diff['presence']['current'])
        adopted=merge_documents(base,deleted,edited,{diff['id']:{'action':'incoming'}})
        self.assertEqual(adopted['merged'],edited)
        self.assertFalse(merge_documents(base,base,deleted)['unresolved'])
        self.assertEqual(merge_documents(base,base,deleted)['merged'],deleted)

    def test_reorder_and_unknown_split_require_structural_review(self):
        base=document(block('a','A'),block('b','B'))
        for incoming in (document(block('b','B'),block('a','A')),document(block('new1','A1'),block('new2','A2'),block('b','B'))):
            preview=merge_documents(base,base,incoming)
            self.assertEqual(preview['merged'],base);self.assertEqual(preview['differences'][0]['path'],'/blocks')
            self.assertEqual(preview['differences'][0]['kind'],'structure')
            decision={preview['unresolved'][0]:{'action':'incoming'}}
            self.assertEqual(merge_documents(base,base,incoming,decision)['merged'],incoming)

    def test_disjoint_insertions_preserve_anchors_and_same_gap_conflicts(self):
        base=document(block('a','A'),block('b','B'))
        current=document(block('a','A'),block('x','X'),block('b','B'))
        incoming=document(block('a','A'),block('b','B'),block('y','Y'))
        result=merge_documents(base,current,incoming)
        self.assertFalse(result['unresolved']);self.assertEqual([b['id'] for b in result['merged']['blocks']],['a','x','b','y'])
        incoming=document(block('a','A'),block('y','Y'),block('b','B'))
        self.assertTrue(merge_documents(base,current,incoming)['unresolved'])

    def test_issues_source_review_and_opaque_fields_merge_without_time_precedence(self):
        base={'issues':[{'id':'i','message':'Check','resolved':False}],'source_review':{'reason':'old','state':'pending'},'future':{'a':1,'b':2},'time':'old'}
        current=deepcopy(base);current['issues'][0]['resolved']=True;current['future']['a']=3;current['time']='2099'
        incoming=deepcopy(base);incoming['source_review']['reason']='explicit source reason';incoming['future']['b']=4;incoming['time']='1999'
        result=merge_documents(base,current,incoming)
        self.assertTrue(result['merged']['issues'][0]['resolved']);self.assertEqual(result['merged']['future'],{'a':3,'b':4})
        self.assertEqual(result['merged']['source_review']['reason'],'explicit source reason')
        self.assertEqual(result['merged']['time'],'2099');self.assertEqual(len(result['unresolved']),1)

    def test_null_and_absence_are_distinct(self):
        result=merge_documents({'x':None},{},{'x':'text'})
        self.assertEqual(result['merged'],{});self.assertTrue(result['differences'][0]['presence']['base'])
        self.assertFalse(result['differences'][0]['presence']['current'])

    def test_invalid_identities_decisions_and_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):merge_documents(document(block('a','1'),block('a','2')),document(),document())
        with self.assertRaises(ValueError):merge_documents({}, {}, {}, {'unknown':{'action':'incoming'}})
        with self.assertRaises(ValueError):merge_documents({'bad':float('nan')},{},{})
        base=document(block('a','base'));preview=merge_documents(base,document(),document(block('a','other')))
        with self.assertRaises(ValueError):merge_documents(base,document(),document(block('a','other')),{preview['unresolved'][0]:{'action':'edit','value':block('changed-id','bad')}})


    def test_nested_boolean_and_number_changes_are_not_silently_equal(self):
        result=merge_documents({'x':{'value':False}},{'x':{'value':False}},{'x':{'value':0}})
        self.assertEqual(len(result['differences']),1)
        self.assertIs(type(result['merged']['x']['value']),int)

    def test_opaque_future_table_named_field_remains_generic_mapping(self):
        result=merge_documents({'future':{'table':{'a':1,'b':2}}},{'future':{'table':{'a':3,'b':2}}},{'future':{'table':{'a':1,'b':4}}})
        self.assertFalse(result['unresolved']);self.assertEqual(result['merged']['future']['table'],{'a':3,'b':4})

    def test_unchanged_incoming_keeps_human_table_structure_and_order(self):
        base=document({'id':'t','type':'table','table':{'rows':[['A']],'merges':[]}},block('b','text'))
        current=deepcopy(base);current['blocks'][0]['table']['rows'].append(['human addition'])
        self.assertFalse(merge_documents(base,current,base)['unresolved'])
        current['blocks'].reverse()
        result=merge_documents(base,current,base)
        self.assertFalse(result['unresolved']);self.assertEqual(result['merged'],current)

    def test_v2_order_can_change_without_replacing_manual_text_or_table_repairs(self):
        base=document(block('a','source'),{'id':'t','type':'table','table':{'rows':[['12']],'merges':[]}},block('z','end'))
        current=deepcopy(base);current['blocks'][0]['text']='human corrected'
        current['blocks'][1]['table']['rows']=[['14'],['manual row']]
        incoming=deepcopy(base);incoming['blocks']=[incoming['blocks'][2],incoming['blocks'][0],incoming['blocks'][1]]
        preview=merge_documents(base,current,incoming,version=2)
        order=next(d for d in preview['differences'] if d['kind']=='order')
        self.assertEqual(order['current'],['a','t','z'])
        self.assertEqual(order['incoming'],['z','a','t'])
        self.assertEqual(preview['merged'],current)
        applied=merge_documents(base,current,incoming,{order['id']:{'action':'incoming'}},version=2)
        self.assertFalse(applied['unresolved'])
        self.assertEqual([b['id'] for b in applied['merged']['blocks']],['z','a','t'])
        self.assertEqual(applied['merged']['blocks'][1]['text'],'human corrected')
        self.assertEqual(applied['merged']['blocks'][2]['table']['rows'],[['14'],['manual row']])
        self.assertEqual(base['blocks'][1]['table']['rows'],[['12']])

    def test_v2_competing_order_and_text_require_independent_choices(self):
        base=document(block('a','base'),block('b','B'),block('c','C'))
        current=document(block('b','B'),block('a','human'),block('c','C'))
        incoming=document(block('c','C'),block('b','B'),block('a','candidate'))
        preview=merge_documents(base,current,incoming,version=2)
        order=next(d for d in preview['differences'] if d['kind']=='order')
        text=next(d for d in preview['differences'] if d['path']=='/blocks/a/text')
        keep_order={order['id']:{'action':'current'}}
        partial=merge_documents(base,current,incoming,keep_order,version=2)
        self.assertEqual(partial['unresolved'],[text['id']])
        result=merge_documents(base,current,incoming,{**keep_order,text['id']:{'action':'incoming'}},version=2)
        self.assertFalse(result['unresolved'])
        self.assertEqual([b['id'] for b in result['merged']['blocks']],['b','a','c'])
        self.assertEqual(result['merged']['blocks'][1]['text'],'candidate')

    def test_v2_order_edit_cannot_remove_duplicate_replace_or_change_identity(self):
        base=document(block('a','A'),block('b','B'))
        incoming=document(block('b','B'),block('a','A'))
        preview=merge_documents(base,base,incoming,version=2)
        identity=next(d['id'] for d in preview['differences'] if d['kind']=='order')
        for value in (['a'],['a','a'],['a','new'],[block('a','A'),block('b','B')],None,'ab'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'exactly once'):
                merge_documents(base,base,incoming,{identity:{'action':'edit','value':value}},version=2)
        self.assertEqual(merge_documents(base,base,incoming,{identity:{'action':'edit','value':['b','a']}},version=2)['merged'],incoming)

    def test_v2_unknown_replacement_retains_whole_list_decision(self):
        base=document(block('a','A'),block('b','B'))
        incoming=document(block('b','B'),block('x','replacement'))
        old=merge_documents(base,base,incoming)
        new=merge_documents(base,base,incoming,version=2)
        self.assertEqual(old,new)
        self.assertEqual(new['differences'][0]['kind'],'structure')

    def test_version_one_decision_still_means_entire_list_not_order_only(self):
        base=document(block('a','A'),block('b','B'))
        current=document(block('a','human'),block('b','B'))
        incoming=document(block('b','B'),block('a','candidate'))
        preview=merge_documents(base,current,incoming)
        identity=preview['differences'][0]['id']
        decision={identity:{'action':'incoming'}}
        self.assertEqual(merge_documents(base,current,incoming,decision)['merged'],incoming)
        self.assertEqual(merge_documents(base,current,incoming,decision,version=1)['merged'],incoming)
        for version in (True,0,3,'2'):
            with self.subTest(version=version),self.assertRaises(ValueError):
                merge_documents(base,current,incoming,version=version)

    def test_v2_keeps_human_order_when_incoming_unchanged(self):
        base=document(block('a','A'),block('b','B'))
        current=document(block('b','human'),block('a','A'))
        result=merge_documents(base,current,base,version=2)
        self.assertFalse(result['unresolved'])
        self.assertEqual(result['merged'],current)
