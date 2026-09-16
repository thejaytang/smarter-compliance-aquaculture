"""Isolated persisted archive/task boundaries; no business data or decisions."""
from local_workbench.sqlite_support import connect as connect_sqlite
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
    def db(self):return connect_sqlite(self.runtime/'workflow.sqlite')
    def write(self,m):
        with self.db() as db:
            db.execute('DELETE FROM material_read_index WHERE id=?',(m['id'],));db.execute('DELETE FROM material_documents WHERE id=?',(m['id'],))
            db.execute('INSERT INTO material_read_index VALUES(?,?,?)',(m['id'],m['source']['source_id'],json.dumps(m)));db.execute('INSERT INTO material_documents VALUES(?,?)',(m['id'],json.dumps(m)));db.execute('INSERT INTO material_revision_index VALUES(?,?,?)',(m['id'],m['revision'],json.dumps(m)))
    def create(self):
        r={'material_id':self.material['id'],'archive_revision':2,'request_id':uid(),'scope':['page:1'],'assignee':B,'reason':'Engineering recheck'}
        result=self.q.create(A,r);self.assertEqual(self.q.create(A,r),result);return result['inspection']
    def save(self,t,action='save',**extra):
        return self.q.save(B,{'task_id':t['id'],'material_id':t['material_id'],'expected_revision':t['revision'],'request_id':uid(),'action':action,'note':'Engineering evidence','checked_scope':['page:1'],'explicit_confirmation':True,**extra})['inspection']
    def test_pin_is_persistent_actor_scoped_and_precedes_pagination(self):
        for i in range(55):
            m = deepcopy(self.material)
            m.update(id=f'{i:032x}', title='example' if i == 0 else f'Material {i}', content_status='draft', confirmation=None, last_action={'kind':'opened'})
            self.write(m)
        identity = f'{0:032x}'
        request = {'material_id': identity, 'pinned': True}
        self.assertEqual(self.q.pin(A, request), self.q.pin(A, request))
        self.assertEqual(MaterialQueue(self.c).listing(A, 'pending', limit=1)['materials'][0]['id'], identity)
        self.assertNotEqual(self.q.listing(B, 'pending', limit=1)['materials'][0]['id'], identity)
        self.assertEqual(self.q.listing(A, 'pending', query='Material 54')['materials'][0]['title'], 'Material 54')
        self.q.pin(A, {'material_id':identity,'pinned':False})
        self.assertNotEqual(self.q.listing(A, 'pending', limit=1)['materials'][0]['id'], identity)
        with self.assertRaises(ValueError): self.q.pin(A, {'material_id':'missing','pinned':True})

    def test_task_filter_runs_before_pagination_and_does_not_call_edits_conflicts(self):
        for index in range(58):
            material = deepcopy(self.material)
            material.update(id=f'{index:032x}', revision=1, content_status='not_extracted' if index < 55 else 'draft', confirmation=None, last_action={'kind':'opened'})
            material['source']['source_id'] = f'FILTER{index:03}'
            self.write(material)
        first = self.q.listing(A, 'pending', task_type='first', offset=50)
        self.assertEqual(first['total'], 55)
        self.assertEqual(len(first['materials']), 5)
        review = self.q.listing(A, 'pending', task_type='review')
        self.assertEqual(review['total'], 3)
        self.assertTrue(all(row['queue']['task_type'] == 'review' for row in review['materials']))
        with self.assertRaises(ValueError):
            self.q.listing(A, 'pending', task_type='conflict')

    def test_inspection_filter_preserves_the_archived_material(self):
        task = self.create()
        pending = self.q.listing(A, 'pending', task_type='inspection')
        self.assertEqual(pending['total'], 1)
        self.assertEqual(pending['materials'][0]['queue']['open_inspections'][0]['id'], task['id'])
        self.assertEqual(self.q.listing(A, 'pending', task_type='review')['total'], 0)
        self.assertEqual(self.q.listing(A, 'archive')['total'], 1)

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

    def test_empty_partial_candidate_stays_pending_and_retains_extraction_summary(self):
        summary={'id':'empty-candidate','status':'partial','complete':False,'block_count':1,
            'extraction':{'parser_status':'empty','processed_scope_count':2,'usable_scope_count':0,'unprocessed_scope_count':0,'unresolved_count':2}}
        with self.db() as db: db.execute('INSERT INTO material_candidate_index VALUES(?,?)',(self.material['id'],json.dumps(summary)))
        pending=self.q.listing(A,'pending')
        self.assertEqual(pending['materials'][0]['candidates'][0],summary)
        self.assertFalse(pending['materials'][0]['queue']['archive_current'])
        self.assertEqual(self.q.listing(A,'archive')['materials'][0]['revision'],2)

    def test_failed_candidate_is_visible_until_resolved_without_losing_prior_archive(self):
        failed={'id':'failed-candidate','status':'failed','error':'Isolated failure','block_count':0}
        with self.db() as db: db.execute('INSERT INTO material_candidate_index VALUES(?,?)',(self.material['id'],json.dumps(failed)))
        pending=self.q.listing(A,'pending')
        self.assertEqual(pending['total'],1)
        self.assertEqual(pending['materials'][0]['candidates'][0]['error'],'Isolated failure')
        self.assertEqual(self.q.listing(A,'archive')['total'],1)
        with self.db() as db: db.execute('UPDATE material_candidate_index SET data=?',(json.dumps(dict(failed,status='kept')),))
        self.assertEqual(self.q.listing(A,'pending')['total'],0)
        self.assertEqual(self.q.listing(A,'archive')['materials'][0]['candidates'][0]['status'],'kept')

    def test_replaced_original_has_one_current_queue_entry_and_retained_history(self):
        old=deepcopy(self.material);new=deepcopy(old)
        new.update(id='b'*32,revision=0,content_status='not_extracted',confirmation=None,blocks=[])
        old.update(source_stale=True,newer_material_id=new['id'])
        self.write(old);self.write(new)
        rows=self.q.listing(A,'pending')['materials']
        self.assertEqual([r['id'] for r in rows],[new['id']])
        # Source observation may mark the old version stale before opening its successor.
        old.pop('newer_material_id');self.write(old)
        self.assertEqual([r['id'] for r in self.q.listing(A,'pending')['materials']],[new['id']])
        self.assertEqual(self.app.system2.call('material_read',material_id=old['id'])['id'],old['id'])
        with self.db() as db:db.execute('DELETE FROM material_read_index WHERE id=?',(new['id'],))
        self.assertEqual(self.q.listing(A,'pending')['materials'][0]['id'],old['id'])

    def test_unchanged_empty_personal_copy_is_not_labelled_saved_work(self):
        material=deepcopy(self.material)
        material.update(revision=0,content_revision=0,content_status='not_extracted',confirmation=None,blocks=[],last_action={'kind':'opened'})
        self.write(material)
        workspace={'id':uid(),'actor':A,'material_id':material['id'],'source_id':'TS001','base_material':deepcopy(material)}
        runtime=self.c.workspace_runtime(workspace);runtime.mkdir(parents=True)
        with connect_sqlite(runtime/'workflow.sqlite') as db:
            db.executescript('CREATE TABLE material_read_index(id TEXT,data TEXT);CREATE TABLE material_documents(id TEXT,data TEXT);CREATE TABLE material_candidate_index(material_id TEXT,data TEXT);')
            raw=json.dumps(material)
            db.execute('INSERT INTO material_read_index VALUES(?,?)',(material['id'],raw));db.execute('INSERT INTO material_documents VALUES(?,?)',(material['id'],raw))
        self.c.put('workspace',A+':'+material['id'],workspace)
        row=self.q.listing(A,'pending')['materials'][0]
        self.assertEqual(row['collaboration_view'],'master')
        self.assertEqual(row['content_status'],'not_extracted')
        self.assertFalse(row['queue']['personal_changes'])

    def test_personal_confirmation_never_becomes_new_master_confirmation_in_queue(self):
        workspace={'id':uid(),'actor':A,'material_id':self.material['id'],'source_id':'TS001','base_material':deepcopy(self.material)}
        runtime=self.c.workspace_runtime(workspace);runtime.mkdir(parents=True)
        with connect_sqlite(runtime/'workflow.sqlite') as db:
            db.executescript('CREATE TABLE material_read_index(id TEXT,data TEXT);CREATE TABLE material_documents(id TEXT,data TEXT);CREATE TABLE material_candidate_index(material_id TEXT,data TEXT);')
            raw=json.dumps(self.material)
            db.execute('INSERT INTO material_read_index VALUES(?,?)',(self.material['id'],raw));db.execute('INSERT INTO material_documents VALUES(?,?)',(self.material['id'],raw))
        self.c.put('workspace',A+':'+self.material['id'],workspace)
        master=deepcopy(self.material);master.update(revision=3,content_revision=2,confirmation=None,content_status='draft',last_action={'kind':'collaboration_adopted'});self.write(master)
        row=self.q.listing(A,'pending')['materials'][0]
        self.assertEqual(row['collaboration_view'],'personal');self.assertEqual(row['content_status'],'content_review_complete')
        self.assertEqual(row['queue']['master_revision'],3);self.assertEqual(row['queue']['master_content_status'],'draft');self.assertFalse(row['queue']['master_review_current'])
        self.assertEqual(row['confirmation'],self.material['confirmation']);self.assertEqual(self.q.read_archive(A,master['id'])['revision'],2)

    def test_task_receipt_summary_and_download_catalogue_include_existing_material_receipts(self):
        from local_workbench.collaboration_collection import Collection
        material={'request_id':uid(),'submission_id':uid(),'status':'adopted','actor':A}
        task={'id':uid(),'item_id':uid(),'status':'adopted','actor':A}
        self.c.put('adoption_receipt',material['request_id'],material);self.c.put('collection_adoption',task['id'],task)
        collection=Collection(self.c)
        self.assertEqual(collection.catalogue(A)['receipts'],[material,task])
        self.assertEqual({i['key'] for i in collection.receipt_catalogue(A)['items']},{material['request_id'],task['id']})
        self.assertEqual(self.c.all('adoption_receipt'),[material]);self.assertEqual(self.c.all('collection_adoption'),[task])

    def test_receipt_choices_identify_saved_material_contributor_and_adopted_revision(self):
        from local_workbench.collaboration_collection import Collection
        receipt={'request_id':uid(),'submission_id':uid(),'status':'adopted','actor':A,'contributor':B,'at':'2026-09-13T10:00:00Z',
            'material':{'id':self.material['id'],'source':{'source_id':'PA001'},'title':'PA001','revision':3}}
        self.c.put('adoption_receipt',receipt['request_id'],receipt)
        # Labels must describe the retained receipt, even when the current master differs.
        master=deepcopy(self.material);master.update(revision=99,title='New title');self.write(master)
        choice=Collection(self.c).receipt_catalogue(A)['items'][0]
        self.assertEqual(choice['title'],'PA001 · Ana Jokic · adopted · master revision 3 · 2026-09-13T10:00:00Z')
        self.assertEqual(choice['key'],receipt['request_id']);self.assertEqual(choice['evidence_id'],receipt['request_id'])
        self.assertNotIn(receipt['submission_id'],choice['title']);self.assertEqual(self.c.all('adoption_receipt'),[receipt])
        fallback={'id':uid(),'item_id':uid(),'status':'adopted','actor':A}
        self.c.put('collection_adoption',fallback['id'],fallback)
        self.assertEqual(Collection(self.c).receipt_catalogue(A)['items'][1]['title'],'Receipt '+fallback['id']+' · adopted')
