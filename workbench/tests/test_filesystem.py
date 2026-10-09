"""Actual long-path I/O and unchanged evidence identity across atomic copies."""
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from backend.shared.filesystem import FilePath, check_file_paths, windows_io_path, logical_path, sqlite_uri, temporary_directory
from local_workbench.workspace_migration import clone_file, sha, promotion_temp


class FilesystemTests(unittest.TestCase):
    def test_windows_drive_unc_and_existing_namespace(self):
        self.assertEqual(windows_io_path(r'C:\root\a\..\original.txt'), r'\\?\C:\root\original.txt')
        self.assertEqual(windows_io_path(r'\\server\share\original.txt'), r'\\?\UNC\server\share\original.txt')
        self.assertEqual(windows_io_path(r'\\?\C:\root\original.txt'), r'\\?\C:\root\original.txt')
        self.assertEqual(logical_path(r'\\?\UNC\server\share\original.txt'), r'\\server\share\original.txt')

    def test_long_unicode_copy_retry_traversal_uri_and_sqlite(self):
        with temporary_directory(prefix='wb-path-') as directory:
            root = FilePath(directory)
            deep = root / ('資料 ' + 'x' * 80) / ('y' * 80) / ('z' * 80)
            check_file_paths([deep / 'original.html'])
            deep.mkdir(parents=True)
            source = deep / 'original.html'
            source.write_bytes(b'immutable original')
            target = deep / 'copy.html'
            clone_file(Path(str(source)), Path(str(target)))
            clone_file(source, target)
            self.assertEqual(sha(source), sha(target))
            self.assertFalse(promotion_temp(target).exists())
            self.assertEqual(source.resolve(), source)
            self.assertIn(source, list(root.rglob('*.html')))
            self.assertNotIn('?', source.as_uri())
            self.assertNotIn('\\\\?\\', str(source))
            with closing(sqlite3.connect(deep/'state.sqlite')) as db:
                db.execute('CREATE TABLE saved(value TEXT)')
                db.execute("INSERT INTO saved VALUES('preserved')"); db.commit()
            with closing(sqlite3.connect(sqlite_uri(deep/'state.sqlite')+'?mode=ro', uri=True)) as db:
                self.assertEqual(db.execute('SELECT value FROM saved').fetchone()[0], 'preserved')
            source.write_bytes(b'changed incoming')
            with self.assertRaisesRegex(ValueError, 'differs'):
                clone_file(source, target)
            self.assertEqual(target.read_bytes(), b'immutable original')
        self.assertFalse(root.exists())

    def test_long_alias_retains_readonly_uri_and_logical_descriptor(self):
        from backend.shared.workspace_storage import alias, connect
        import json
        with temporary_directory(prefix='wb-alias-') as root:
            root=FilePath(root)
            folder=root/('a'*100)/('b'*100)/('c'*80)
            database=root/'owner.sqlite'
            with closing(sqlite3.connect(database)) as db:
                db.execute('CREATE TABLE documents(id TEXT)');db.commit()
            alias(folder,'workflow.sqlite',database)
            self.assertNotIn('?',json.loads((folder/'.storage.json').read_text())['workflow.sqlite']['database'])
            with connect((folder/'workflow.sqlite').as_uri()+'?mode=ro',uri=True) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM documents').fetchone()[0],0)
                with self.assertRaises(sqlite3.OperationalError):db.execute("INSERT INTO documents VALUES('forbidden')")

    def test_memory_and_temporary_sqlite_connections_remain_nonpersistent(self):
        from backend.shared.workspace_storage import connect
        for target,options in [('',{}),(':memory:',{}),('file::memory:?cache=shared',{'uri':True}),('file:wb-test?mode=memory&cache=shared',{'uri':True})]:
            with connect(target,**options) as db:
                self.assertEqual(db.execute('PRAGMA database_list').fetchone()[2],'')

    def test_temporary_cleanup_handles_readonly_files(self):
        import stat
        with temporary_directory(prefix='wb-readonly-') as root:
            file=root/'retained-copy';file.write_bytes(b'copy')
            file.chmod(stat.S_IREAD)
        self.assertFalse(root.exists())

    @unittest.skipUnless(os.name == 'nt', 'Native Windows component length')
    def test_unrepresentable_component_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, 'native Windows'):
            check_file_paths([FilePath.cwd()/('x'*256)])
