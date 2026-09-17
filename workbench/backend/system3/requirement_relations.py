"""Relational projection of active Requirement links, retaining nested counts."""
import json
from backend.system3 import requirement_structure as structure


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
    db.executescript('''
      CREATE TABLE IF NOT EXISTS requirement_structure_nodes(
        session_id TEXT NOT NULL, owner_id TEXT NOT NULL, node_id TEXT NOT NULL, parent_id TEXT,
        position INTEGER NOT NULL, kind TEXT NOT NULL, role TEXT, quantity TEXT, negated INTEGER NOT NULL,
        start INTEGER, end INTEGER, target_id TEXT, origin_role TEXT,
        PRIMARY KEY(session_id,node_id),
        FOREIGN KEY(session_id) REFERENCES requirement_sessions(id),
        FOREIGN KEY(owner_id) REFERENCES requirement_units(id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(target_id) REFERENCES requirement_units(id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(session_id,parent_id) REFERENCES requirement_structure_nodes(session_id,node_id) DEFERRABLE INITIALLY DEFERRED);
      CREATE INDEX IF NOT EXISTS requirement_structure_owner ON requirement_structure_nodes(owner_id);
      CREATE INDEX IF NOT EXISTS requirement_structure_target ON requirement_structure_nodes(target_id);
      CREATE TABLE IF NOT EXISTS requirement_group_relationships(
        session_id TEXT NOT NULL, node_id TEXT NOT NULL, text TEXT NOT NULL,
        start INTEGER NOT NULL, end INTEGER NOT NULL, before_nodes TEXT NOT NULL, after_nodes TEXT NOT NULL,
        PRIMARY KEY(session_id,node_id),
        FOREIGN KEY(session_id,node_id) REFERENCES requirement_structure_nodes(session_id,node_id));
    ''')
    for row in db.execute('''SELECT s.body FROM requirement_sessions s
        LEFT JOIN requirement_relationship_versions v ON s.id=v.session_id
        WHERE v.revision IS NULL OR v.revision<>s.revision''').fetchall():
        project(db,json.loads(row[0]))


def project(db,doc):
    db.execute('DELETE FROM requirement_group_relationships WHERE session_id=?',(doc['id'],))
    db.execute('DELETE FROM requirement_structure_nodes WHERE session_id=?',(doc['id'],))
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
        if uid in doc.get('structures',{}):
            tree=doc['structures'][uid]
            for node,parent in structure.walk(tree):
                span=node.get('span',[None,None])
                db.execute('INSERT INTO requirement_structure_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (doc['id'],uid,node['id'],parent['id'] if parent else None,parent['children'].index(node) if parent else 0,node['kind'],node.get('role'),json.dumps(node.get('quantity')),int(node.get('negated',False)),*span,node.get('target_id'),node.get('origin_role')))
                if node.get('relationship'):
                    rel=node['relationship'];sides=structure.relationship_sides(node)
                    db.execute('INSERT INTO requirement_group_relationships VALUES(?,?,?,?,?,?,?)',
                        (doc['id'],node['id'],rel['text'],*rel['span'],json.dumps(sides['before']),json.dumps(sides['after'])))
            continue
        for relation in ('conditions','exceptions','subrequirement'):
            if u.get(relation):walk(uid,relation,u[relation])
    db.execute('INSERT INTO requirement_relationship_versions VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET revision=excluded.revision',(doc['id'],doc['revision']))
