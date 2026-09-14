"""HTTP identity, transport and receipt contract; owning ledger tested by System1."""
from hashlib import sha256
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid
from local_workbench.collaboration import Collaboration
from local_workbench.server import Handler
from local_workbench.store import Store

A='Weijie Tang'; B='Ana Jokic'
class SourceIntakeHTTPTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.calls=[];self.original=None
  def call(command,**kwargs):
   self.calls.append((command,kwargs))
   if command=='workflow_intake':
    req=kwargs['request']
    if req.get('upload_path'):
     path=Path(req['upload_path'])
     if sha256(path.read_bytes()).hexdigest()!=req['upload_hash']:raise ValueError('Staged original changed.')
     self.original={'path':str(path),'root':str(path.parent),'hash':req['upload_hash']}
    return {'status':'pending_review','operation_id':'INTAKE-'+req['request_id'],'duplicate_source_id':'TEST001','version_of_source_id':'TEST001'}
   if command=='intake_original':
    if not self.original:raise ValueError('Unknown intake task.')
    return self.original
   raise AssertionError(command)
  self.store=Store(self.root/'workbench.sqlite');self.app=SimpleNamespace(runtime=self.root,store=self.store,csrf='test-csrf',reviewer=False,read_only_restored=False,adapter=SimpleNamespace(call=call),snapshot_time=0)
  self.app.collaboration=Collaboration(self.app)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.app=self.app
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.origin=f'http://127.0.0.1:{self.server.server_port}';self.cookies={}
  for actor in (A,B):
   session=self.store.session('');self.store.select_actor(session['token'],actor);self.cookies[actor]=f"wb_session_{self.server.server_port}={session['token']}"
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
 def request(self,path,method='GET',body=None,actor=A,headers=None):
  fields={'Cookie':self.cookies[actor]} if actor else {}
  if method=='POST':fields.update({'Origin':self.origin,'X-CSRF-Token':self.app.csrf,'Content-Type':'application/json'})
  fields.update(headers or {});data=body if isinstance(body,bytes) else json.dumps(body) if body is not None else None
  c=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  try:
   c.request(method,path,data,fields);r=c.getresponse();return r.status,r.read(),dict(r.getheaders())
  finally:c.close()
 def intake(self,**fields):return {'request_id':str(uuid.uuid4()),'source_title':'Test source','official_url':'https://example.org/source','version':'2099',**fields}
 def upload(self,actor=A):
  status,data,_=self.request('/api/upload','POST',b'%PDF-1.4 test original',actor,{'Content-Type':'application/octet-stream','X-File-Extension':'.pdf'})
  self.assertEqual(status,200);return json.loads(data)
 def test_capability_identity_and_write_transport_protections(self):
  for actor,allowed in ((A,True),(B,False)):
   status,data,_=self.request('/api/sources/intake',actor=actor);self.assertEqual(status,200);value=json.loads(data);self.assertEqual(value['can_register'],allowed);self.assertFalse(value['discovery']['available'])
  for actor,headers in ((None,{}),(B,{}),(A,{'X-CSRF-Token':'wrong'}),(A,{'Origin':'https://untrusted.example'})):
   status,_,_=self.request('/api/sources/intake','POST',self.intake(),actor,headers);self.assertGreaterEqual(status,400)
  self.assertEqual(self.calls,[])
 def test_upload_owner_replay_binding_and_duplicate_receipt(self):
  upload=self.upload(B);req=self.intake(upload_id=upload['upload_id'])
  status,_,_=self.request('/api/sources/intake','POST',req);self.assertGreaterEqual(status,400);self.assertEqual(self.calls,[])
  upload=self.upload();req=self.intake(upload_id=upload['upload_id'])
  status,data,_=self.request('/api/sources/intake','POST',req);self.assertEqual(status,200);result=json.loads(data);self.assertEqual(result['version_of_source_id'],'TEST001')
  self.assertEqual(json.loads(self.request('/api/sources/intake','POST',req)[1]),json.loads(data));self.assertEqual(len(self.calls),1)
  status,_,_=self.request('/api/sources/intake','POST',{**req,'version':'2100'});self.assertGreaterEqual(status,400);self.assertEqual(len(self.calls),1)
  payload=self.calls[0][1]['request'];self.assertEqual(payload['actor'],A);self.assertEqual(payload['upload_hash'],upload['hash']);self.assertEqual(payload['version'],'2099');self.assertNotIn('upload_id',payload)
 def test_original_endpoint_refuses_changed_file_and_anonymous_access(self):
  upload=self.upload();req=self.intake(upload_id=upload['upload_id']);self.assertEqual(self.request('/api/sources/intake','POST',req)[0],200)
  url='/api/sources/intake-original?operation_id=INTAKE-'+req['request_id']
  status,data,headers=self.request(url);self.assertEqual(status,200);self.assertTrue(data.startswith(b'%PDF-'));self.assertTrue(headers['Content-Disposition'].startswith('inline'))
  self.assertGreaterEqual(self.request(url,actor=None)[0],400)
  Path(self.original['path']).write_bytes(b'changed');self.assertGreaterEqual(self.request(url)[0],400)
 def test_upload_metadata_tamper_and_forged_actor_rejected(self):
  upload=self.upload();meta=json.loads((self.root/'uploads'/(upload['upload_id']+'.json')).read_text());Path(meta['path']).write_bytes(b'changed')
  self.assertGreaterEqual(self.request('/api/sources/intake','POST',self.intake(upload_id=upload['upload_id']))[0],400)
  before=len(self.calls);self.assertGreaterEqual(self.request('/api/sources/intake','POST',self.intake(actor=A))[0],400);self.assertEqual(len(self.calls),before)
