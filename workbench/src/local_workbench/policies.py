"""The workbench owns the only editable confidence policy and its history."""
import json
import math
import sqlite3
from local_workbench.sqlite_support import connect as connect_sqlite
import time

DEFAULT = {'revision': 1, 'system1': .95, 'content': .95, 'requirement': .95, 'system3': .95}


class Policies:
    def __init__(self, database):
        self.database = database
        with connect_sqlite(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS review_policies(revision INTEGER PRIMARY KEY, data TEXT, actor TEXT, created REAL)')
            db.execute('INSERT OR IGNORE INTO review_policies VALUES(?,?,?,?)', (1, json.dumps(DEFAULT), 'initial configuration', time.time()))

    def get(self):
        with connect_sqlite(self.database) as db:
            return json.loads(db.execute('SELECT data FROM review_policies ORDER BY revision DESC LIMIT 1').fetchone()[0])

    def save(self, values, actor, expected_revision):
        if not actor or set(values) != set(DEFAULT) - {'revision'}:
            raise ValueError('A named operator and all four thresholds are required.')
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 1 for v in values.values()):
            raise ValueError('Thresholds must be above 0 and at most 100%.')
        with connect_sqlite(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            revision = db.execute('SELECT MAX(revision) FROM review_policies').fetchone()[0]
            if expected_revision != revision:
                raise ValueError('The settings changed. Reload before saving.')
            policy = dict(values, revision=revision + 1)
            db.execute('INSERT INTO review_policies VALUES(?,?,?,?)', (revision + 1, json.dumps(policy), actor, time.time()))
        return policy

    def history(self):
        with connect_sqlite(self.database) as db:
            return [{'policy': json.loads(r[0]), 'actor': r[1], 'created': r[2]}
                    for r in db.execute('SELECT data,actor,created FROM review_policies ORDER BY revision')]
