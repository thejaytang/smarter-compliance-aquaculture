"""Versioned, indexed persistence. Legacy documents remain readable until explicit migration."""
import json
from . import task_model
from ..contracts.hashing import encoded, digest

SCHEMA = '''
CREATE TABLE IF NOT EXISTS storage_version(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS review_units(document_id TEXT, id TEXT, ordinal INTEGER, data TEXT NOT NULL,
 fingerprint TEXT NOT NULL, title TEXT, chapter TEXT, task_type TEXT, pending INTEGER, waiting INTEGER,
 content_ok INTEGER, requirement_ok INTEGER, kind TEXT, search_text TEXT,
 PRIMARY KEY(document_id,id));
CREATE INDEX IF NOT EXISTS review_queue ON review_units(document_id,pending,ordinal);
CREATE INDEX IF NOT EXISTS review_chapter ON review_units(document_id,chapter,ordinal);
CREATE TABLE IF NOT EXISTS review_dependencies(document_id TEXT, unit_id TEXT, dependency_id TEXT,
 PRIMARY KEY(document_id,unit_id,dependency_id));
CREATE INDEX IF NOT EXISTS review_dependents ON review_dependencies(document_id,dependency_id);
CREATE TABLE IF NOT EXISTS review_history(document_id TEXT, request_id TEXT, data TEXT,
 PRIMARY KEY(document_id,request_id));
CREATE TABLE IF NOT EXISTS deliveries(document_id TEXT, unit_id TEXT, data TEXT,
 PRIMARY KEY(document_id,unit_id));
'''


def initialize(db):
    db.executescript(SCHEMA)
    if not db.execute('SELECT 1 FROM documents LIMIT 1').fetchone():
        db.execute('INSERT OR IGNORE INTO storage_version VALUES(2)')


def enabled(db):
    return bool(db.execute('SELECT 1 FROM storage_version WHERE version=2').fetchone())


def load(db, identity, focused=None):
    row = db.execute('SELECT data FROM documents WHERE id=?', (identity,)).fetchone()
    if row is None: raise ValueError('document_not_found')
    doc = json.loads(row[0])
    if not enabled(db): return doc
    # Page checks depend on omissions as well as known units. Until a complete
    # reverse original-region index exists, hydrate the source on writes so a
    # new/changed unit invalidates every affected page and its downstream rows.
    # Indexed list/detail reads remain unchanged.
    if doc.get('source_verification_pages'):
        focused = None
    args = [identity]
    where = ''
    if focused:
        # Descendants need invalidation, ancestors supply their acceptance evidence.
        ids = {focused} if isinstance(focused,str) else set(focused)
        for direction in ('children', 'parents'):
            front = set(ids)
            while front:
                new = set()
                for uid in front:
                    sql = ('SELECT unit_id FROM review_dependencies WHERE document_id=? AND dependency_id=?'
                           if direction == 'children' else
                           'SELECT dependency_id FROM review_dependencies WHERE document_id=? AND unit_id=?')
                    new.update(r[0] for r in db.execute(sql, (identity,uid)))
                front = new - ids; ids.update(new)
        where = ' AND id IN (' + ','.join('?' for _ in ids) + ')'
        args.extend(sorted(ids))
        doc['_partial'] = True
    doc['units'] = [json.loads(r[0]) for r in db.execute('SELECT data FROM review_units WHERE document_id=?'+where+' ORDER BY ordinal',args)]
    doc['_fingerprints'] = {u['id']:digest(u) for u in doc['units']}
    doc['history'] = [] if focused else [json.loads(r[0]) for r in db.execute('SELECT data FROM review_history WHERE document_id=? ORDER BY rowid',(identity,))]
    doc['published'] = {r[0]:json.loads(r[1]) for r in db.execute('SELECT unit_id,data FROM deliveries WHERE document_id=?',(identity,)) if not focused or r[0] in ids}
    return doc


def save(db, doc):
    if not enabled(db):
        db.execute('INSERT INTO documents VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(doc['id'],encoded(doc)))
        return
    did = doc['id']; partial = doc.get('_partial', False)
    if not partial:
        keep = {u['id'] for u in doc['units']}
        for (uid,) in db.execute('SELECT id FROM review_units WHERE document_id=?',(did,)).fetchall():
            if uid not in keep:
                db.execute('DELETE FROM review_units WHERE document_id=? AND id=?',(did,uid))
                db.execute('DELETE FROM review_dependencies WHERE document_id=? AND unit_id=?',(did,uid))
    last = db.execute('SELECT COALESCE(MAX(ordinal),-1) FROM review_units WHERE document_id=?',(did,)).fetchone()[0]
    by_id={u['id']:u for u in doc['units']}
    for ordinal, u in enumerate(doc['units']):
        fingerprint = digest(u)
        if doc.get('_fingerprints',{}).get(u['id']) == fingerprint:
            if not partial:db.execute('UPDATE review_units SET ordinal=? WHERE document_id=? AND id=? AND ordinal<>?',(ordinal,did,u['id'],ordinal))
            continue
        meta = task_model.describe(u, by_id)
        old = db.execute('SELECT ordinal FROM review_units WHERE document_id=? AND id=?',(did,u['id'])).fetchone()
        if partial:
            if old: ordinal=old[0]
            else: last+=1; ordinal=last
        fields = task_model.readable_fields(u, by_id)
        db.execute('INSERT INTO review_units VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(document_id,id) DO UPDATE SET ordinal=excluded.ordinal,data=excluded.data,fingerprint=excluded.fingerprint,title=excluded.title,chapter=excluded.chapter,task_type=excluded.task_type,pending=excluded.pending,waiting=excluded.waiting,content_ok=excluded.content_ok,requirement_ok=excluded.requirement_ok,kind=excluded.kind,search_text=excluded.search_text',
          (did,u['id'],ordinal,encoded(u),fingerprint,meta['title'],meta['chapter'],meta['type'],meta['actionable'],meta['waiting'],task_model.passed(u.get('content_status')),task_model.passed(u.get('requirement_status')),u['kind'],' '.join(str(v) for v in fields.values())))
        db.execute('DELETE FROM review_dependencies WHERE document_id=? AND unit_id=?',(did,u['id']))
        db.executemany('INSERT OR IGNORE INTO review_dependencies VALUES(?,?,?)',[(did,u['id'],v) for v in u.get('dependencies',[])])
    for h in doc.get('history',[]):
        db.execute('INSERT OR IGNORE INTO review_history VALUES(?,?,?)',(did,h['request_id'],encoded(h)))
    loaded = {u['id'] for u in doc['units']}
    for (uid,) in db.execute('SELECT unit_id FROM deliveries WHERE document_id=?',(did,)).fetchall():
        if (not partial or uid in loaded) and uid not in doc['published']:
            db.execute('DELETE FROM deliveries WHERE document_id=? AND unit_id=?',(did,uid))
    for uid,item in doc['published'].items():
        db.execute('INSERT INTO deliveries VALUES(?,?,?) ON CONFLICT(document_id,unit_id) DO UPDATE SET data=excluded.data WHERE data<>excluded.data',(did,uid,encoded(item)))
    meta = {k:v for k,v in doc.items() if k not in {'units','history','published'} and not k.startswith('_')}
    count,pending,waiting = db.execute('SELECT COUNT(*),COALESCE(SUM(pending),0),COALESCE(SUM(waiting),0) FROM review_units WHERE document_id=?',(did,)).fetchone()
    published_count = db.execute("""SELECT COALESCE(SUM(CASE
        WHEN json_extract(data,'$.subdivision.policy.count_basis')='subitems'
        THEN json_array_length(data,'$.subitems') ELSE 1 END),0)
        FROM deliveries WHERE document_id=?""", (did,)).fetchone()[0]
    meta.update(unit_count=count,pending_count=pending,waiting_count=waiting,published_count=published_count)
    cover = db.execute("SELECT COUNT(*),COALESCE(SUM(content_ok=0),0) FROM review_units WHERE document_id=? AND kind='coverage'",(did,)).fetchone()
    meta['source_complete'] = bool(meta.get('parser_complete') and cover[0] and not cover[1] and ('total_pages' not in meta or len(meta.get('processed_pages',[]))==meta['total_pages']))
    unreviewed = db.execute("SELECT COUNT(*) FROM review_units WHERE document_id=? AND (content_ok=0 OR requirement_ok=0) AND COALESCE(json_extract(data,'$.superseded_by'),'') IN ('','[]')",(did,)).fetchone()[0]
    meta['complete'] = bool(count and not unreviewed and meta['source_complete'] and meta['eligible'] and not meta['issues'])
    if meta['state'] not in {'paused','queued','running','failed','conversion_required'}:
        meta['state']='complete' if meta['complete'] else 'partial' if meta['published_count'] else 'waiting_review'
    doc.update({k:meta[k] for k in ('complete','source_complete','state')})
    db.execute('INSERT INTO documents VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(did,encoded(meta)))


def migrate(store, transform=None):
    """Caller quiesces workers; SQLite backup preserves the exact pre-migration state."""
    import sqlite3
    from datetime import datetime, timezone
    backup = store.root / ('workflow-before-v2-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite')
    with store.connect() as db:
        if enabled(db): return {'status':'already_current'}
        with sqlite3.connect(backup) as target: db.backup(target)
    with store.connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
    with store.transaction() as db:
        docs=[json.loads(r[0]) for r in db.execute('SELECT data FROM documents')]
        db.execute('INSERT INTO storage_version VALUES(2)')
        for doc in docs:
            if transform:doc=transform(db,doc)
            save(db,doc)
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('migration_integrity_failed')
    return {'status':'migrated','backup':str(backup),'documents':len(docs),'units':sum(len(d['units']) for d in docs)}
