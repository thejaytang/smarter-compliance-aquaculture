"""Actual HTTP recovery downloads preserve package ownership and saved records."""
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


class CollectionDownloadHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'workbench.sqlite')
        self.app = SimpleNamespace(runtime=self.root, store=self.store, csrf='isolated-csrf',
                                   reviewer=False, read_only_restored=False)
        self.app.collaboration = Collaboration(self.app)
        self.c = self.app.collaboration
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.app = self.app
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.cookies = {}
        for name in ('Weijie Tang', 'Ana Jokic'):
            session = self.store.session('')
            self.store.select_actor(session['token'], name)
            self.cookies[name] = f"wb_session_{self.server.server_port}={session['token']}"
        self.package_id = str(uuid.uuid4())
        self.raw = b'PK\x03\x04\x00retained exact package bytes\xff'
        (self.c.root / 'packages').mkdir()
        self.package_path = self.c.root / 'packages' / (self.package_id + '.zip')
        self.package_path.write_bytes(self.raw)
        self.c.put('sent_collection', self.package_id, {
            'id': self.package_id, 'actor': 'Weijie Tang', 'direction': 'receipt', 'items': []})
        self.c.put('adoption_receipt', 'retained-human-record', {
            'status': 'adopted', 'material': {'revision': 4, 'content_status': 'draft'}})
        self.url = '/api/collaboration/collection-download?id=' + self.package_id

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()

    def snapshot(self):
        with self.store.connect() as db:
            records = '\n'.join(db.iterdump())
        files = {str(p.relative_to(self.c.root)): sha256(p.read_bytes()).hexdigest()
                 for p in self.c.root.rglob('*') if p.is_file()}
        return records, files

    def request(self, path, method='GET', body=None, actor='Weijie Tang', headers=None):
        fields = {}
        if actor is not None: fields['Cookie'] = self.cookies[actor]
        if method == 'POST':
            fields.update(Origin=self.origin, **{'X-CSRF-Token': self.app.csrf,
                                                'Content-Type': 'application/json'})
        fields.update(headers or {})
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, fields)
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally: conn.close()

    def test_owner_get_and_repeated_direct_navigation_return_exact_saved_bytes_without_writes(self):
        before = self.snapshot()
        for headers in ({}, {'Sec-Fetch-Site': 'same-origin'}, {'Sec-Fetch-Site': 'none'},
                        {'Referer': self.origin + '/?material=current'}, {'Origin': self.origin}):
            with self.subTest(headers=headers):
                status, raw, response = self.request(self.url, headers=headers)
                self.assertEqual((status, raw), (200, self.raw))
                self.assertEqual(response['Content-Type'], 'application/zip')
                self.assertEqual(response['Content-Disposition'],
                                 'attachment; filename="review-' + self.package_id + '.zip"')
                self.assertEqual(response['Content-Location'], self.url)
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertNotIn('Set-Cookie', response)
                self.assertEqual(self.snapshot(), before)

    def test_existing_post_download_remains_compatible_with_recovery_header(self):
        before = self.snapshot()
        status, raw, headers = self.request('/api/collaboration/collection-download', 'POST',
                                            {'id': self.package_id.upper()})
        self.assertEqual((status, raw), (200, self.raw))
        self.assertEqual(headers['Content-Location'], self.url)
        self.assertEqual(headers['Content-Disposition'],
                         'attachment; filename="review-' + self.package_id + '.zip"')
        self.assertEqual(self.snapshot(), before)

    def test_real_receipt_export_returns_canonical_recovery_url_and_reuses_saved_package(self):
        receipt = str(uuid.uuid4()); identity = str(uuid.uuid4())
        self.c.put('adoption_receipt', receipt, {'id': receipt, 'status': 'adopted',
                   'material': {'revision': 4, 'source': {'source_id': 'TS001'}, 'content_status': 'draft'}})
        body = {'request_id': identity.upper(), 'kind': 'receipt',
                'items': [{'type': 'receipt', 'key': receipt}]}
        status, raw, headers = self.request('/api/collaboration/collection-export', 'POST', body)
        self.assertEqual(status, 200, raw)
        self.assertEqual(headers['Content-Disposition'],
                         'attachment; filename="adoption-receipts-' + identity[:8] + '.zip"')
        location = '/api/collaboration/collection-download?id=' + identity
        self.assertEqual(headers['Content-Location'], location)
        before = self.snapshot()
        self.assertEqual(self.request(location)[:2], (200, raw))
        self.assertEqual(self.request('/api/collaboration/collection-export', 'POST', body)[:2], (200, raw))
        self.assertEqual(self.snapshot(), before)

    def test_foreign_actor_or_unauthenticated_get_cannot_read_or_create_sessions(self):
        before = self.snapshot()
        for actor, headers in [('Ana Jokic', {}), (None, {}),
                               (None, {'Cookie': 'wb_session=' + 'unknown'}),
                               (None, {'Cookie': f'wb_session_{self.server.server_port}=unknown'})]:
            with self.subTest(actor=actor, headers=headers):
                status, raw, response = self.request(self.url, actor=actor, headers=headers)
                self.assertIn(status, (400, 403))
                self.assertNotEqual(raw, self.raw)
                self.assertNotIn('Content-Location', response)
                self.assertEqual(self.snapshot(), before)

    def test_cross_origin_metadata_and_wrong_host_are_denied_without_writes(self):
        before = self.snapshot()
        for headers in ({'Origin': 'https://outside.invalid'}, {'Origin': 'null'},
                        {'Referer': 'https://outside.invalid/path'},
                        {'Referer': self.origin + '.outside.invalid/path'},
                        {'Referer': 'http://127.0.0.1:1/'},
                        {'Sec-Fetch-Site': 'cross-site'}, {'Sec-Fetch-Site': 'same-site'},
                        {'Host': 'outside.invalid'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(self.url, headers=headers)[0], 403)
                self.assertEqual(self.snapshot(), before)

    def test_malformed_unknown_duplicate_and_unrelated_ids_are_rejected_without_writes(self):
        before = self.snapshot()
        for query in ('', '?id=', '?id=../private', '?id=invalid', '?id=' + str(uuid.uuid4()),
                      '?id=' + self.package_id + '&id=' + self.package_id,
                      '?id=' + self.package_id + '&path=private', '?id=%0D%0AInjected:yes'):
            with self.subTest(query=query):
                status, raw, headers = self.request('/api/collaboration/collection-download' + query)
                self.assertEqual(status, 400)
                self.assertNotEqual(raw, self.raw)
                self.assertNotIn('Content-Location', headers)
                self.assertEqual(self.snapshot(), before)

    def test_inspection_mode_and_existing_post_guards_remain_enforced(self):
        before = self.snapshot()
        self.app.read_only_restored = True
        self.assertEqual(self.request(self.url)[0], 403)
        self.app.read_only_restored = False
        for headers in ({'Origin': 'https://outside.invalid'}, {'X-CSRF-Token': 'wrong'}):
            self.assertEqual(self.request('/api/collaboration/collection-download', 'POST',
                                         {'id': self.package_id}, headers=headers)[0], 403)
        self.assertEqual(self.request('/api/collaboration/collection-download', 'POST',
                                     {'id': self.package_id}, actor='Ana Jokic')[0], 400)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__': unittest.main()
