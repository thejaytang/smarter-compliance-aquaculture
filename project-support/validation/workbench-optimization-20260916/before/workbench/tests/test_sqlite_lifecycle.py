"""Regression for durable transactions and Windows file-handle release."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from local_workbench.sqlite_support import connect

class ConnectionLifecycleTests(unittest.TestCase):
    def test_commit_rollback_and_handle_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'review.sqlite'
            with connect(path) as db:
                db.execute('CREATE TABLE review(note TEXT)')
                db.execute('INSERT INTO review VALUES (?)', ('saved',))
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute('SELECT * FROM review')
            with self.assertRaisesRegex(ValueError, 'rollback'):
                with connect(path) as aborted:
                    aborted.execute('INSERT INTO review VALUES (?)', ('not saved',))
                    raise ValueError('rollback')
            with connect(path) as current:
                self.assertEqual(current.execute('SELECT note FROM review').fetchall(), [('saved',)])
            moved = path.with_name('moved.sqlite')
            path.rename(moved)
            moved.unlink()
