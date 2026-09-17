from backend.shared.sqlite_support import connect as connect_sqlite
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import time

from local_workbench.export_status import read_status, cached_snapshot


class ExportStatusTests(unittest.TestCase):
    def test_saved_newer_than_snapshot_and_failure_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with connect_sqlite(root/'workflow.sqlite') as db:
                db.executescript('CREATE TABLE events(sequence INTEGER); CREATE TABLE policies(revision INTEGER); INSERT INTO events VALUES(7); INSERT INTO policies VALUES(1);')
            book = root/'snapshot.xlsx'
            book.write_bytes(b'coherent snapshot')
            meta = dict(event_cursor=7, policy_revision=1, path=str(book), sha256=hashlib.sha256(book.read_bytes()).hexdigest(),
                        registry_sha256='a'*64,registry_kind='sqlite_snapshot')
            source=dict(schema='system2-source-version/1',checked_at=time.time(),status='checked',
                        registry_sha256='a'*64,registry_kind='sqlite_snapshot')
            (root/'source-version.json').write_text(json.dumps(source))
            (root/'workbook.json').write_text(json.dumps(meta))
            self.assertEqual(read_status(root)['status'], 'current')
            with connect_sqlite(root/'workflow.sqlite') as db: db.execute('INSERT INTO events VALUES(8)')
            state = read_status(root, {'status': 'current'})
            self.assertEqual((state['status'],state['saved_event_cursor'],state['event_cursor']),('pending',8,7))
            self.assertEqual(read_status(root, {'status': 'refreshing'})['status'], 'refreshing')
            self.assertEqual(read_status(root, {'status': 'failed', 'message': 'disk error'})['status'], 'failed')
            # Failure/retry does not remove the earlier coherent download.
            self.assertEqual(cached_snapshot(root), (meta, b'coherent snapshot'))
            meta['event_cursor'] = 8
            (root/'workbook.json').write_text(json.dumps(meta))
            self.assertEqual(read_status(root, {'status': 'current'})['status'], 'current')
            book.write_bytes(b'new bytes before new marker')
            with self.assertRaises(ValueError): cached_snapshot(root)
            (root/'workbook.json').write_text('{interrupted')
            self.assertEqual(read_status(root)['status'], 'unknown')

    def test_source_change_without_review_events_is_pending_and_failed_check_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);book=root/'snapshot.xlsx';book.write_bytes(b'previous coherent source snapshot')
            with connect_sqlite(root/'workflow.sqlite') as db:
                db.executescript('CREATE TABLE events(sequence INTEGER);CREATE TABLE policies(revision INTEGER);INSERT INTO events VALUES(7);INSERT INTO policies VALUES(1);')
            meta=dict(event_cursor=7,policy_revision=1,path=str(book),sha256=hashlib.sha256(book.read_bytes()).hexdigest(),
                      registry_sha256='a'*64,registry_kind='sqlite_snapshot')
            (root/'workbook.json').write_text(json.dumps(meta))
            self.assertEqual(read_status(root)['status'],'unknown')
            source=dict(schema='system2-source-version/1',checked_at=time.time(),status='checked',registry_sha256='b'*64,registry_kind='sqlite_snapshot')
            marker=root/'source-version.json';marker.write_text(json.dumps(source))
            self.assertEqual(read_status(root)['status'],'pending')
            self.assertEqual(cached_snapshot(root)[1],book.read_bytes())
            meta['registry_sha256']='b'*64;(root/'workbook.json').write_text(json.dumps(meta))
            self.assertEqual(read_status(root)['status'],'current')
            marker.write_text(json.dumps(dict(source,status='unknown')))
            self.assertEqual(read_status(root)['status'],'unknown')
            marker.write_text(json.dumps(dict(source,checked_at=time.time()-31)))
            self.assertEqual(read_status(root)['status'],'unknown')
            marker.write_text(json.dumps(source))
            self.assertEqual(read_status(root)['status'],'current')
