"""Actual HTTP reviewer workspace with absent System1 data and isolated stores."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
from local_workbench.server import Application, Handler
from local_workbench.store import Store


class ReviewerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)/'reviewer data'
        runtime=self.root/'runtime';runtime.mkdir(parents=True)
        store=Store(runtime/'workbench.sqlite');session=store.session('')
        actor=store.select_actor(session['token'],'Ana')
        self.old_request=store.enqueue(actor,{'request_id':str(uuid.uuid4()),'action':'assess','note':'retained old submission'})
        self.system1_forbidden=patch('local_workbench.adapter.System1.call',side_effect=AssertionError('Normal System1 access is forbidden in reviewer mode'))
        self.guard=self.system1_forbidden.start()
        self.absent_system1=Path(self.temporary.name)/'absent-system1'
        self.app=Application(self.root,system_root=self.absent_system1,reviewer=True,start_workers=True)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.app=self.app
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.origin=f'http://127.0.0.1:{self.server.server_port}'
        status,data,headers=self.request('/api/state')
        self.assertEqual(status,200,data)
        self.cookie=headers['Set-Cookie'].split(';')[0]
        status,_,_=self.request('/api/actor','POST',{'name':'Ana'})
        self.assertEqual(status,200)

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.app.close()
        self.system1_forbidden.stop();self.temporary.cleanup()

    def request(self,path,method='GET',body=None,headers=None):
        fields={'Origin':self.origin,'X-CSRF-Token':self.app.csrf,'Content-Type':'application/json'}
        if hasattr(self,'cookie'):fields['Cookie']=self.cookie
        fields.update(headers or {})
        client=HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        client.request(method,path,json.dumps(body) if body is not None else None,fields)
        response=client.getresponse();raw=response.read();result=(response.status,json.loads(raw),dict(response.getheaders()));client.close();return result

    def test_empty_reviewer_reads_work_without_normal_system1(self):
        for path in ('/api/state','/api/collaboration/state','/api/materials','/api/runtime-status'):
            status,result,_=self.request(path);self.assertEqual(status,200,(path,result))
        self.guard.assert_not_called();self.assertFalse(self.absent_system1.exists())
        self.assertTrue((self.app.system2.runtime/'offline-source.json').is_file())
        for worker in (self.app.worker,self.app.parser_worker,self.app.workbook_worker,self.app.confidence_worker):
            self.assertIsNone(worker.ident)
        self.assertEqual(self.app.store.requests()[0]['id'],self.old_request['id'])
        self.assertEqual(self.app.store.requests()[0]['status'],'queued')

    def test_reviewer_cannot_invoke_legacy_routes_upload_or_old_decisions(self):
        for path in ('/api/system2/workbook','/api/system2/state','/api/system2/references','/api/system3/input','/api/system1/workbook'):
            self.assertEqual(self.request(path)[0],403,path)
        for path in ('/api/system2/start','/api/system2/decision','/api/system1/assess','/api/settings','/api/upload'):
            self.assertEqual(self.request(path,'POST',{'source_ids':['TS001']})[0],403,path)
        before=self.app.store.requests()
        for actor in ('Ana','Weijie Tang'):
            self.assertEqual(self.request('/api/actor','POST',{'name':actor})[0],200)
            status,result,_=self.request('/api/decisions','POST',{'request_id':str(uuid.uuid4()),'action':'assess','upload_path':'/untrusted'})
            self.assertEqual(status,409);self.assertEqual(result['code'],'personal_source_review_required')
        self.assertEqual(self.app.store.requests(),before);self.guard.assert_not_called()

    def test_reviewer_still_enforces_origin_csrf_and_named_actor(self):
        for headers in ({'Origin':'https://outside.invalid'},{'X-CSRF-Token':'wrong'}):
            self.assertEqual(self.request('/api/actor','POST',{'name':'Weijie Tang'},headers)[0],403)
        self.cookie='wb_session_'+str(self.server.server_port)+'=unknown'
        status,body,_=self.request('/api/collaboration/source-save','POST',{'source_id':'TS001'})
        self.assertEqual(status,400);self.assertIn('reviewer',body['error'])
        self.guard.assert_not_called()
