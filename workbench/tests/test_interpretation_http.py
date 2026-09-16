"""Real HTTP lineage, actor binding and rejected rule writes."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from local_workbench.server import Handler

class InterpretationHTTPTests(unittest.TestCase):
 def setUp(self):
  from test_interpretations import InterpretationTests
  self.fixture=InterpretationTests();self.fixture.setUp()
  self.actor={'id':'test-actor','name':'Weijie Tang','token':'test'}
  self.app=self.fixture.c.app;self.app.csrf='synthetic-csrf';self.app.reviewer=False
  self.app.store=SimpleNamespace(session=lambda token:self.actor)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.app=self.app
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.fixture.tearDown()
 def call(self,path,body=None,csrf=True):
  connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{self.server.server_port}'}
  if csrf:headers['X-CSRF-Token']=self.app.csrf
  connection.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),headers)
  response=connection.getresponse();result=response.status,json.loads(response.read());connection.close();return result
 def test_save_trace_actor_boundary_and_source_version(self):
  status,saved=self.call('/api/interpretations/save',self.fixture.request());self.assertEqual(status,200)
  path='/api/interpretations/trace?unit_id='+self.fixture.uid+'&revision=1'
  status,trace=self.call(path);self.assertEqual(status,200);self.assertEqual(trace['source']['content_hash'],'v1')
  self.actor['name']='Ana Jokic';self.assertEqual(self.call(path)[0],400)
 def test_invalid_rule_never_becomes_saved_data_and_origin_is_enforced(self):
  request=self.fixture.request();request['check_design']={'sql':'DROP TABLE sources'}
  self.assertEqual(self.call('/api/interpretations/save',request)[0],400)
  self.assertEqual(self.fixture.s.read('Weijie Tang',self.fixture.uid)['revision'],0)
  self.assertEqual(self.call('/api/interpretations/save',self.fixture.request(),csrf=False)[0],403)
 def test_restored_readonly_rejects_writes(self):
  self.app.read_only_restored=True
  self.assertEqual(self.call('/api/interpretations/save',self.fixture.request())[0],403)

 def test_working_copy_and_catalog_http_csrf_and_readonly(self):
  import uuid
  f=self.fixture
  body=dict(request_id=str(uuid.uuid4()),unit_id=f.uid,expected_revision=0,body=dict(fields=f.fields(),revision=0,material_id=f.material['id']))
  self.assertEqual(self.call('/api/interpretations/draft',body,csrf=False)[0],403)
  self.assertEqual(self.call('/api/interpretations/draft',body)[0],200)
  self.assertEqual(len(self.call('/api/interpretations/drafts')[1]['drafts']),1)
  self.actor['name']='Ana Jokic';self.assertEqual(self.call('/api/interpretations/drafts')[1]['drafts'],[])
  self.actor['name']='Weijie Tang'
  self.assertEqual(self.call('/api/settings/site-catalog',{'revision':0,'fields':[]})[0],200)
  self.app.read_only_restored=True
  self.assertEqual(self.call('/api/settings/site-catalog',{'revision':1,'fields':[]})[0],403)
  self.assertEqual(self.call('/api/interpretations/draft',body)[0],403)
