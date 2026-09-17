"""Source-only Group connectors across preview, history, projection and exchange."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import threading
import unittest
import uuid
from backend.system3.requirements import Requirements
from backend.system3.requirement_structure import walk, validate, pending, relationship_sides
from backend.system3.requirement_delivery import Delivery
from backend.system3.interpretations import Interpretations, annotations, KEYS
from backend.shared.sqlite_support import connect

ACTOR = 'Weijie Tang'
TEXT = '🐟 Records of animals, including origin and destination. Records including notes.'


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite'
        self.material = dict(id='a'*32, revision=1, source=dict(source_id='demo', snapshot_id='v1', content_hash='abc'), blocks=[dict(id='b', type='text', text=TEXT, source_refs=[{'page':1}])])
        self.c = self.connection(self.path)
        self.r = Requirements(self.c)
        self.doc = self.r.apply(ACTOR, dict(action='start', request_id=str(uuid.uuid4()), material_id=self.material['id'], material_revision=1, block_id='b'))['document']
        self.uid = next(iter(self.doc['units']))

    def connection(self, path):
        c = SimpleNamespace(db=lambda:connect(path), lock=threading.RLock(), read_material=lambda a,i:deepcopy(self.material))
        c.app = SimpleNamespace(runtime=path.parent, collaboration=c)
        return c

    def tearDown(self): self.tmp.cleanup()
    def tree(self): return self.doc['structure_views'][self.uid]
    def nodes(self): return [n for n,_ in walk(self.tree())]
    def node(self, identity): return next(n for n in self.nodes() if n['id']==identity)
    def span(self, word):
        start=TEXT.index(word)
        return dict(start=start,end=start+len(word))
    def step(self, action, **args):
        result=self.r.apply(ACTOR,dict(action=action,request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=self.doc['revision'],**args))
        self.doc=result['document'];return result
    def edit(self, operation, node=None, **args):
        return self.step('structure',unit_id=self.uid,node_id=node or self.tree()['id'],operation=operation,**args)
    def group(self, word, parent=None):
        before={n['id'] for n in self.nodes()}
        self.edit('add-group',parent,**self.span(word))
        return next(n['id'] for n in self.nodes() if n['kind']=='clause' and n['id'] not in before)
    def prepare(self):
        self.owner=self.group(TEXT.split('. ')[0])
        self.before=self.group('🐟 Records of animals',self.owner)
        self.edit('add',self.before,field='Object',**self.span('🐟 Records of animals'))
        for word in ('origin','destination'):
            self.edit('add',self.owner,field='Object',**self.span(word))
        self.after=next(n['id'] for n in self.node(self.owner)['children'] if n['role']=='Object')
        self.edit('quantity',self.after,quantity=2)

    def test_connector_is_source_bound_metadata_with_unchanged_counts(self):
        self.prepare();before=deepcopy(self.node(self.owner)['children'])
        self.edit('relationship',self.owner,**self.span('including'))
        owner=self.node(self.owner)
        self.assertEqual(owner['children'],before)
        self.assertEqual(owner['relationship'],dict(text='including',span=[22,31]))
        self.assertEqual(self.node(self.after)['quantity'],2)
        self.assertEqual(self.doc['structure_schema'],'requirement-structure/2')
        self.assertFalse(pending(self.tree()))
        self.step('done',unit_id=self.uid)
        spans=annotations(self.c,ACTOR,self.material['id'])['spans']
        self.assertEqual([(s['start'],s['end']) for s in spans if s['field']=='relationship'],[(22,31)])
        with self.c.db() as db:
            rel=db.execute('SELECT text,start,end,before_nodes,after_nodes FROM requirement_group_relationships WHERE node_id=?',(self.owner,)).fetchone()
            self.assertEqual(rel[:3],('including',22,31))
            self.assertEqual(json.loads(rel[4]),[self.after])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(Requirements(self.c).read(ACTOR,self.doc['id'])['structures'],self.doc['structures'])

    def test_invalid_owner_connectors_overlaps_and_forged_source_do_not_save(self):
        self.prepare();before=self.r.read(ACTOR,self.doc['id'])
        leaf=next(n['id'] for n in self.nodes() if n['kind']=='fragment')
        for node,word in [(None,'including'),(leaf,'including'),(self.owner,'and')]:
            with self.assertRaises(ValueError):self.edit('relationship',node,**self.span(word))
        # The second identical connector lies outside the selected source Group.
        with self.assertRaises(ValueError):self.edit('relationship',self.owner,start=TEXT.rindex('including'),end=TEXT.rindex('including')+9)
        self.assertEqual(self.r.read(ACTOR,self.doc['id']),before)
        self.edit('relationship',self.owner,**self.span('including'))
        for key,value in [('text','such as'),('span',[0,9])]:
            forged=deepcopy(self.doc)
            node=next(n for n,_ in walk(forged['structures'][self.uid]) if n['id']==self.owner)
            node['relationship'][key]=value
            with self.assertRaises(ValueError):validate(forged)
        with self.assertRaises(ValueError):self.edit('add',self.owner,field='Object',**self.span('including origin'))
        with self.assertRaisesRegex(ValueError,'relationship before degrouping'):
            self.edit('degroup-range',self.owner,**self.span(TEXT.split('. ')[0]))

    def test_preview_save_replay_conflict_removal_and_restore(self):
        self.prepare();old_revision=self.doc['revision']
        operation=dict(action='structure',request_id=str(uuid.uuid4()),unit_id=self.uid,node_id=self.owner,operation='relationship',**self.span('including'))
        req=dict(action='preview',request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=old_revision,steps=[operation])
        preview=self.r.apply(ACTOR,req)['document']
        self.assertEqual(preview['structure_schema'],'requirement-structure/2')
        self.assertEqual(self.r.read(ACTOR,self.doc['id'])['revision'],old_revision)
        with self.c.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_group_relationships').fetchone()[0],0)
        save=dict(req,action='save-draft',request_id=str(uuid.uuid4()))
        first=self.r.apply(ACTOR,save);self.assertEqual(self.r.apply(ACTOR,save),first);self.doc=first['document']
        self.assertEqual(self.r.apply(ACTOR,dict(save,request_id=str(uuid.uuid4())))['status'],'conflict')
        with self.assertRaises(ValueError):self.r.read('Ana Jokic',self.doc['id'])
        saved_revision=self.doc['revision'];children=deepcopy(self.node(self.owner)['children'])
        self.edit('remove-relationship',self.owner)
        self.assertEqual(self.node(self.owner)['children'],children)
        self.assertNotIn('relationship',self.node(self.owner))
        self.step('restore',history_revision=saved_revision)
        self.assertEqual(self.node(self.owner)['relationship']['text'],'including')
        self.edit('remove',self.after)
        self.assertTrue(pending(self.tree()))
        with self.assertRaises(ValueError):self.step('done',unit_id=self.uid)
        self.edit('remove',self.owner)
        with self.c.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_group_relationships').fetchone()[0],0)
        self.step('restore',history_revision=old_revision)
        self.assertEqual(self.doc['structure_schema'],'requirement-structure/1')
        self.assertEqual(self.doc['text'],TEXT)

    def test_wrapping_existing_clauses_moves_their_whole_source_groups(self):
        before=self.group('🐟 Records of animals')
        self.edit('add',before,field='Object',**self.span('🐟 Records of animals'))
        for word in ('origin','destination'):self.edit('add',field='Object',**self.span(word))
        ids={n['id'] for n in self.nodes() if n['kind']=='fragment'}
        outer=self.group(TEXT.split('. ')[0])
        self.assertIn(before,{n['id'] for n,_ in walk(self.node(outer))})
        self.assertEqual(ids,{n['id'] for n in self.nodes() if n['kind']=='fragment'})
        self.edit('relationship',outer,**self.span('including'))
        self.assertTrue(relationship_sides(self.node(outer))['before'])
        self.assertTrue(relationship_sides(self.node(outer))['after'])

    def test_interpretation_fingerprint_and_versioned_exchange_retain_connector(self):
        self.prepare();service=Interpretations(self.c);old_context=service.context(ACTOR,self.uid)
        fields={k:dict(value='',basis='unresolved',references=[],gaps=[]) for k in KEYS}
        self.edit('relationship',self.owner,**self.span('including'))
        ctx=service.context(ACTOR,self.uid)
        self.assertNotEqual(ctx['fingerprint'],old_context['fingerprint'])
        service.save(ACTOR,dict(request_id=str(uuid.uuid4()),unit_id=self.uid,expected_revision=0,context_fingerprint=ctx['fingerprint'],fields=fields))
        saved=service.read(ACTOR,self.uid)
        self.assertFalse(saved['logic']['executable'])
        bundle=Delivery(self.c).capture()[0]['value']
        self.assertEqual(bundle['schema'],'requirement-delivery/3');Delivery(self.c).validate(bundle)
        with self.assertRaises(ValueError):Delivery(self.c).validate(dict(bundle,schema='requirement-delivery/2'))
        peer=self.connection(Path(self.tmp.name)/'peer.sqlite');other=Delivery(peer);request_id=str(uuid.uuid4())
        result=other.apply(bundle,request_id);self.assertEqual(other.apply(bundle,request_id),result)
        restored=Requirements(peer).read(ACTOR,self.doc['id'])
        self.assertEqual(restored['structures'],self.doc['structures'])
        with peer.db() as db:
            self.assertEqual(db.execute('SELECT text FROM requirement_group_relationships').fetchone()[0],'including')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        other.validate(other.capture()[0]['value'])

    def test_same_role_objects_on_both_sides_can_be_grouped_from_existing_marks(self):
        # Operator order: mark Objects, wrap the phrase, group the two examples,
        # then annotate the connecting source word. No invented role is needed.
        for word in ('🐟 Records of animals','origin','destination'):
            self.edit('add',field='Object',**self.span(word))
        self.edit('quantity',self.tree()['children'][0]['id'],quantity=3)
        outer=self.group(TEXT.split('. ')[0])
        after=self.group('origin and destination',outer)
        self.edit('relationship',outer,**self.span('including'))
        sides=relationship_sides(self.node(outer))
        self.assertEqual(len(sides['before']),1)
        self.assertEqual(len(sides['after']),1)
        self.assertEqual(sides['crossing'],[])
        objects=self.node(after)['children'][0]
        self.assertEqual(objects['role'],'Object')
        self.assertEqual(objects['quantity'],2)
        self.assertEqual([n['text'] for n in objects['children']],['origin','destination'])
        self.assertFalse(pending(self.tree()))
