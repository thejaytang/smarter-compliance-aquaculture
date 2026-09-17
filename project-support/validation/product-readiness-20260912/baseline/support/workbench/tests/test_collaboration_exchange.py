from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid
from local_workbench.collaboration_exchange import pack, unpack, segment
from local_workbench.collaboration_package import build_package
from local_workbench.collaboration import Collaboration, fingerprint


class ExchangeTests(unittest.TestCase):
    def test_large_history_payload_roundtrips_without_large_manifest(self):
        metadata={'id':str(uuid.uuid4()),'history':[{'text':'工程 norsk ø'*300000}]}
        result=unpack(pack('work',metadata,{'original.html':b'original'}))
        self.assertEqual(result['metadata'],metadata)
        self.assertEqual(result['files'],{'original.html':b'original'})

    def test_payload_wrong_identity_and_duplicate_json_keys_rejected(self):
        identity=str(uuid.uuid4());wrapper={'id':identity,'payload':'review.json'}
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            unpack(build_package('work',wrapper,{'review.json':json.dumps({'id':str(uuid.uuid4())}).encode()}))
        with self.assertRaisesRegex(ValueError,'invalid_manifest'):
            unpack(build_package('work',wrapper,{'review.json':('{"id":"'+identity+'","id":"'+identity+'"}').encode()}))

    def test_portable_segments_reject_traversal_and_windows_aliases(self):
        for value in ('../../escaped','../','..','.','CON','nul.txt','C:drive','x\\y','/root','trailing.','trailing ','x/y'):
            with self.subTest(value=value),self.assertRaises(ValueError):segment(value)
        self.assertEqual(segment('材料 ø.html'),'材料 ø.html')

    def test_import_cannot_create_source_folder_outside_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'workspace';runtime=root/'runtime';runtime.mkdir(parents=True)
            app=SimpleNamespace(runtime=runtime,system2=Mock(runtime=runtime/'system2-workflow'))
            collaboration=Collaboration(app,reviewer=True)
            collaboration._write_reviewer_catalog=Mock()
            raw=b'isolated original'
            source={'source_id':'TS999','content_hash':sha256(raw).hexdigest(),
                'snapshot_id':'TS999-001','file_format':'html',
                'folder_code':'../../../../escaped','stored_filename':'original.html'}
            metadata={'id':str(uuid.uuid4()),'actor':'Weijie Tang','source_id':'TS999',
                'source':source,'material':None,'original':'original.html'}
            metadata['base_digest']=fingerprint({'source':source,'material':None})
            blob=pack('work',metadata,{'original.html':raw})
            with self.assertRaises(ValueError):collaboration.import_package('Weijie Tang',blob)
            self.assertFalse((root/'escaped').exists())
            self.assertEqual(collaboration.all('package_receipt'),[])
            self.assertEqual(collaboration.all('source_catalog'),[])
            app.system2.call.assert_not_called()
            metadata['id']=str(uuid.uuid4())
            source['folder_code']='材料 ø';source['stored_filename']='Original ø.html'
            metadata['base_digest']=fingerprint({'source':source,'material':None})
            blob=pack('work',metadata,{'original.html':raw})
            self.assertEqual(collaboration.import_package('Weijie Tang',blob)['status'],'imported')
            self.assertEqual(collaboration.import_package('Weijie Tang',blob)['status'],'already_imported')
            saved=collaboration.root/'originals'/metadata['id']/'材料 ø'/'Original ø.html'
            self.assertEqual(saved.read_bytes(),raw)
            self.assertEqual(len(collaboration.all('package_receipt')),1)

    def test_submission_file_injection_refused_before_source_processing(self):
        with tempfile.TemporaryDirectory() as temporary:
            app=SimpleNamespace(runtime=Path(temporary),system2=Mock())
            collaboration=Collaboration(app)
            blob=pack('submission',{'id':str(uuid.uuid4()),'actor':'Weijie Tang'}, {'original.html':b'replacement'})
            with self.assertRaisesRegex(ValueError,'cannot contain or replace'):
                collaboration.import_package('Weijie Tang',blob)
            app.system2.call.assert_not_called()
            self.assertEqual(collaboration.all('package_receipt'),[])
