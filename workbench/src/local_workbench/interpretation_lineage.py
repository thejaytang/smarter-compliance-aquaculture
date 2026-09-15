"""Append-only relational projection of frozen interpretation provenance.

JSON history remains the authoritative saved artifact. This transactionally built
index provides foreign-key checked joins without linking to mutable unit rows.
"""
import json
from .requirements import encode


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS interpretation_origins(
        actor TEXT NOT NULL, unit_id TEXT NOT NULL, revision INTEGER NOT NULL,
        session_id TEXT NOT NULL, session_revision INTEGER NOT NULL,
        material_id TEXT NOT NULL, material_revision INTEGER NOT NULL,
        block_id TEXT NOT NULL, source_id TEXT NOT NULL, source_json TEXT NOT NULL,
        chapter TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
        original_text TEXT NOT NULL, source_refs TEXT NOT NULL, quality TEXT NOT NULL,
        PRIMARY KEY(actor,unit_id,revision),
        FOREIGN KEY(actor,unit_id,revision) REFERENCES interpretation_history(actor,unit_id,revision),
        FOREIGN KEY(session_id,session_revision) REFERENCES requirement_steps(session_id,revision),
        CHECK(start>=0 AND end>=start));
      CREATE TABLE IF NOT EXISTS interpretation_fields(
        actor TEXT NOT NULL, unit_id TEXT NOT NULL, revision INTEGER NOT NULL,
        field_key TEXT NOT NULL, value TEXT NOT NULL, basis TEXT NOT NULL,
        PRIMARY KEY(actor,unit_id,revision,field_key),
        FOREIGN KEY(actor,unit_id,revision) REFERENCES interpretation_origins(actor,unit_id,revision));
      CREATE TABLE IF NOT EXISTS interpretation_citations(
        actor TEXT NOT NULL, unit_id TEXT NOT NULL, revision INTEGER NOT NULL,
        field_key TEXT NOT NULL, ordinal INTEGER NOT NULL, citation_id TEXT NOT NULL,
        material_id TEXT NOT NULL, material_revision INTEGER, block_id TEXT,
        source_json TEXT NOT NULL, source_refs TEXT NOT NULL, quote TEXT NOT NULL,
        start INTEGER, end INTEGER, anchor_status TEXT NOT NULL,
        PRIMARY KEY(actor,unit_id,revision,field_key,ordinal),
        FOREIGN KEY(actor,unit_id,revision,field_key) REFERENCES interpretation_fields(actor,unit_id,revision,field_key));
      CREATE INDEX IF NOT EXISTS interpretation_origin_source ON interpretation_origins(actor,source_id,material_id);
      CREATE INDEX IF NOT EXISTS interpretation_citation_source ON interpretation_citations(actor,material_id,block_id);
      CREATE TABLE IF NOT EXISTS interpretation_rule_nodes(
        actor TEXT NOT NULL, unit_id TEXT NOT NULL, revision INTEGER NOT NULL,
        node_id TEXT NOT NULL, group_key TEXT NOT NULL, parent_id TEXT,
        field_key TEXT, body TEXT NOT NULL,
        PRIMARY KEY(actor,unit_id,revision,node_id),
        FOREIGN KEY(actor,unit_id,revision) REFERENCES interpretation_origins(actor,unit_id,revision),
        FOREIGN KEY(actor,unit_id,revision,field_key) REFERENCES interpretation_fields(actor,unit_id,revision,field_key),
        FOREIGN KEY(actor,unit_id,revision,parent_id) REFERENCES interpretation_rule_nodes(actor,unit_id,revision,node_id));
      CREATE INDEX IF NOT EXISTS requirement_session_material ON requirement_sessions(actor,material_id);
      CREATE INDEX IF NOT EXISTS requirement_unit_session ON requirement_units(actor,session_id);
      CREATE TABLE IF NOT EXISTS interpretation_run_index(
        actor TEXT NOT NULL, id TEXT NOT NULL, unit_id TEXT NOT NULL,
        PRIMARY KEY(actor,id), FOREIGN KEY(actor,id) REFERENCES interpretation_runs(actor,id));
      CREATE INDEX IF NOT EXISTS interpretation_runs_by_unit ON interpretation_run_index(actor,unit_id);
      CREATE TRIGGER IF NOT EXISTS interpretation_run_insert AFTER INSERT ON interpretation_runs BEGIN
        INSERT INTO interpretation_run_index VALUES(NEW.actor,NEW.id,json_extract(NEW.body,'$.unit_id'));
      END;
    ''')


def source_anchor(doc, split, quality='captured'):
    uid=doc['unit_id']; start,end=split['spans'][uid]
    return dict(session_id=split['id'],session_revision=split['revision'],material_id=split['material_id'],
        material_revision=split['material_revision'],block_id=split['block_id'],source=split['source'],
        chapter=split.get('chapter',''),span=[start,end],text=split['text'],
        source_refs=split.get('source_refs',[]),quality=quality)


def project(db, doc, anchor, citations=()):
    key=(doc['actor'],doc['unit_id'],doc['revision'])
    if db.execute('SELECT 1 FROM interpretation_origins WHERE actor=? AND unit_id=? AND revision=?',key).fetchone():return
    db.execute('INSERT INTO interpretation_origins VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',key+(
        anchor['session_id'],anchor['session_revision'],anchor['material_id'],anchor['material_revision'],
        anchor['block_id'],anchor['source'].get('source_id',''),encode(anchor['source']),anchor['chapter'],
        *anchor['span'],anchor['text'],encode(anchor['source_refs']),anchor['quality']))
    by_id={x['id']:x for x in citations}; materials={x['id']:x for x in doc.get('context_manifest',[])}
    for field,f in doc['fields'].items():
        db.execute('INSERT INTO interpretation_fields VALUES(?,?,?,?,?,?)',key+(field,f['value'],f['basis']))
        for i,ref in enumerate(f['references']):
            citation=by_id.get(ref['id'],{}); mid=citation.get('material_id') or ref['id'].split(':',1)[0]
            material=materials.get(mid,{})
            start,end=ref.get('start'),ref.get('end')
            status='exact' if start is not None else 'ambiguous' if citation else 'legacy-unlocated'
            db.execute('INSERT INTO interpretation_citations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',key+(
                field,i,ref['id'],mid,material.get('revision'),citation.get('block_id'),encode(material.get('source',{})),
                encode(citation.get('source_refs',[])),ref['quote'],start,end,status))
    def add_rule(node,group,parent=None):
        db.execute('INSERT INTO interpretation_rule_nodes VALUES(?,?,?,?,?,?,?,?)',key+(
            node['id'],group,parent,node.get('interpretation_field'),encode(node)))
        for child in node.get('rules',[]):add_rule(child,group,node['id'])
    for group,node in doc.get('check_design',{}).get('groups',{}).items():
        if node:add_rule(node,group)


def backfill(db, actor, uid):
    """Use immutable saved steps only; never silently bind old drafts to new text."""
    rows=db.execute('''SELECT h.body FROM interpretation_history h LEFT JOIN interpretation_origins o
      ON h.actor=o.actor AND h.unit_id=o.unit_id AND h.revision=o.revision
      WHERE h.actor=? AND h.unit_id=? AND o.revision IS NULL''',(actor,uid)).fetchall()
    for row in rows:
        doc=json.loads(row[0]); s=db.execute('SELECT body FROM requirement_steps WHERE session_id=? AND revision=?',
            (doc['session_id'],doc['session_revision'])).fetchone()
        if not s:continue  # report absent lineage, do not fabricate a source version
        split=json.loads(s[0])
        if uid not in split['spans']:continue
        project(db,doc,source_anchor(doc,split,'legacy-saved-step'))


def read(db, actor, uid, revision):
    key=(actor,uid,revision)
    row=db.execute('SELECT * FROM interpretation_origins WHERE actor=? AND unit_id=? AND revision=?',key).fetchone()
    if not row:return {'status':'not-saved' if revision==0 else 'unavailable','fields':[]}
    names=[d[1] for d in db.execute('PRAGMA table_info(interpretation_origins)')]
    result=dict(zip(names,row));result['source']=json.loads(result.pop('source_json'));result['source_refs']=json.loads(result['source_refs'])
    result['fields']=[]
    for field,value,basis in db.execute('SELECT field_key,value,basis FROM interpretation_fields WHERE actor=? AND unit_id=? AND revision=?',key):
        refs=[]
        for r in db.execute('SELECT citation_id,material_id,material_revision,block_id,source_json,source_refs,quote,start,end,anchor_status FROM interpretation_citations WHERE actor=? AND unit_id=? AND revision=? AND field_key=? ORDER BY ordinal',key+(field,)):
            refs.append(dict(id=r[0],material_id=r[1],material_revision=r[2],block_id=r[3],source=json.loads(r[4]),source_refs=json.loads(r[5]),quote=r[6],start=r[7],end=r[8],anchor_status=r[9]))
        result['fields'].append(dict(key=field,value=value,basis=basis,references=refs))
    result['rules']=[dict(id=r[0],group=r[1],parent_id=r[2],field_key=r[3],rule=json.loads(r[4])) for r in db.execute(
        'SELECT node_id,group_key,parent_id,field_key,body FROM interpretation_rule_nodes WHERE actor=? AND unit_id=? AND revision=?',key)]
    result['status']='saved';result['text_kind']='saved-extracted-passage';return result
