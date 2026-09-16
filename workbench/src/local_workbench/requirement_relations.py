"""Relational projection of active Requirement links, retaining nested counts."""
import json


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS requirement_relationships(
        session_id TEXT NOT NULL, owner_id TEXT NOT NULL, target_id TEXT NOT NULL,
        relation TEXT NOT NULL CHECK(relation IN ('conditions','exceptions','subrequirement')),
        path TEXT NOT NULL, quantities TEXT NOT NULL,
        PRIMARY KEY(owner_id,relation,path),
        FOREIGN KEY(session_id) REFERENCES requirement_sessions(id),
        FOREIGN KEY(owner_id) REFERENCES requirement_units(id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(target_id) REFERENCES requirement_units(id) DEFERRABLE INITIALLY DEFERRED);
      CREATE INDEX IF NOT EXISTS requirement_relation_target ON requirement_relationships(target_id);
      CREATE INDEX IF NOT EXISTS requirement_relation_session ON requirement_relationships(session_id);
      CREATE TABLE IF NOT EXISTS requirement_relationship_versions(
        session_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
        FOREIGN KEY(session_id) REFERENCES requirement_sessions(id));
    ''')
    for row in db.execute('''SELECT s.body FROM requirement_sessions s
        LEFT JOIN requirement_relationship_versions v ON s.id=v.session_id
        WHERE v.revision IS NULL OR v.revision<>s.revision''').fetchall():
        project(db,json.loads(row[0]))


def project(db,doc):
    db.execute('DELETE FROM requirement_relationships WHERE session_id=?',(doc['id'],))
    if doc.get('deleted'):
        db.execute('INSERT INTO requirement_relationship_versions VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET revision=excluded.revision',(doc['id'],doc['revision']))
        return
    def walk(owner,relation,group,path=(),quantities=()):
        counts=quantities+(group[0],)
        for index,child in enumerate(group[1:],1):
            branch=path+(index,)
            if isinstance(child,list):walk(owner,relation,child,branch,counts)
            else:db.execute('INSERT INTO requirement_relationships VALUES(?,?,?,?,?,?)',
                (doc['id'],owner,child,relation,json.dumps(branch),json.dumps(counts)))
    for uid,u in doc['units'].items():
        for relation in ('conditions','exceptions','subrequirement'):
            if u.get(relation):walk(uid,relation,u[relation])
    db.execute('INSERT INTO requirement_relationship_versions VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET revision=excluded.revision',(doc['id'],doc['revision']))
