"""Exercise saved work across physically separate SQLite files."""
import json
import sqlite3
import unittest
import uuid
from contextlib import closing
from backend.shared.workspace import Workspace,owner
from backend.system3.requirements import Requirements
from backend.system3.interpretations import Interpretations
from backend.shared.workspace_storage import copy_tables
from test_shared_requirements import SharedRequirementsTests,A,B


class SplitStoreTests(SharedRequirementsTests):
    def setUp(self):
        super().setUp()
        self.layout=Workspace(self.root/'separate')
        for name,role in [('system3_requirements','requirements'),('system3_scd','scd')]:
            copy_tables(self.root/'test.sqlite',self.layout.database(name),include=lambda t:owner(t)==role,drop_cross_fk=role=='scd')
        self.c.db=self.layout.connect
        self.r=Requirements(self.c);self.s=Interpretations(self.c)

    def test_saved_scd_remains_bound_to_old_split_and_cannot_have_dangling_origin(self):
        self.step('assign',field='Subject',start=0,end=48)
        self.step('assign',field='Modal Verb',start=49,end=53)
        self.assertEqual(self.doc['revision'],3)
        request=self.request();request['fields']['verification']['value']='Human evidence design'
        self.s.save(A,request);saved=self.s.read(A,self.uid);self.assertEqual(saved['session_revision'],3)
        self.step('assign',field='Main Verb',start=54,end=64)
        self.assertEqual(self.doc['revision'],4)
        after=self.s.read(B,self.uid)
        self.assertEqual(after['session_revision'],3);self.assertTrue(after['stale'])
        self.assertEqual(after['fields']['verification']['value'],'Human evidence design')
        with self.assertRaisesRegex(ValueError,'missing saved Requirement'):
            with self.c.db() as db:
                db.execute('UPDATE interpretation_origins SET session_revision=999 WHERE unit_id=?',(self.uid,))
        with self.c.db() as db:self.assertEqual(db.execute('SELECT session_revision FROM interpretation_origins').fetchone()[0],3)

    def test_atomic_failure_rolls_back_both_owning_databases(self):
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            with self.c.db() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO requirement_requests VALUES(?,?,?,?)',(A,'probe','digest','{}'))
                db.execute('INSERT INTO interpretation_requests VALUES(?,?,?,?)',(A,'probe','digest','{}'))
                raise RuntimeError('interrupted')
        for name,table in [('system3_requirements','requirement_requests'),('system3_scd','interpretation_requests')]:
            with closing(sqlite3.connect(self.layout.database(name))) as db:
                self.assertIsNone(db.execute('SELECT 1 FROM '+table+' WHERE id=?',('probe',)).fetchone())
        with closing(sqlite3.connect(self.layout.database('system3_scd'))) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='requirement_sessions'").fetchone())

    def test_replaceable_markers_use_runtime_and_preserve_legacy_fallback(self):
        from backend.shared.workspace_storage import alias, operational_root
        branch=self.layout.workspace/'sources/processing/personal'
        alias(branch,'workflow.sqlite',self.layout.database('system2'),'branch_test__')
        self.assertEqual(operational_root(branch),(self.layout.runtime/'state/system2/branch_test__').resolve())
        self.assertEqual(operational_root(self.root/'legacy'),self.root/'legacy')
        self.assertFalse(operational_root(branch).exists())

    def test_sql_literals_are_never_renamed_by_branch_storage(self):
        from backend.shared.workspace_storage import alias,connect
        branch=self.layout.workspace/'sources/test-branch';alias(branch,'workflow.sqlite',self.layout.database('system2'),'branch_test__')
        with connect(branch/'workflow.sqlite') as db:
            db.execute('CREATE TABLE material_documents(id TEXT PRIMARY KEY, data TEXT)')
            db.execute("INSERT INTO material_documents VALUES('material_documents',?)",('documents and receipts',))
            self.assertEqual(db.execute('SELECT id,data FROM material_documents').fetchone(),('material_documents','documents and receipts'))
            self.assertTrue(db.execute("SELECT 1 FROM sqlite_master WHERE name='material_documents'").fetchone())

if __name__=='__main__':unittest.main()
