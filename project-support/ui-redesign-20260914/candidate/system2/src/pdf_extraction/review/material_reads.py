"""Rebuildable, additive read projections. Authoritative revision JSON is untouched."""
import json


def summary_sql(expression):
    return f"json_set(json_remove({expression}, '$.blocks', '$.legacy', '$.scope', '$.checked_scope', '$.review_checks', '$.review_impact.affected_blocks', '$.review_impact.affected_scope', '$.review_impact.retained_scope', '$.confirmation.checked_scope', '$.issues'), '$.block_count', json_array_length({expression}, '$.blocks'), '$.scope_count', json_array_length({expression}, '$.scope'), '$.checked_scope_count', json_array_length({expression}, '$.checked_scope'))"


def extraction_summary(candidate):
    metadata = candidate.get('metadata') or {}
    summary = {key: metadata.get(key) for key in ('parser_status', 'parser_version')}
    for key in ('processed_scope', 'usable_scope', 'unprocessed_scope', 'unresolved'):
        value = metadata.get(key)
        summary[key + '_count'] = len(value) if isinstance(value, list) else None
    return summary


def compact_candidate(candidate):
    warnings = candidate.get('warnings', [])
    return {**{k: v for k, v in candidate.items() if k not in {'blocks', 'base_blocks', 'differences', 'metadata', 'scope', 'issues', 'warnings'}},
            'extraction': extraction_summary(candidate),
            'block_count': len(candidate['blocks']) if 'blocks' in candidate else candidate.get('block_count', 0),
            'warnings': warnings[:3], 'warning_count': candidate.get('warning_count', len(warnings))}


def candidate_summary_sql(expression):
    removed = f"json_remove({expression},'$.blocks','$.base_blocks','$.differences','$.metadata','$.scope','$.issues')"
    warnings = f"CASE WHEN json_array_length({expression},'$.warnings') <= 3 THEN json_extract({expression},'$.warnings') ELSE json_array(json_extract({expression},'$.warnings[0]'),json_extract({expression},'$.warnings[1]'),json_extract({expression},'$.warnings[2]')) END"
    extraction = "json_object(" + ",".join(
        [f"'{key}',json_extract({expression},'$.metadata.{key}')" for key in ('parser_status', 'parser_version')]
        + [f"'{key}_count',json_array_length({expression},'$.metadata.{key}')" for key in ('processed_scope', 'usable_scope', 'unprocessed_scope', 'unresolved')]) + ")"
    return f"json_set({removed},'$.extraction',{extraction},'$.block_count',json_array_length({expression},'$.blocks'),'$.warning_count',json_array_length({expression},'$.warnings'),'$.warnings',json({warnings}))"


class MaterialReads:
    def ensure_read_indexes(self, db):
        # Projections are disposable, never an authority or replacement for history.
        db.executescript('''
            CREATE TABLE IF NOT EXISTS material_read_schema(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS material_candidate_index(id TEXT PRIMARY KEY, material_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS material_candidate_index_material ON material_candidate_index(material_id);
            CREATE TABLE IF NOT EXISTS material_read_index(id TEXT PRIMARY KEY, source_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS material_revision_index(material_id TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(material_id,revision));
            CREATE INDEX IF NOT EXISTS material_source_lookup ON material_documents(source_id);
            CREATE INDEX IF NOT EXISTS material_candidate_lookup ON material_candidates(material_id);
            CREATE INDEX IF NOT EXISTS material_conflict_lookup ON material_conflicts(material_id);
        ''')
        def ready():
            return db.execute('SELECT 1 FROM material_read_schema WHERE version=5').fetchone() and all(
                db.execute('SELECT count(*) FROM '+projection).fetchone()[0] == db.execute('SELECT count(*) FROM '+authority).fetchone()[0]
                for projection,authority in (('material_read_index','material_documents'),('material_revision_index','material_revisions'),('material_candidate_index','material_candidates')))
        if ready():
            return
        db.execute('BEGIN IMMEDIATE')
        if ready():
            return
        # Rebuild only disposable projections when their contract changes.
        for trigger in ('material_read_insert','material_read_update','material_revision_read_insert','material_candidate_read_insert','material_candidate_read_update'):
            db.execute('DROP TRIGGER IF EXISTS '+trigger)
        db.execute('DELETE FROM material_candidate_index')
        db.execute('DELETE FROM material_read_index')
        db.execute('DELETE FROM material_revision_index')
        for operation in ('INSERT', 'UPDATE'):
            db.execute(f'''CREATE TRIGGER IF NOT EXISTS material_read_{operation.lower()} AFTER {operation} ON material_documents BEGIN
                INSERT INTO material_read_index VALUES(new.id,new.source_id,{summary_sql('new.data')})
                ON CONFLICT(id) DO UPDATE SET data=excluded.data,source_id=excluded.source_id; END''')
        candidate_sql = candidate_summary_sql('new.data')
        for operation in ('INSERT', 'UPDATE'):
            db.execute(f'''CREATE TRIGGER IF NOT EXISTS material_candidate_read_{operation.lower()} AFTER {operation} ON material_candidates BEGIN
                INSERT INTO material_candidate_index VALUES(new.id,new.material_id,{candidate_sql})
                ON CONFLICT(id) DO UPDATE SET data=excluded.data; END''')
        db.execute(f'''INSERT INTO material_candidate_index SELECT id,material_id,{candidate_sql.replace('new.data','data')} FROM material_candidates c
            WHERE NOT EXISTS(SELECT 1 FROM material_candidate_index i WHERE i.id=c.id)''')
        db.execute(f'''CREATE TRIGGER IF NOT EXISTS material_revision_read_insert AFTER INSERT ON material_revisions BEGIN
            INSERT INTO material_revision_index VALUES(new.material_id,new.revision,{summary_sql('new.data')}); END''')
        db.execute(f'''INSERT INTO material_read_index SELECT id,source_id,{summary_sql('data')} FROM material_documents d
            WHERE NOT EXISTS(SELECT 1 FROM material_read_index i WHERE i.id=d.id)''')
        db.execute(f'''INSERT INTO material_revision_index SELECT material_id,revision,{summary_sql('data')} FROM material_revisions d
            WHERE NOT EXISTS(SELECT 1 FROM material_revision_index i WHERE i.material_id=d.material_id AND i.revision=d.revision)''')

        db.execute('INSERT OR IGNORE INTO material_read_schema VALUES(5)')

    @staticmethod
    def page_options(offset=0, limit=50, maximum=50):
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= maximum:
            raise ValueError('invalid_material_page')
        return offset, limit

    def source_metadata(self, identity):
        with self.connect() as db:
            row = db.execute("SELECT json_extract(data,'$.source') FROM material_read_index WHERE id=?", (identity,)).fetchone()
            if row is None: raise ValueError('material_not_found')
            return json.loads(row[0])

    def source_bindings(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT json_set(json_extract(data,'$.source'),'$.source_stale',json_extract(data,'$.source_stale')) FROM material_read_index")]

    def candidate_summaries(self, db, material):
        result = []
        for row in db.execute("SELECT data FROM material_candidate_index WHERE material_id=? ORDER BY rowid", (material['id'],)):
            candidate = json.loads(row[0])
            candidate['stale'] = candidate['input_revision'] != material['content_revision'] or bool(material['source_stale'])
            result.append(candidate)
        return result

    def compact_view(self, material):
        # Also used after mutations: remove only transport-heavy nested payloads.
        result = dict(material)
        result['candidates'] = [compact_candidate(c) if 'blocks' in c else dict(c) for c in material.get('candidates', [])]
        result['conflicts'] = [{k:v for k,v in c.items() if k not in {'request', 'current'}} for c in material.get('conflicts', [])]
        return result

    def read_compact(self, identity, revision=None):
        if revision is not None:
            return self.read(identity, revision)
        with self.connect() as db:
            material = self._load(db, identity)
            material['candidates'] = self.candidate_summaries(db, material)
            material['conflicts'] = [json.loads(row[0]) for row in db.execute("SELECT json_remove(data,'$.request','$.current') FROM material_conflicts WHERE material_id=? ORDER BY rowid", (identity,))]
            material['related_versions'] = [json.loads(row[0]) for row in db.execute('SELECT data FROM material_read_index WHERE source_id=? AND id!=?', (material['source']['source_id'],identity))]
            return material

    def list_page(self, offset=0, limit=50, query=""):
        offset, limit = self.page_options(offset, limit)
        if not isinstance(query,str) or len(query)>300: raise ValueError('invalid_material_search')
        with self.connect() as db:
            where = " WHERE instr(lower(json_extract(data,'$.title')),lower(?))>0 OR instr(lower(source_id),lower(?))>0" if query else ''
            values = (query,query) if query else ()
            total = db.execute('SELECT count(*) FROM material_read_index'+where,values).fetchone()[0]
            materials = [json.loads(row[0]) for row in db.execute('SELECT data FROM material_read_index'+where+' ORDER BY rowid DESC LIMIT ? OFFSET ?', (*values,limit,offset))]
            for material in materials:
                material['candidates'] = self.candidate_summaries(db, material)
            return dict(materials=materials, total=total, offset=offset, limit=limit, has_more=offset+limit<total)

    def counts(self, source_issue_ids=()):
        counts = dict(total=0,current_reviewed=0,in_progress=0,historical=0,needs_followup=0)
        issue_ids = set(source_issue_ids)
        with self.connect() as db:
            active = {row[0] for row in db.execute("SELECT DISTINCT material_id FROM material_candidate_index WHERE json_extract(data,'$.status') IN ('running','ready','partial')")}
            for row in db.execute("SELECT id,source_id,json_extract(data,'$.source_stale'),json_extract(data,'$.content_status') FROM material_read_index"):
                identity,source,stale,status=row
                counts['total']+=1
                group='historical' if stale else 'needs_followup' if source in issue_ids or (status=='content_review_complete' and identity in active) else 'current_reviewed' if status=='content_review_complete' else 'in_progress'
                counts[group]+=1
        return counts

    def history_page(self, identity, offset=0, limit=20):
        offset, limit = self.page_options(offset, limit, 20)
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM material_read_index WHERE id=?', (identity,)).fetchone():
                raise ValueError('material_not_found')
            total = db.execute('SELECT count(*) FROM material_revision_index WHERE material_id=?',(identity,)).fetchone()[0]
            revisions = [json.loads(row[0]) for row in db.execute('SELECT data FROM material_revision_index WHERE material_id=? ORDER BY revision DESC LIMIT ? OFFSET ?', (identity,limit,offset))]
            return dict(revisions=revisions,total=total,offset=offset,limit=limit,has_more=offset+limit<total)

    def candidate_detail(self, identity, candidate_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?',(candidate_id,identity)).fetchone()
            if not row: raise ValueError('material_candidate_not_found')
            candidate = json.loads(row[0])
            material = json.loads(db.execute('SELECT data FROM material_read_index WHERE id=?',(identity,)).fetchone()[0])
            candidate['stale'] = candidate['input_revision'] != material['content_revision'] or bool(material['source_stale'])
            return candidate

    def conflict_detail(self, identity, conflict_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM material_conflicts WHERE id=? AND material_id=?',(conflict_id,identity)).fetchone()
            if not row: raise ValueError('material_conflict_not_found')
            return json.loads(row[0])
