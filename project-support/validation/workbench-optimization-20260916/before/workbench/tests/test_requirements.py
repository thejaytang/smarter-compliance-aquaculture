"""Isolated source fidelity, quantity semantics, persistence and HTTP contract checks."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import threading
import unittest
import uuid
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from local_workbench.requirements import Requirements, leaves
from local_workbench.sqlite_support import connect
from local_workbench.server import Handler

ACTOR = 'Weijie Tang'
TEXT = 'The human shall remove the fish if the water is hot or the pump is off. Small fish are exempt.'

class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.path=Path(self.temp.name)/'test.sqlite'
        self.material=dict(id='a'*32, revision=3, source={'source_id':'fixture','snapshot_id':'v1','content_hash':'hash'},
            blocks=[dict(id='h',type='heading',text='Chapter 2',level=1),dict(id='b',type='text',text=TEXT,source_refs=[{'page':2}])])
        self.c=SimpleNamespace(db=lambda:connect(self.path),lock=threading.RLock(),read_material=lambda actor,identity:deepcopy(self.material))
        self.service=Requirements(self.c)
        self.doc=self.service.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action='start',material_id='a'*32,material_revision=3,block_id='b'))['document']
    def tearDown(self): self.temp.cleanup()
    def step(self,action,**args):
        r=self.service.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action=action,session_id=self.doc['id'],expected_revision=self.doc['revision'],**args))
        self.doc=r.get('document',self.doc);return r
    def root(self): return next(iter(self.doc['units']))
    def span(self,text):
        source=self.doc['units'][self.root()]['text'];start=source.index(text);return dict(start=start,end=start+len(text))
    def test_document_information_is_not_requirement_intake(self):
        self.material['blocks'][1]['role']='document_information'
        with self.assertRaisesRegex(ValueError,'Select a saved text passage'):
            self.service.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action='start',material_id='a'*32,material_revision=3,block_id='b'))

    def test_exact_range_and_direct_children(self):
        self.assertEqual(leaves([2,'A','B','C']),['A','B','C'])
        self.assertEqual(leaves([[1,2],'A',[3,'B','C','D']]),['A','B','C','D'])
        for bad in ([4,'A','B','C'], [[1,3],'A',[3,'B','C','D']], [True,'A'], [[2,1],'A','B'], [1,'A','A']):
            with self.assertRaises(ValueError):leaves(bad)
    def test_outside_in_and_original_offsets_reopen(self):
        self.step('split',unit_id=self.root(),at=TEXT.index(' Small'))
        ids=list(self.doc['units']);self.assertEqual(''.join(self.doc['units'][x]['text'] for x in ids),TEXT)
        self.step('link',unit_id=ids[0],field='exceptions',target_id=ids[1])
        self.step('phase',phase='fields')
        self.step('assign',unit_id=ids[0],field='Subject',start=0,end=9)
        self.assertEqual(self.doc['units'][ids[0]]['Subject'],'The human')
        saved=Requirements(self.c).read(ACTOR,self.doc['id']);self.assertEqual(saved['units'],self.doc['units']);self.assertFalse(saved['stale'])
        self.assertEqual(saved['source_refs'],[{'page':2}]);self.assertEqual(saved['chapter'],'Chapter 2')
    def test_inline_fields_and_completion_without_phase_navigation(self):
        original=deepcopy(self.material)
        self.step('assign',unit_id=self.root(),field='Subject',**self.span('The human'))
        self.step('extract',unit_id=self.root(),field='conditions',**self.span('the water is hot'))
        self.step('done',unit_id=self.root())
        self.step('phase',phase='complete')
        self.assertEqual(self.doc['phase'],'complete')
        self.assertEqual(self.material,original)
        with self.assertRaises(ValueError):
            self.step('clear',unit_id=self.root(),field='Subject')
        self.step('phase',phase='fields')
        self.step('clear',unit_id=self.root(),field='Subject')
        self.assertNotIn(self.root(),self.doc['done'])
        self.assertIsNone(self.doc['units'][self.root()]['Subject'])

    def test_replay_conflict_and_actor_isolation(self):
        req=dict(request_id=str(uuid.uuid4()),action='phase',session_id=self.doc['id'],expected_revision=1,phase='fields')
        once=self.service.apply(ACTOR,req);self.assertEqual(once,self.service.apply(ACTOR,req))
        stale=self.service.apply(ACTOR,dict(req,request_id=str(uuid.uuid4())));self.assertEqual(stale['status'],'conflict')
        with self.assertRaises(ValueError):self.service.apply(ACTOR,dict(req,phase='relationships'))
        with self.assertRaises(ValueError):self.service.read('Ana Jokic',self.doc['id'])
        self.assertEqual(self.service.search('Ana Jokic','human')['units'],[])
    def test_changed_source_blocks_edits_and_preserves_history(self):
        self.material['blocks'][1]['text']='Changed original'
        self.assertTrue(self.service.read(ACTOR,self.doc['id'])['stale'])
        with self.assertRaises(ValueError):self.step('phase',phase='fields')
        self.assertEqual(self.service.read(ACTOR,self.doc['id'])['text'],TEXT)
    def test_nested_condition_groups_and_restore(self):
        self.step('phase',phase='fields');root=self.root()
        for text in ('the water is hot','the pump is off'):
            self.step('extract',unit_id=root,field='conditions',**self.span(text))
        self.step('quantity',unit_id=root,field='conditions',path=[],quantity=[1,2])
        self.assertEqual(self.doc['units'][root]['conditions'][0],[1,2])
        before=self.doc['revision']
        self.step('group',unit_id=root,field='conditions',path=[],indices=[1,2])
        self.assertIsInstance(self.doc['units'][root]['conditions'][1],list)
        self.step('restore',history_revision=before)
        self.assertEqual(self.doc['units'][root]['conditions'][0],[1,2]);self.assertGreater(self.doc['revision'],before)
    def test_cross_passage_links_and_no_dangling_targets(self):
        target=self.root();old=self.doc
        self.doc=self.service.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action='start',material_id='a'*32,material_revision=3,block_id='b'))['document']
        self.step('link',unit_id=self.root(),field='conditions',target_id=target)
        self.assertIn(target,self.doc['reference_evidence'])
        newer=self.doc;self.doc=old
        with self.assertRaisesRegex(ValueError,'lost'):self.step('split',unit_id=target,at=10)
        with self.assertRaisesRegex(ValueError,'circular'):self.step('link',unit_id=target,field='conditions',target_id=next(iter(newer['units'])))
    def test_finish_requires_explicit_unit_steps_and_keeps_material_unchanged(self):
        original=deepcopy(self.material);self.step('phase',phase='fields')
        with self.assertRaises(ValueError):self.step('phase',phase='complete')
        self.step('assign',unit_id=self.root(),field='Subject',**self.span('The human'))
        self.step('done',unit_id=self.root());self.step('phase',phase='complete')
        self.assertEqual(self.doc['phase'],'complete');self.assertEqual(self.material,original)
    def test_http_session_actor_csrf_and_reopen(self):
        actor=dict(id='fixture',name=ACTOR,token='test')
        app=SimpleNamespace(collaboration=self.c,csrf='csrf',reviewer=False,store=SimpleNamespace(session=lambda token:actor))
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.app=app
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        def request(method,path,body=None,secure=True):
            client=HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            headers={'Content-Type':'application/json'}
            if secure:headers.update(Origin=f'http://127.0.0.1:{server.server_port}',**{'X-CSRF-Token':'csrf'})
            client.request(method,path,json.dumps(body) if body else None,headers);r=client.getresponse();result=(r.status,json.loads(r.read()));client.close();return result
        try:
            body=dict(request_id=str(uuid.uuid4()),action='phase',session_id=self.doc['id'],expected_revision=1,phase='fields')
            self.assertEqual(request('POST','/api/requirements/step',body,False)[0],403)
            self.assertEqual(request('POST','/api/requirements/step',body)[0],200)
            status,doc=request('GET','/api/requirements/session?id='+self.doc['id']);self.assertEqual(status,200);self.assertEqual(doc['phase'],'fields')
        finally:server.shutdown();server.server_close();t.join()

if __name__=='__main__':unittest.main()
