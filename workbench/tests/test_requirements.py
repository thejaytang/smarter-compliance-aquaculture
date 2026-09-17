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
from backend.system3.requirements import Requirements, leaves
from backend.shared.sqlite_support import connect
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
    def test_relational_links_preserve_ownership_and_nested_quantity(self):
        uid=self.root()
        self.step('extract',unit_id=uid,field='conditions',**self.span('the water is hot'))
        self.step('extract',unit_id=uid,field='conditions',**self.span('the pump is off'))
        self.step('quantity',unit_id=uid,field='conditions',path=[],quantity=1)
        with self.c.db() as db:
            links=db.execute('SELECT r.owner_id,r.target_id,r.quantities,u.actor,u.material_id FROM requirement_relationships r JOIN requirement_units u ON u.id=r.target_id ORDER BY r.path').fetchall()
            self.assertEqual(len(links),2)
            self.assertTrue(all(row[0]==uid and json.loads(row[2])==[1] and row[3]==ACTOR and row[4]==self.material['id'] for row in links))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        # Reopening the service reuses, rather than duplicates, the projection.
        Requirements(self.c)
        with self.c.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM requirement_relationships').fetchone()[0],2)

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


    def test_multiblock_source_segments_and_independent_staleness(self):
        second=dict(id='second',type='text',text='鱼 shall be checked.\nCheck æ ø å.',source_refs=[{'page':3}])
        self.material['blocks'].append(second)
        d=self.service.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=3,block_ids=['second','b']))['document']
        self.assertEqual(d['text'],TEXT+'\n\n'+second['text'])
        self.assertEqual([p['block_id'] for p in d['source_segments']],['b','second'])
        self.assertFalse(self.service.stale(d,self.material))
        self.material['blocks'][-1]['text']+=' changed'
        self.assertTrue(self.service.stale(d,self.material))

    def test_removed_entry_retains_history_and_can_be_restored(self):
        identity=self.doc['id'];uid=self.root();self.step('delete')
        self.assertEqual(self.service.listing(ACTOR,self.material['id'])['sessions'],[])
        self.assertEqual(self.service.listing(ACTOR,self.material['id'])['deleted'][0]['id'],identity)
        self.assertEqual(self.service.search(ACTOR,uid)['units'],[])
        self.step('undelete')
        self.assertEqual(self.service.search(ACTOR,uid)['units'][0]['id'],uid)
        self.assertEqual([s['action'] for s in self.service.read(ACTOR,identity)['steps']],['undelete','delete','start'])

    def test_parallel_conditions_each_support_recursive_fields_and_children(self):
        root=self.root()
        for phrase in ('the water is hot','the pump is off'):
            self.step('extract',unit_id=root,field='conditions',**self.span(phrase))
        children=self.doc['units'][root]['conditions'][1:]
        for child in children:
            self.step('assign',unit_id=child,field='Subject',start=0,end=3)
            self.step('extract',unit_id=child,field='conditions',start=4,end=len(self.doc['units'][child]['text']))
        self.assertNotEqual(self.doc['units'][children[0]]['conditions'],self.doc['units'][children[1]]['conditions'])
        self.assertEqual(self.doc['units'][root]['conditions'],[2,*children])

    def test_unsaved_batch_never_creates_history_and_explicit_save_replays_once(self):
        uid=self.root();revision=self.doc['revision']
        op=dict(request_id=str(uuid.uuid4()),action='assign',unit_id=uid,field='Subject',start=0,end=9)
        base=dict(request_id=str(uuid.uuid4()),session_id=self.doc['id'],expected_revision=revision,steps=[op])
        preview=self.service.apply(ACTOR,dict(base,action='preview'))['document']
        self.assertEqual(preview['units'][uid]['Subject'],'The human')
        self.assertIsNone(self.service.read(ACTOR,self.doc['id'])['units'][uid]['Subject'])
        self.assertEqual(len(self.service.read(ACTOR,self.doc['id'])['steps']),1)
        save=dict(base,action='save-draft');result=self.service.apply(ACTOR,save)
        self.assertEqual(result,self.service.apply(ACTOR,save))
        self.assertEqual(len(self.service.read(ACTOR,self.doc['id'])['steps']),2)

    def test_save_and_close_validates_and_commits_one_replayable_revision(self):
        uid=self.root()
        request=dict(request_id=str(uuid.uuid4()),action='save-draft',session_id=self.doc['id'],expected_revision=self.doc['revision'],steps=[
            dict(request_id=str(uuid.uuid4()),action='assign',unit_id=uid,field='Subject',start=0,end=9),
            dict(request_id=str(uuid.uuid4()),action='done',unit_id=uid),
            dict(request_id=str(uuid.uuid4()),action='phase',phase='complete')])
        result=self.service.apply(ACTOR,request)
        self.assertEqual(result,self.service.apply(ACTOR,request))
        saved=self.service.read(ACTOR,self.doc['id'])
        self.assertEqual(saved['phase'],'complete')
        self.assertEqual(saved['done'],[uid])
        self.assertEqual(len(saved['steps']),2)
        self.assertEqual(saved['text'],TEXT)

    def test_save_and_close_rejects_an_empty_group_without_partial_history(self):
        uid=self.root();before=self.service.read(ACTOR,self.doc['id'])
        request=dict(request_id=str(uuid.uuid4()),action='save-draft',session_id=self.doc['id'],expected_revision=self.doc['revision'],steps=[
            dict(request_id=str(uuid.uuid4()),action='structure',unit_id=uid,node_id=self.doc['structure_views'][uid]['id'],operation='add-group',start=0,end=9),
            dict(request_id=str(uuid.uuid4()),action='done',unit_id=uid),
            dict(request_id=str(uuid.uuid4()),action='phase',phase='complete')])
        with self.assertRaisesRegex(ValueError,'Complete empty groups'):
            self.service.apply(ACTOR,request)
        self.assertEqual(self.service.read(ACTOR,self.doc['id']),before)
        with self.c.db() as db:self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_new_unsaved_entry_and_recursive_preview_use_stable_ids_without_db_rows(self):
        start=dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=3,block_id='b')
        request=dict(request_id=str(uuid.uuid4()),action='preview',steps=[start])
        first=self.service.apply(ACTOR,request)['document'];second=self.service.apply(ACTOR,request)['document']
        self.assertEqual(first,second)
        self.assertEqual(len(self.service.listing(ACTOR,self.material['id'])['sessions']),1)
        root=next(iter(first['units']));request['steps'].append(dict(request_id=str(uuid.uuid4()),action='extract',unit_id=root,field='conditions',start=34,end=50))
        self.assertEqual(self.service.apply(ACTOR,request),self.service.apply(ACTOR,request))

    def test_batch_reuses_one_source_snapshot_but_rechecks_before_commit(self):
        uid=self.root();calls=[]
        def read(actor,mid):
            calls.append(mid);return deepcopy(self.material)
        self.service.material=read
        edits=[dict(request_id=str(uuid.uuid4()),action='assign',unit_id=uid,field='Subject',start=0,end=9) for _ in range(20)]
        request=dict(request_id=str(uuid.uuid4()),action='preview',session_id=self.doc['id'],expected_revision=self.doc['revision'],steps=edits)
        self.service.apply(ACTOR,request);self.assertEqual(len(calls),1)
        calls.clear();request.update(request_id=str(uuid.uuid4()),action='save-draft')
        self.service.apply(ACTOR,request);self.assertEqual(len(calls),2)

    def test_batch_does_not_commit_if_source_changes_after_preview_snapshot(self):
        calls=[]
        def read(actor,mid):
            calls.append(mid);material=deepcopy(self.material)
            if len(calls)>1:material['blocks'][-1]['text']='Changed original'
            return material
        self.service.material=read
        request=dict(request_id=str(uuid.uuid4()),action='save-draft',session_id=self.doc['id'],expected_revision=self.doc['revision'],steps=[dict(request_id=str(uuid.uuid4()),action='assign',unit_id=self.root(),field='Subject',start=0,end=9)])
        with self.assertRaises(ValueError):self.service.apply(ACTOR,request)
        with self.service.c.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requirement_steps').fetchone()[0],1)
