"""The local PDF viewer ships exact assets, without general file serving or business calls."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import threading
import unittest
from local_workbench.server import Handler, Application


class PDFReaderRouteTests(unittest.TestCase):
    def setUp(self):
        self.ui = Path(__file__).resolve().parents[1] / 'frontend'
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.app = SimpleNamespace(ui_root=self.ui, reviewer=True, read_only_restored=False)
        self.server.app.static_path=lambda name:Application.static_path(self.server.app,name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def get(self, path, headers=None):
        conn=HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request('GET', path, headers=headers or {})
            response=conn.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally:
            conn.close()

    def test_reader_and_worker_are_usable_with_scoped_local_policy(self):
        for route,mime in [('/pdf-reader.html','text/html'),('/pdf-reader.js','text/javascript'),
                           ('/pdf-reader.css','text/css'),('/vendor/pdfjs/build/pdf.worker.mjs','text/javascript')]:
            status,headers,data=self.get(route)
            self.assertEqual(status,200);self.assertTrue(headers['Content-Type'].startswith(mime))
            self.assertEqual(data,self.server.app.static_path(route.lstrip('/')).read_bytes())
            self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        _,headers,_=self.get('/pdf-reader.html')
        policy=headers['Content-Security-Policy']
        for required in ("connect-src 'self'","worker-src 'self'","frame-ancestors 'self'","object-src 'none'","form-action 'none'"):
            self.assertIn(required,policy)
        self.assertNotIn('unsafe-eval',policy)
        _,headers,_=self.get('/')
        self.assertNotIn('unsafe-inline',headers['Content-Security-Policy'])

    def test_javascript_mime_is_independent_of_windows_registry(self):
        from unittest.mock import patch
        with patch('local_workbench.server.mimetypes.guess_type', return_value=('text/plain', None)):
            for route in ('/pdf-reader.js', '/interpretations.js', '/check-design.js', '/vendor/markdown/tools.mjs'):
                status,headers,_=self.get(route)
                self.assertEqual(status,200,route)
                self.assertTrue(headers['Content-Type'].startswith('text/javascript'),route)

    def test_manifest_assets_are_exact_and_versioned(self):
        root=self.ui/'assets/vendor/pdfjs';manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(manifest['version'],'6.3.289')
        for name,digest in manifest['files'].items():
            with self.subTest(asset=name):
                self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
        self.assertIn('standard_fonts/LiberationSans-Regular.ttf',manifest['files'])
        self.assertIn('cmaps/Adobe-Japan1-UCS2.bcmap',manifest['files'])

    def test_unknown_traversal_and_foreign_host_do_not_serve_files(self):
        for route in ('/vendor/pdfjs/../../server.py','/vendor/pdfjs/%2e%2e/LICENSE',
                      '/vendor/pdfjs/manifest.json','/vendor/pdfjs/package.json','/pdf-reader.html/../../server.py'):
            self.assertEqual(self.get(route)[0],404,route)
        self.assertEqual(self.get('/pdf-reader.html',{'Host':'foreign.example'})[0],403)


if __name__=='__main__':unittest.main()
