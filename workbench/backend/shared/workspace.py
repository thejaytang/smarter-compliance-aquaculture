"""Owning workspace paths and coordinated System3 transactions."""
from contextlib import ExitStack, contextmanager, closing
from pathlib import Path
import json
import os
import re
import sqlite3

from .workspace_storage import Connection, alias

DATABASES=('system1','system2','system3_requirements','system3_scd')


def owner(table):
    if table=='source_workspace_objects':return 'sources'
    if table=='requirement_interpretations' or table.startswith('interpretation_') or table=='site_field_catalog':return 'scd'
    if table.startswith('requirement_'):return 'requirements'
    if table=='collaboration_objects':return 'materials'
    return None


class BusinessConnection(Connection):
    def execute(self, sql, parameters=(), /):
        match=re.search(r'CREATE\s+(TABLE|INDEX|TRIGGER)\s+(?:IF NOT EXISTS\s+)?([A-Za-z_]\w*)',sql,re.I)
        if match:
            kind,name=match.groups();schema=owner(name)
            if kind.upper()!='TABLE':
                target=re.search(r'\bON\s+([A-Za-z_]\w*)',sql,re.I)
                if target:schema=owner(target[1])
            if schema:
                sql=sql[:match.start(2)]+schema+'.'+sql[match.start(2):]
                # SQLite foreign keys cannot target another database. The
                # commit validator below replaces this specific old FK.
                sql=re.sub(r',\s*FOREIGN KEY\(session_id,session_revision\) REFERENCES requirement_steps\(session_id,revision\)','',sql)
        return super().execute(sql,parameters)


def validate_system3(db):
    def exists(schema,name):
        return db.execute(f"SELECT 1 FROM {schema}.sqlite_master WHERE type='table' AND name=?",(name,)).fetchone()
    if exists('scd','interpretation_origins') and exists('requirements','requirement_steps'):
        missing=db.execute('''SELECT o.unit_id,o.session_revision FROM interpretation_origins o
            LEFT JOIN requirement_steps r ON r.session_id=o.session_id AND r.revision=o.session_revision
            WHERE r.session_id IS NULL LIMIT 1''').fetchone()
        if missing:raise ValueError('S/C/D references a missing saved Requirement revision: '+str(tuple(missing)))


class Workspace:
    def __init__(self, workbench):
        self.root=Path(workbench).resolve()
        self.workspace=self.root/'workspace'
        self.runtime=self.root/'runtime'
        self.databases=self.workspace/'databases'
        for folder in (self.databases,self.workspace/'sources',self.workspace/'logs',self.workspace/'packages/collaboration',
                       self.workspace/'packages/delivery',self.runtime/'state',self.runtime/'settings',self.runtime/'backups',self.runtime/'logs',self.runtime/'cache'):
            folder.mkdir(parents=True,exist_ok=True)
    def database(self,name):
        if name not in DATABASES:raise ValueError('Unknown owning database.')
        return self.databases/(name+'.sqlite')
    @property
    def journal(self):return self.runtime/'state/workbench.sqlite'
    @property
    def source_config(self):return self.runtime/'settings/system1/config.json'
    @property
    def materials(self):return self.workspace/'sources/processing/main'
    def material_branch(self,root,prefix=''):
        alias(root,'workflow.sqlite',self.database('system2'),prefix)
    def connect(self,timeout=30):
        db=sqlite3.connect(self.journal,timeout=timeout,factory=BusinessConnection)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        for name,schema in (('system1','sources'),('system2','materials'),('system3_requirements','requirements'),('system3_scd','scd')):
            db.execute(f'ATTACH DATABASE ? AS {schema}',(str(self.database(name)),))
            db.execute(f'PRAGMA {schema}.synchronous=FULL')
        db.validator=validate_system3
        return db
    @contextmanager
    def freeze(self):
        """Reserve all writers before opening any backup read snapshots.

        Same-file readers remain available. A bounded busy error refuses a
        partial capture. Writers to attached stores use the same path order.
        """
        with ExitStack() as stack:
            for path in [self.journal,*[self.database(n) for n in DATABASES]]:
                db=stack.enter_context(closing(sqlite3.connect(path,timeout=10)))
                db.execute('BEGIN IMMEDIATE')
            yield


def active(root):
    return (Path(root)/'runtime/state/layout.json').is_file()
