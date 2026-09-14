"""Isolated persisted archive/task boundaries; no business data or decisions."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import sqlite3
import tempfile
import unittest
import uuid
from local_workbench.collaboration import Collaboration
from local_workbench.material_queue import MaterialQueue

A='Weijie Tang'; B='Ana Jokic'
def uid():return str(uuid.uuid4())

class MaterialQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.runtime=self.root/'s2';self.runtime.mkdir()
        self.material={'id':'a'*32,'title':'Engineering fixture','revision':2,'content_revision':1,
            'source':{'source_id':'TS001','content_hash':'b'*64,'snapshot_id':'v1'},'source_stale':False,
            'scope':[{'id':'page:1'},{'id':'page:2'}],'checked_scope':['page:1','page:2'],'blocks':[], 'issues':[],
            'content_status':'content_review_complete','confirmation':{'actor':A,'content_revision':1,'source_hash':'b'*64},
            'last_action':{'kind':'content_confirmed'}}
        with self.db() as db:
            db.executescript('CREATE TABLE material_read_index(id TEXT,source_id TEXT,data TEXT);CREATE TABLE material_documents(id TEXT,data TEXT);CREATE TABLE material_revision_index(material_id TEXT,revision INTEGER,data TEXT);CREATE TABLE material_candidate_index(material_id TEXT,data TEXT);')
        self.write(self.material)
        def call(command,**kw):
            if command=='material_list':return {'sources':[],'materials':[],'counts':{}}
            if command=='material_read':
                with self.db() as db:
                    r=db.execute('SELECT data FROM material_revision_index WHERE material_id=? AND revision=?',(kw['material_id'],kw['revision'])).fetchone() if kw.get('revision') is not None else db.execute('SELECT data FROM material_read_index WHERE id=?',(kw['material_id'],)).fetchone()
                if not r: raise ValueError('material_revision_not_found')
                return json.loads(r[0])
            raise AssertionError(command)
        self.app=SimpleNamespace(runtime=self.root,system2=SimpleNamespace(runtime=self.runtime,call=call),adapter=SimpleNamespace(call=lambda *a,**k:{'tasks':[]}))
        self.c=Collaboration(self.app);self.q=MaterialQueue(self.c)
    def tearDown(self):self.tmp.cleanup()
    def db(self):return sqlite3.connect(self.runtime/'workflow.sqlite')
    def write(self,m):
        with self.db() as db:
            db.execute('DELETE FROM material_read_index WHERE id=?',(m['id'],));db.execute('DELETE FROM material_documents WHERE id=?',(m['id'],))
            db.execute('INSERT INTO material_read_index VALUES(?,?,?)',(m['id'],m['source']['source_id'],json.dumps(m)));db.execute('INSERT INTO material_documents VALUES(?,?)',(m['id'],json.dumps(m)));db.execute('INSERT INTO material_revision_index VALUES(?,?,?)',(m['id'],m['revision'],json.dumps(m)))
    def create(self):
        r={'material_id':self.material['id'],'archive_revision':2,'request_id':uid(),'scope':['page:1'],'assignee':B,'reason':'Engineering recheck'}
        result=self.q.create(A,r);self.assertEqual(self.q.create(A,r),result);return result['inspection']
    def save(self,t,action='save',**extra):
        return self.q.save(B,{'task_id':t['id'],'material_id':t['material_id'],'expected_revision':t['revision'],'request_id':uid(),'action':action,'note':'Engineering evidence','checked_scope':['page:1'],'explicit_confirmation':True,**extra})['inspection']
    def test_archive_is_master_confirmation_and_sampling_does_not_remove_it(self):
        self.assertEqual(self.q.listing(A,'pending')['total'],0);self.assertEqual(self.q.listing(A,'archive')['total'],1)
        before=self.app.system2.call('material_read',material_id=self.material['id']);t=self.create()
        self.assertEqual(self.q.listing(A,'pending')['total'],1);self.assertTrue(self.q.listing(A,'pending')['materials'][0]['queue']['inspection_only'])
        self.assertEqual(self.q.listing(A,'archive')['total'],1);self.assertEqual(self.app.system2.call('material_read',material_id=self.material['id']),before)
        self.save(t,'pass');self.assertEqual(self.q.listing(A,'pending')['total'],0)
    def test_restart_partial_progress_and_history_are_preserved(self):
        t=self.save(self.create(),checked_scope=[])
        restored=MaterialQueue(Collaboration(self.app));self.assertEqual(restored.tasks()[0],t)
        with self.assertRaisesRegex(ValueError,'complete selected scope'):self.save(t,'pass',checked_scope=[])
        done=self.save(t,'pass');self.assertEqual(len(done['history']),2)
        self.assertEqual(restored.tasks()[0]['status'],'passed')
    def test_new_draft_preserves_old_archive_and_old_checks_cannot_pass_new_archive(self):
        t=self.create();m=deepcopy(self.material);m.update(revision=3,content_revision=2,confirmation=None,content_status='draft',last_action={'kind':'collaboration_adopted'});self.write(m)
        self.assertEqual(self.q.listing(A,'archive')['materials'][0]['revision'],2)
        self.assertEqual(self.q.listing(A,'pending')['total'],1)
        m.update(revision=4,content_status='content_review_complete',confirmation={'actor':A,'content_revision':2},last_action={'kind':'content_confirmed'});self.write(m)
        with self.assertRaisesRegex(ValueError,'newer archived version'):self.save(t,'pass')
        self.assertEqual(self.q.tasks()[0]['status'],'pending')
        old=self.save(t,'restart');self.assertEqual(old['status'],'superseded')
        replacement=self.q.tasks()[1];self.assertEqual(replacement['archive_revision'],4);self.assertEqual(replacement['checked_scope'],[])
        self.assertEqual(self.q.listing(A,'pending')['materials'][0]['queue']['open_inspections'][0]['id'],replacement['id'])
    def test_finding_blocks_new_acceptance_until_explicit_recheck_resolution(self):
        t=self.save(self.create(),'finding')
        with self.assertRaisesRegex(ValueError,'open archive inspection'):self.c.confirm_master(A,{'material_id':t['material_id']})
        with self.assertRaisesRegex(ValueError,'Master changed'):self.save(t,'resolve',expected_master_revision=99,checked_scope=['page:1','page:2'])
        done=self.save(t,'resolve',expected_master_revision=2,checked_scope=['page:1','page:2']);self.assertEqual(done['status'],'resolved')
        self.assertEqual(self.q.listing(A,'pending')['total'],0)
    def test_identity_actor_stale_revision_and_request_reuse_are_rejected(self):
        t=self.create()
        with self.assertRaisesRegex(ValueError,'identity'):self.save(t,material_id='other')
        with self.assertRaisesRegex(ValueError,'changed'):self.save(t,expected_revision=3)
        r={'task_id':t['id'],'material_id':t['material_id'],'expected_revision':0,'request_id':uid(),'action':'save','note':'one','checked_scope':[]}
        with self.assertRaisesRegex(ValueError,'another reviewer'):self.q.save('Daniel Restad',r)
        r['request_id']=uid();one=self.q.save(B,r);self.assertEqual(self.q.save(B,r),one)
        with self.assertRaisesRegex(ValueError,'identity'):self.q.save(B,dict(r,note='different'))
    def test_source_stale_cannot_pass_but_archive_remains(self):
        t=self.create();m=deepcopy(self.material);m.update(revision=3,source_stale=True,last_action={'kind':'source_changed'});self.write(m)
        self.assertEqual(self.q.archives()[m['id']]['revision'],2)
        with self.assertRaisesRegex(ValueError,'Source changed'):self.save(t,'pass')
        self.assertEqual(self.q.listing(A,'archive')['total'],1)
    def test_scope_and_archive_creation_guard_do_not_guess(self):
        r={'material_id':self.material['id'],'archive_revision':1,'request_id':uid(),'scope':['unknown'],'reason':'check'}
        with self.assertRaises(ValueError):self.q.create(A,r)
        self.assertEqual(self.q.tasks(),[])
        with self.assertRaises(ValueError):self.q.read_archive(A,self.material['id'],99)
    def test_search_and_pagination_apply_after_category_filter(self):
        for i in range(55):
            m=deepcopy(self.material);m.update(id=str(i),title='Draft '+str(i),content_status='draft',confirmation=None,last_action={'kind':'saved'});self.write(m)
        self.assertEqual(self.q.listing(A,'pending',offset=50)['total'],55);self.assertEqual(len(self.q.listing(A,'pending',offset=50)['materials']),5)
        self.assertEqual(self.q.listing(A,'archive',query='Engineering')['total'],1)
        self.assertEqual(self.q.listing(A,'pending',query='Engineering')['total'],0)
