import http.client
import json
import tempfile
import threading
import unittest
import uuid
import hashlib
from pathlib import Path
from local_workbench.store import Store
from local_workbench.server import Handler, ThreadingHTTPServer
from local_workbench.evidence import registered_pdf, pdf_range


class StoreTests(unittest.TestCase):
    def test_idempotency_actor_binding_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/"db.sqlite")
            session=store.session("")
            actor=store.select_actor(session["token"],"Ana")
            request={"request_id":str(uuid.uuid4()),"action":"assess","note":"review"}
            first=store.enqueue(actor,request)
            self.assertEqual(store.enqueue(actor,request)["id"],first["id"])
            with self.assertRaises(ValueError):
                store.enqueue(actor,dict(request,note="changed"))
            claimed=store.next_request()
            self.assertEqual(claimed["actor"],"Ana Jokic")
            reopened=Store(Path(tmp)/"db.sqlite")
            self.assertEqual(reopened.next_request()["id"],first["id"])
            reopened.finish(first["id"],"applied","saved")
            self.assertIsNone(reopened.next_request())

    def test_only_three_current_reviewers_and_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/"db.sqlite")
            self.assertEqual([a['name'] for a in store.actors()], ['Ana Jokic','Daniel Restad','Weijie Tang'])
            session=store.session('')
            self.assertEqual(store.select_actor(session['token'],'DR')['name'],'Daniel Restad')
            with self.assertRaises(ValueError):store.select_actor(session['token'],'Unknown person')
            with self.assertRaises(ValueError):store.enqueue({'id':'legacy','name':'Jay'},{'request_id':str(uuid.uuid4())})

    def test_drafts_do_not_submit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/"db.sqlite")
            store.draft("ana","task",{"note":"draft"})
            self.assertEqual(store.draft("ana","task"),{"note":"draft"})
            self.assertEqual(store.draft("dr","task"),{})
            self.assertEqual(store.requests(),[])


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        class FakeApp:
            pass
        self.app=FakeApp()
        self.app.root=self.root;self.app.instance="test";self.app.csrf="valid"
        self.app.runtime=self.root;self.app.store=Store(self.root/"db.sqlite")
        self.app.snapshot=lambda:{"sources":[],"tasks":[],"history":[],"counts":{}}
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler);self.server.app=self.app
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.origin=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,path="/api/state",method="GET",body=None,headers=None):
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port)
        connection.request(method,path,body,headers or {})
        response=connection.getresponse();status=response.status
        data=response.read();hdr=dict(response.getheaders());connection.close()
        return status,json.loads(data),hdr

    def test_host_origin_csrf_and_path_restriction(self):
        self.assertEqual(self.request(headers={"Host":"attacker.test"})[0],403)
        status,state,headers=self.request()
        self.assertEqual(status,200)
        self.assertIn("HttpOnly",headers["Set-Cookie"])
        for values in [{"Origin":"https://attacker.test","X-CSRF-Token":"valid"},
                       {"Origin":self.origin,"X-CSRF-Token":"wrong"}]:
            self.assertEqual(self.request("/api/actor","POST",'{"name":"Ana"}',dict(values,**{"Content-Type":"application/json"}))[0],403)
        self.assertEqual(self.request("/../../etc/passwd")[0],404)

    def test_actor_required_and_client_paths_forbidden(self):
        _,_,headers=self.request()
        base={"Origin":self.origin,"X-CSRF-Token":"valid","Content-Type":"application/json","Cookie":headers["Set-Cookie"].split(";")[0]}
        self.assertEqual(self.request("/api/decisions","POST",json.dumps({"request_id":str(uuid.uuid4())}),base)[0],400)
        self.assertEqual(self.request("/api/actor","POST",'{"name":"Ana"}',base)[0],200)
        self.assertEqual(self.request("/api/decisions","POST",json.dumps({"request_id":str(uuid.uuid4()),"upload_path":"/etc/passwd"}),base)[0],400)

    def test_instance_cookie_preserves_reviewer_when_another_local_service_changes_legacy_cookie(self):
        session = self.app.store.session("")
        self.app.store.select_actor(session["token"], "Ana")
        _, data, headers = self.request(headers={"Cookie": "wb_session=" + session["token"]})
        self.assertEqual(data["actor"]["name"], "Ana Jokic")
        scoped = headers["Set-Cookie"].split(";")[0]
        self.assertTrue(scoped.startswith(f"wb_session_{self.server.server_port}="))
        _, data, _ = self.request(headers={"Cookie": "wb_session=other-instance; " + scoped})
        self.assertEqual(data["actor"]["name"], "Ana Jokic")

    def test_imported_verdict_is_visible_without_exposing_machine_payload(self):
        review={'reviewer':'Ana','verdict':'ACCEPT','row':57,'artifact_sha256':'a'*64,'review_date':None,'private':'hidden'}
        self.app.snapshot=lambda:{'sources':[],'tasks':[],'history':[{
            'operation_id':'old','source_id':'PA006','operator':'Ana',
            'payload_json':json.dumps({'external_review':review,'internal_evidence':'not public'})}], 'counts':{}}
        status,data,_=self.request()
        self.assertEqual(status,200)
        record=data['history'][0]
        self.assertEqual(record['external_review']['verdict'],'ACCEPT')
        self.assertIsNone(record['external_review']['review_date'])
        self.assertNotIn('private',record['external_review'])
        self.assertNotIn('payload_json',record)

    def test_inline_pdf_uses_registered_version_and_only_pdf_can_embed(self):
        pdf=self.root/'source.pdf';pdf.write_bytes(b'%PDF-1.7\nverified fixture\n%%EOF')
        fingerprint=hashlib.sha256(pdf.read_bytes()).hexdigest()
        class Adapter:
            def call(inner,command,source_id):
                if source_id!='CS005':raise ValueError('Unknown registered source')
                return {'path':str(pdf),'hash':fingerprint}
        self.app.adapter=Adapter()
        status,info,_=self.request('/api/preview/CS005')
        self.assertEqual(status,200);self.assertEqual(info['kind'],'pdf')
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request('GET',info['url'],headers={'Range':'bytes=0-4'})
        response=connection.getresponse()
        self.assertEqual(response.status,206);self.assertEqual(response.read(),b'%PDF-')
        self.assertEqual(response.getheader('Content-Type'),'application/pdf')
        self.assertIn("frame-ancestors 'self'",response.getheader('Content-Security-Policy'))
        connection.close()
        self.assertEqual(self.request(info['url'].replace(fingerprint,'0'*64))[0],400)
        pdf.write_bytes(b'%PDF-1.7\nchanged')
        self.assertEqual(self.request(info['url'])[0],400)
        self.assertEqual(self.request(info['url']+'?path=/etc/passwd')[0],404)


class PDFEvidenceTests(unittest.TestCase):
    def test_range_boundaries(self):
        data=b'0123456789'
        self.assertEqual(pdf_range(data,'bytes=2-4')[:2],(206,b'234'))
        self.assertEqual(pdf_range(data,'bytes=-3')[:2],(206,b'789'))
        self.assertEqual(pdf_range(data,'bytes=8-999')[:2],(206,b'89'))
        for header in ('bytes=10-','bytes=4-3','bytes=-0','bytes=0-1,3-4','bytes=-','bad'):
            self.assertEqual(pdf_range(data,header)[0],416)

    def test_pdf_identity_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'wrong.pdf';path.write_bytes(b'<html>not a PDF</html>')
            with self.assertRaises(ValueError):registered_pdf({'path':path,'hash':hashlib.sha256(path.read_bytes()).hexdigest()})
            path.write_bytes(b'%PDF-1.7 test')
            with self.assertRaises(ValueError):registered_pdf({'path':path,'hash':None})
