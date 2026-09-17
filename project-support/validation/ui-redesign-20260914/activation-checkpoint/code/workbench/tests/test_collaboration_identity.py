"""Failure injection at collaboration journal boundaries; owning calls are recorded fakes."""
from copy import deepcopy
from pathlib import Path
import tempfile
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

from local_workbench.collaboration import Collaboration, fingerprint, source_review
from local_workbench.collaboration_exchange import pack


class CollaborationIdentityTests(unittest.TestCase):
    def test_interrupted_source_adoption_reserves_uuid_against_different_material_merge(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime=Path(temporary)
            material={'id':'material-two','revision':0,'source':{'content_hash':'hash'},'blocks':[],'issues':[]}
            writes=[]
            def material_call(command,**kwargs):
                if command=='material_read':return deepcopy(material)
                writes.append(kwargs['request'])
                return {'status':'applied','material':dict(material,revision=1)}
            owner=Mock()
            owner.call.side_effect=lambda command,**kw:{'status':'applied','request_id':kw['request']['request_id']}
            app=SimpleNamespace(runtime=runtime,adapter=owner,
                system2=SimpleNamespace(call=material_call,runtime=runtime/'system2-workflow'),snapshot_time=0)
            c=Collaboration(app)
            sources={sid:{'source_id':sid,'source_revision':'r0','content_hash':'hash','effective_selection':'INCLUDE'}
                     for sid in ('TS001','TS002')}
            c.source=lambda sid:deepcopy(sources[sid])
            for i,sid in enumerate(sources):
                mid=None if i==0 else material['id'];identity=str(uuid.uuid4());merge_id='merge-'+str(i)
                c.put('submission',identity,{'id':identity,'actor':'Ana Jokic','material':material if mid else None,'base_digest':'known'})
                c.put('merge',merge_id,{'id':merge_id,'actor':'Weijie Tang','status':'preview',
                    'submission_id':identity,'source_id':sid,'material_id':mid,'current_source':sources[sid],
                    'source_digest':fingerprint(sources[sid]),'master_digest':fingerprint(material) if mid else fingerprint(None),
                    'decisions':{}})
            def view(merge):
                review=source_review(merge['current_source'])
                if merge['id']=='merge-0':review['note']='Source-only adoption before interrupted final journal write.'
                return {'unresolved':[],'source_review':review,'material':deepcopy(material),'provenance':[]}
            c.merge_view=view
            with c.db() as db:
                db.execute("CREATE TRIGGER interrupt_final BEFORE INSERT ON collaboration_objects WHEN NEW.kind='merge' AND json_extract(NEW.data,'$.status')='adopted' BEGIN SELECT RAISE(ABORT,'Injected process interruption'); END")
            rid=str(uuid.uuid4())
            with self.assertRaises(sqlite3.IntegrityError):
                c.adopt('Weijie Tang',{'merge_id':'merge-0','request_id':rid})
            with c.db() as db:db.execute('DROP TRIGGER interrupt_final')
            self.assertTrue(c.get('merge','merge-0').get('source_receipt'))
            self.assertIsNone(c.get('adoption_receipt',rid))
            self.assertEqual(c.get('merge','merge-0')['adoption_request_id'],rid)
            submission=c.get('submission',c.get('merge','merge-0')['submission_id'])
            self.assertEqual(submission['adoption_merge_id'],'merge-0')
            with self.assertRaisesRegex(ValueError,'bound|identity'):
                c.adopt('Weijie Tang',{'merge_id':'merge-1','request_id':rid})
            self.assertEqual(writes,[])
            self.assertIsNone(c.get('merge','merge-1').get('material_request'))
            result=c.adopt('Weijie Tang',{'merge_id':'merge-0','request_id':rid})
            self.assertEqual(result['status'],'adopted')
            self.assertEqual(owner.call.call_count,1)
            self.assertEqual(c.adopt('Weijie Tang',{'merge_id':'merge-0','request_id':rid}),result)

    def test_bad_source_evidence_rejected_before_catalog_or_material_write(self):
        for evidence in ([], {'source_open_issues':'wrong'}, {'source_open_issues':[None]},
                         {'source_open_issues':[{'source_id':'TS998','reason':'Different source'}]}):
            with self.subTest(evidence=evidence),tempfile.TemporaryDirectory() as temporary:
                runtime=Path(temporary);owner=Mock(runtime=runtime/'system2-workflow')
                c=Collaboration(SimpleNamespace(runtime=runtime,system2=owner),reviewer=True)
                source={'source_id':'TS999','source_title':'Isolated unfinished source',
                        'snapshot_status':'NOT_COLLECTED','effective_selection':'PENDING'}
                metadata={'id':str(uuid.uuid4()),'actor':'Weijie Tang','source_id':'TS999','material_id':None,
                    'source':source,'material':None,'history':[],'original':None,'source_evidence':evidence,
                    'source_review':source_review(source),'base_digest':fingerprint({'source':source,'material':None})}
                with self.assertRaises(ValueError):c.import_package('Ana Jokic',pack('work',metadata,{}))
                for kind in ('source_catalog','material_catalog','work','package_receipt'):
                    self.assertEqual(c.all(kind),[])
                owner.call.assert_not_called()


class OwnPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();runtime=Path(self.temporary.name)
        self.source={'source_id':'TS001','source_revision':'r1','source_title':'Isolated source','content_hash':'hash','effective_selection':'INCLUDE'}
        self.material={'id':'material','revision':0,'content_revision':0,'source':{'source_id':'TS001','snapshot_id':'v1','content_hash':'hash'},'blocks':[],'issues':[]}
        self.exported={'material':deepcopy(self.material),'history':[deepcopy(self.material)]}
        self.base=deepcopy(self.material)
        def call(command,**kwargs):
            if command=='material_read':return deepcopy(self.material)
            if command=='material_validate':return {'status':'valid'}
            raise AssertionError(command)
        self.app=SimpleNamespace(runtime=runtime,system2=SimpleNamespace(runtime=runtime/'system2',call=call))
        self.c=self.collaboration()
    def tearDown(self):self.temporary.cleanup()
    def collaboration(self):
        c=Collaboration(self.app);c.source=lambda sid:deepcopy(self.source);c.source_issues=lambda sid:[]
        c.workspace=lambda actor,mid:{'source_id':'TS001','base_material':deepcopy(self.base),'base_source':deepcopy(self.source),'runtime':str(self.app.runtime/'personal')}
        c.workspace_runtime=lambda workspace:Path(workspace['runtime'])
        c.adapter=lambda runtime:SimpleNamespace(call=lambda command,**kw:deepcopy(self.exported))
        return c
    def test_repeat_and_restart_preserve_one_submission_and_preview_choices(self):
        actor='Weijie Tang';review=source_review(self.source);review['note']='Engineering saved proposal'
        self.c.save_source(actor,{'source_id':'TS001','expected_revision':0,'source_review':review})
        first=self.c.prepare_own(actor,{'source_id':'TS001'})
        difference=next(d for d in first['differences'] if d['path']=='/source_review/note')
        self.c.resolve(actor,{'merge_id':first['merge_id'],'decisions':{difference['id']:{'action':'current'}}})
        repeated=self.c.prepare_own(actor,{'source_id':'TS001'})
        restarted=self.collaboration().prepare_own(actor,{'source_id':'TS001'})
        self.assertEqual(first['submission_id'],repeated['submission_id']);self.assertEqual(first['merge_id'],restarted['merge_id'])
        self.assertEqual(restarted['source_review']['note'],'');self.assertEqual(len(self.c.all('submission')),1);self.assertEqual(len(self.c.all('merge')),1)
    def test_response_loss_after_submission_does_not_create_another_pending_item(self):
        original=self.c.preview
        self.c.preview=lambda *args,**kwargs:(_ for _ in ()).throw(OSError('Isolated interrupted response'))
        with self.assertRaises(OSError):self.c.prepare_own('Weijie Tang',{'source_id':'TS001','material_id':'material'})
        self.assertEqual(len(self.c.all('submission')),1)
        self.c.preview=original
        result=self.c.prepare_own('Weijie Tang',{'source_id':'TS001','material_id':'material'})
        self.assertEqual(result['submission_id'],self.c.all('submission')[0]['id']);self.assertEqual(len(self.c.all('submission')),1)
        self.exported['material']['revision']=1;self.exported['material']['content_revision']=1
        self.exported['material']['blocks']=[{'id':'b','type':'text','text':'New saved human version'}]
        self.exported['history'].append(deepcopy(self.exported['material']))
        newer=self.c.prepare_own('Weijie Tang',{'source_id':'TS001','material_id':'material'})
        self.assertNotEqual(newer['submission_id'],result['submission_id']);self.assertEqual(len(self.c.all('submission')),2)
    def test_master_change_creates_new_comparison_without_copying_old_choices(self):
        actor='Weijie Tang';first=self.c.prepare_own(actor,{'source_id':'TS001'})
        self.source['source_revision']='r2'
        second=self.c.preview(actor,{'submission_id':first['submission_id']})
        self.assertNotEqual(first['merge_id'],second['merge_id']);self.assertEqual(len(self.c.all('submission')),1)
        self.assertEqual(self.c.get('merge',second['merge_id'])['decisions'],{})
        self.assertEqual(self.c.get('merge',first['merge_id'])['current_source']['source_revision'],'r1')
    def test_legacy_identical_pending_submission_is_reused(self):
        actor='Weijie Tang';metadata=self.c._submission(actor,{'source_id':'TS001'})
        self.c._import_submission(metadata);first=self.c.preview(actor,{'submission_id':metadata['id']})
        repeated=self.c.prepare_own(actor,{'source_id':'TS001'})
        self.assertEqual(first['submission_id'],repeated['submission_id']);self.assertEqual(first['merge_id'],repeated['merge_id']);self.assertEqual(len(self.c.all('submission')),1)
