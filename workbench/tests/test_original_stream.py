import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from local_workbench.server import Handler

class OriginalStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.pinned = self.root/'material-originals'; self.pinned.mkdir()
        self.raw = b'%PDF-1.7\n'+b'bound original\n'*80000
        self.hash = hashlib.sha256(self.raw).hexdigest(); self.path = self.pinned/(self.hash+'.pdf'); self.path.write_bytes(self.raw)
        self.result = dict(path=str(self.path), sha256=self.hash, filename='sample.pdf', file_format='pdf', size=len(self.raw))
        self.calls = []
        def call(command, **kw): self.calls.append((command, kw)); return self.result
        self.server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.app = SimpleNamespace(reviewer=False, read_only_restored=True,
            system2=SimpleNamespace(runtime=self.root, call=call),
            store=SimpleNamespace(session=lambda token:{'id':None,'name':''}))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join()
    def get(self, headers=None, path=None):
        conn = HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        conn.request('GET',path or '/api/material/original?id='+'a'*32,headers=headers or {})
        response = conn.getresponse(); result = response.status, response.read(), dict(response.getheaders()); conn.close(); return result
    def test_ranges_full_and_invalid(self):
        status,body,headers = self.get({'Range':'bytes=0-4'}); self.assertEqual((status,body),(206,b'%PDF-'))
        self.assertEqual(headers['Content-Range'],f'bytes 0-4/{len(self.raw)}')
        self.assertEqual(self.get()[1],self.raw)
        self.assertEqual(self.get({'Range':'bytes=-3'})[1],self.raw[-3:])
        for value in ['bytes=-0','bytes=8-4','bytes=999999999-','bytes=0-2,4-6']:
            self.assertEqual(self.get({'Range':value})[:2],(416,b''))
    def test_wrong_hash_or_outside_store_refused(self):
        self.path.write_bytes(b'changed')
        self.assertEqual(self.get()[0],400)
        self.path.write_bytes(self.raw); outside=self.root/self.path.name; outside.write_bytes(self.raw)
        self.result['path']=str(outside); self.assertEqual(self.get()[0],400)
    def test_summary_queries_and_details_forwarded(self):
        self.result={}
        self.get(path='/api/materials?offset=50&limit=50&query=fish')
        self.assertEqual(self.calls[-1],('material_list',{'options':{'offset':50,'limit':50,'query':'fish'}}))
        self.get(path='/api/material/history?id='+'a'*32+'&offset=20&limit=20')
        self.assertEqual(self.calls[-1],('material_history',{'material_id':'a'*32,'options':{'offset':20,'limit':20}}))
        self.get(path='/api/material/candidate?id='+'a'*32+'&candidate_id=fixture')
        self.assertEqual(self.calls[-1],('material_candidate',{'material_id':'a'*32,'candidate_id':'fixture'}))
