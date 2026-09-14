"""Small read-only browser projections; full evidence is loaded only for one unit."""
import json
from . import row_store, task_model, effective
from ..contracts.hashing import digest

UNIT_KEYS = ('id', 'kind', 'version', 'classification', 'content_status', 'requirement_status',
             'content_confidence', 'requirement_confidence', 'content_reasons', 'requirement_reasons',
             'superseded_by', 'evidence_only')
DOC_KEYS = ('id', 'source', 'revision', 'state', 'eligible', 'issues', 'error', 'parser_complete',
            'source_complete', 'complete', 'upstream_issues', 'cursor', 'total_pages', 'processed_pages', 'generation', 'policy_revision','hierarchy_version')


def browser_state(store, view='browser', document_id=None, unit_id=None, offset=0, query='', chapter='', task_type='', include_reviewed=False, stage='',page_index=None,parent_id=None):
    with store.connect() as db:
        db.execute('BEGIN')
        policy = store.policy(db)
        normalized = row_store.enabled(db)
        if view == 'unit' and unit_id == 'processing-failure':
            from .processing_failure import describe
            row=db.execute('SELECT data FROM documents WHERE id=?',(document_id,)).fetchone()
            if not row:raise ValueError('document_not_found')
            failure=describe(json.loads(row[0]))
            if not failure:raise ValueError('processing_failure_changed_refresh_required')
            return {'document_id':document_id,'processing_failure':failure,
                    'effective':{'references':failure['references']}}
        if view=='outline' and normalized:
            from .outline import read
            return read(db,document_id,parent_id,offset)
        if view in {'pages','page'} and normalized:
            from .pdf_pages import read
            if view=='page' and page_index is None:raise ValueError('page_index_required')
            return read(db,document_id,page_index if view=='page' else None,offset)
        if view == 'history_page' and normalized:
            total=db.execute('SELECT COUNT(*) FROM review_history WHERE document_id=?',(document_id,)).fetchone()[0]
            rows=db.execute('SELECT data FROM review_history WHERE document_id=? ORDER BY rowid DESC LIMIT 50 OFFSET ?',(document_id,max(0,int(offset)))).fetchall()
            return {'items':[json.loads(r[0]) for r in rows],'total':total,'offset':int(offset),'limit':50}
        if view == 'tasks' and normalized:
            return task_page(db, document_id, offset, query, chapter, task_type, include_reviewed, stage)
        if view == 'unit' and normalized:
            meta = db.execute('SELECT data FROM documents WHERE id=?',(document_id,)).fetchone()
            row = db.execute('SELECT data FROM review_units WHERE document_id=? AND id=?',(document_id,unit_id)).fetchone()
            if not row or not meta: raise ValueError('unit_not_found')
            doc=json.loads(meta[0]); unit=json.loads(row[0])
            related={unit['id']:unit}
            for r in db.execute("""WITH RECURSIVE ancestors(id) AS (SELECT ? UNION SELECT dependency_id FROM ancestors a CROSS JOIN review_dependencies d ON d.unit_id=a.id WHERE d.document_id=?) SELECT u.data FROM ancestors a CROSS JOIN review_units u ON u.id=a.id WHERE u.document_id=?""",(unit_id,document_id,document_id)):
                item=json.loads(r[0]);related[item['id']]=item
            view=effective.resolve(unit,related)
            from .coverage_preview import references as coverage_references
            view['references']=coverage_references(store,doc,unit,view.get('references',[]))
            if unit.get('source_hierarchy') or unit.get('hierarchy_edit'):
                from ..domains.requirements.review_hierarchy import ancestors
                view['ancestors']=ancestors(unit,related,doc.get('hierarchy_containers',{}))
            owner=effective.table_owner(unit,related)
            revisions=[]
            for r in db.execute('SELECT data FROM review_history WHERE document_id=? ORDER BY rowid DESC LIMIT 100',(document_id,)):
                h=json.loads(r[0])
                if (h.get('unit_id')==unit_id or unit_id in h.get('created_ids',[])) and h.get('repair_before'):revisions.append({k:h[k] for k in ('request_id','action','actor','revision')})
            from .splitting import context as split_context
            from .table_geometry import context as table_context
            from ..verification.acceptance import dimension_details,ASPECTS
            from .dependency_checks import pending as pending_dependencies
            from ..verification.requirement_scores import applicable_parts
            task=task_model.describe(unit,related)
            return {'document_id':document_id,'revision':doc['revision'],'policy_revision':policy['revision'],
                'guard':guard(db,doc,unit_id),'unit':unit,'task':task,
                'confidence_dimensions':{stage:dimension_details(applicable_parts(unit,task['proposal']) if stage=='requirement' else unit.get(stage+'_parts',[]),stage,policy[stage]) for stage in ASPECTS},
                'effective':view,'repair_history':revisions,'table_owner_fingerprint':digest(owner) if owner else None,
                'display_fields':view['fields'],
                'pending_content_dependencies':pending_dependencies(unit,related),
                'coverage_pages':sorted({r['page_index'] for r in view['references'] if type(r.get('page_index')) is int}) if unit['kind']=='coverage' else [],
                'table_context':table_context(db,document_id,owner) if owner and owner['id']==unit_id else None,
                'split_context':split_context(db,document_id,unit) if doc.get('hierarchy_version') and not owner and not unit.get('table_assembly') and unit['kind']!='coverage' and not unit.get('superseded_by') else None,
                'coverage':coverage_summary(db,document_id,unit) if unit['kind']=='coverage' else None}
        if view == 'unit':
            doc = store._load(db, document_id)
            unit = next((u for u in doc['units'] if u['id'] == unit_id), None)
            if unit is None:
                raise ValueError('unit_not_found')
            return {'document_id': doc['id'], 'revision': doc['revision'],
                    'policy_revision': policy['revision'], 'unit': unit}
        result = {'schema_version': 'system2-browser/1', 'policy': policy,
                  'documents': [], 'pending': 0, 'published': 0, 'processing_followups':0}
        for row in db.execute('SELECT data FROM documents ORDER BY id'):
            doc = json.loads(row[0])
            if normalized and view not in {'summary'}:
                doc=store._load(db,doc['id'])
            item = {k: doc[k] for k in DOC_KEYS if k in doc}
            from .processing_failure import describe
            item['processing_failure']=describe(doc)
            if doc['eligible'] and item['processing_failure']:result['processing_followups']+=1
            item['published'] = dict.fromkeys(doc.get('published',{}))
            from .requirement_subdivision import count
            item['published_count'] = doc.get('published_count', count(doc.get('published', {})))
            item['history'] = doc.get('history',[]) if view == 'history' else []
            item['units'] = []
            item['unit_count'] = doc.get('unit_count',len(doc.get('units',[])))
            item['waiting_count'] = doc.get('waiting_count',0)
            item['pending_count'] = sum(u['content_status'] not in {'machine_accepted','human_accepted'} or
                                        u['requirement_status'] not in {'machine_accepted','human_accepted'} for u in doc.get('units',[]))
            if normalized: item['pending_count']=doc['pending_count']
            if doc['eligible']:
                result['pending'] += item['pending_count']
            result['published'] += item['published_count']
            if view == 'browser':
                for unit in doc['units']:
                    small = {k: unit[k] for k in UNIT_KEYS if k in unit}
                    # Retain full body text for existing queue search. Evidence/structures,
                    # drafts, scores and other fields arrive from the guarded unit read.
                    fields = {**unit['original']['fields'], **unit.get('edits', {})}
                    small.update(_summary=True, original={'fields': {k: fields.get(k, '') for k in ('identifier','title','body')},
                                                         'references': [], 'structure': []})
                    item['units'].append(small)
            result['documents'].append(item)
        return result


def guard(db, doc, unit_id):
    rows = db.execute("""WITH RECURSIVE ancestors(id) AS (
      SELECT ? UNION SELECT d.dependency_id FROM ancestors a CROSS JOIN review_dependencies d ON d.unit_id=a.id WHERE d.document_id=?
    ) SELECT u.id,u.fingerprint FROM ancestors a CROSS JOIN review_units u ON u.id=a.id WHERE u.document_id=? ORDER BY u.id""",(unit_id,doc['id'],doc['id'])).fetchall()
    return digest([doc['source']['content_hash'],doc.get('generation',0),doc['canonical'],[list(r) for r in rows]])


def task_page(db, document_id, offset=0, query='', chapter='', task_type='', include_reviewed=False, stage=''):
    offset=max(0,int(offset)); args=[document_id]; terms=['document_id=?',"COALESCE(json_extract(data,'$.superseded_by'),'') IN ('','[]')"]
    if not include_reviewed: terms.append('pending=1')
    if stage=='content' and not include_reviewed:terms.append('content_ok=0')
    elif stage=='requirement':terms.append('content_ok=1')
    if chapter: terms.append('chapter=?'); args.append(chapter)
    if task_type: terms.append('task_type=?'); args.append(task_type)
    if query: terms.append("search_text LIKE ? ESCAPE '\\'"); args.append('%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
    where=' AND '.join(terms)
    total=db.execute('SELECT COUNT(*) FROM review_units INDEXED BY review_active_rows WHERE '+where,args).fetchone()[0]
    rows=db.execute("SELECT id,title,chapter,task_type,pending,waiting,fingerprint,COALESCE(json_extract(data,'$.evidence_only'),0) AS evidence_only,COALESCE(json_extract(data,'$.blockers[0]'),json_extract(data,'$.content_reasons[0]'),json_extract(data,'$.requirement_reasons[0]'),'confidence_missing') AS reason_code FROM review_units INDEXED BY review_active_rows WHERE "+where+' ORDER BY ordinal LIMIT 50 OFFSET ?',args+[offset]).fetchall()
    chapters=[r[0] for r in db.execute('SELECT chapter FROM review_units WHERE document_id=? GROUP BY chapter ORDER BY MIN(ordinal)',(document_id,))]
    return {'schema_version':'system2-tasks/2','items':[dict(r,reason=task_model.reason(r['reason_code'])) for r in rows],'total':total,'offset':offset,'limit':50,'chapters':chapters,'stage_counts':dict(db.execute('SELECT COALESCE(SUM(pending=1 AND content_ok=0),0) AS content,COALESCE(SUM(pending=1 AND content_ok=1),0) AS requirement,COALESCE(SUM(waiting),0) AS waiting FROM review_units WHERE document_id=?',(document_id,)).fetchone())}


def coverage_summary(db,did,unit):
    args=[did];where="document_id=? AND kind!='coverage' AND COALESCE(json_extract(data,'$.superseded_by'),'') IN ('','[]')"
    from ..domains.requirements.pdf_review_scope import pages
    scope=pages(unit)
    if scope:
        where+=" AND EXISTS(SELECT 1 FROM json_each(COALESCE(json_extract(data,'$.reviewed_references'),json_extract(data,'$.original.references'))) r WHERE json_extract(r.value,'$.page_index') IN ("+','.join('?' for _ in scope)+'))'
        args.extend(sorted(scope))
    elif unit.get('chapter') and unit['chapter']!='Source completeness':where+=' AND chapter=?';args.append(unit['chapter'])
    rows=db.execute('SELECT chapter,COUNT(*) AS units,SUM(content_ok) AS content_accepted,SUM(requirement_ok) AS classified FROM review_units WHERE '+where+' GROUP BY chapter ORDER BY MIN(ordinal)',args).fetchall()
    return [dict(r) for r in rows]
