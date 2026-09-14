"""Real isolated HTTP boundary tests; no runtime workers or business stores."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace
import unittest
import uuid

from local_workbench.server import Handler


class MaterialHTTPTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.result = {'status': 'applied', 'material': {'id': 'fixture', 'revision': 1}}
        self.actor = {'id': 'fixture-reviewer', 'name': 'Isolated Reviewer', 'token': 'isolated'}
        def call(command, **kwargs):
            self.calls.append((command, kwargs))
            return self.result
        personal = SimpleNamespace(call=call)
        def master_forbidden(*args, **kwargs): self.fail('Personal material HTTP must not call the master adapter')
        collaboration = SimpleNamespace(mode='coordinator',
            material_action=lambda actor,action,request: call('material_'+action, request=dict(request,actor=actor)),
            read_material=lambda actor,identity,revision=None,view='personal': call('material_read',material_id=identity,revision=revision),
            personal_adapter=lambda actor,identity: personal)
        app = SimpleNamespace(csrf='isolated-csrf', reviewer=False, collaboration=collaboration,
            system2=SimpleNamespace(call=master_forbidden), store=SimpleNamespace(session=lambda token: self.actor))
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.app = app
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, action, body, *, origin=True, csrf=True):
        client = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type': 'application/json', 'X-Material-API-Version':'3'}
        if origin:
            headers['Origin'] = f'http://127.0.0.1:{self.server.server_port}'
        if csrf:
            headers['X-CSRF-Token'] = 'isolated-csrf'
        client.request('POST', '/api/material/' + action, json.dumps(body), headers)
        response = client.getresponse()
        result = response.status, json.loads(response.read())
        client.close()
        return result

    def body(self, **kwargs):
        return dict(request_id=str(uuid.uuid4()), material_id='fixture', expected_revision=0, **kwargs)

    def test_old_client_cannot_mutate_new_compact_interface(self):
        for version in (None,'2'):
            client=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
            headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{self.server.server_port}',
                     'X-CSRF-Token':'isolated-csrf'}
            if version is not None:headers['X-Material-API-Version']=version
            client.request('POST','/api/material/save',json.dumps(self.body(blocks=[])),headers)
            response=client.getresponse()
            self.assertEqual(response.status,426)
            self.assertEqual(json.loads(response.read())['code'],'material_client_upgrade_required')
            self.assertEqual(self.calls,[])
            client.close()

    def test_actor_is_server_bound_and_client_actor_paths_rejected(self):
        body = self.body(blocks=[])
        status, _ = self.post('save', body)
        self.assertEqual(status, 200)
        self.assertEqual(self.calls, [('material_save', {'request':dict(body,actor='Isolated Reviewer')})])
        self.calls.clear()
        for field in ('actor', 'source', 'source_path', 'staged_path', 'canonical_artifacts'):
            status, result = self.post('save', dict(body, **{field:'untrusted'}))
            self.assertEqual(status, 400, (field, result))
        self.assertEqual(self.calls, [])

    def test_named_reviewer_and_origin_csrf_required(self):
        for options in ({'origin':False}, {'csrf':False}):
            self.assertEqual(self.post('save',self.body(blocks=[]),**options)[0],403)
        self.actor = {'id': None, 'name':'', 'token':'isolated'}
        status, result = self.post('save', self.body(blocks=[]))
        self.assertEqual(status, 400)
        self.assertIn('reviewer', result['error'])
        self.assertEqual(self.calls, [])

    def test_conflict_preserves_current_and_process_unavailable_http_status(self):
        self.result = {'status':'conflict','conflict_id':'durable','material':{'id':'fixture','revision':2}}
        status, result = self.post('save', self.body(blocks=[]))
        self.assertEqual(status,409)
        self.assertEqual(result['current']['revision'],2)
        self.assertEqual(result['conflict_id'],'durable')
        self.result = {'status':'unavailable','candidate_payload':None,'material':{'id':'fixture','revision':2}}
        status, result = self.post('process', self.body())
        self.assertEqual(status,503)
        self.assertIsNone(result['candidate_payload'])
        self.assertIn('not connected',result['error'])

    def test_open_accepts_only_source_identity_and_does_not_call_extract(self):
        body = {'request_id':str(uuid.uuid4()),'source_id':'TS001'}
        status, _ = self.post('open',body)
        self.assertEqual(status,200)
        self.assertEqual(self.calls[0][0],'material_open')
        self.assertEqual(self.calls[0][1]['request']['actor'],'Isolated Reviewer')
        status, _ = self.post('open',dict(body,relative_path='/arbitrary/file'))
        self.assertEqual(status,400)
        self.assertEqual(len(self.calls),1)

    def test_read_and_history_are_read_only_calls(self):
        for path, command in [('/api/material?id='+'a'*32,'material_read'),('/api/material/history?id='+'a'*32,'material_history')]:
            client = HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
            client.request('GET',path)
            response = client.getresponse()
            self.assertEqual(response.status,200,response.read())
            response.read()
            client.close()
            self.assertEqual(self.calls[-1][0],command)
        self.assertEqual(len(self.calls),2)

    def test_source_issue_requires_personal_review_instead_of_direct_source_write(self):
        reports=[]
        self.server.app.adapter=SimpleNamespace(call=lambda *args,**kwargs:reports.append((args,kwargs)))
        for revision in (0,3):
            self.result={'id':'fixture','revision':revision,'source':{'source_id':'TS001','content_hash':'a'*64}}
            status,result=self.post('source-issue',self.body(note='Original appendix missing'))
            self.assertEqual(status,409)
            self.assertEqual(result['code'],'personal_source_review_required')
        self.assertEqual(reports,[])
        self.assertEqual(self.calls,[])

    def test_source_issue_rejects_client_actor_source_hash_and_document_binding(self):
        for field in ('actor','source_id','source_sha256','content_hash','document_id','source_path'):
            status,result = self.post('source-issue',dict(self.body(note='Original issue'),**{field:'untrusted'}))
            self.assertEqual(status,400,(field,result))
        self.assertEqual(self.calls,[])

    def test_import_legacy_is_explicit_and_accepts_only_server_bound_identity(self):
        body = self.body()
        status,result = self.post('import-legacy',body)
        self.assertEqual(status,200,result)
        self.assertEqual(self.calls,[('material_import-legacy',{'request':dict(body,actor='Isolated Reviewer')})])
        self.calls.clear()
        for field in ('blocks','actor','document_id','source','provenance','issues'):
            status,result = self.post('import-legacy',dict(body,**{field:'untrusted'}))
            self.assertEqual(status,400,(field,result))
        self.assertEqual(self.calls,[])


if __name__ == '__main__':
    unittest.main()
