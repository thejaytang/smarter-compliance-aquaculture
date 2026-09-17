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
