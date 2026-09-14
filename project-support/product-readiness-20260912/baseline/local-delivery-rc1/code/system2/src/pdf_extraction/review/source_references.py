"""Source-first reference drafts and immutable confirmations in the owning DB.

Reference confirmation does not accept extraction, qualify a sample, or release
data. These records never overwrite Canonical, Gold or ordinary review units.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math

from ..contracts.hashing import digest, encoded

ROLES = {'text','heading','header','footer','table','table_cell','caption','footnote','figure','unknown'}
LINKS = {'footnote','caption','continuation','reading_order','context'}


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS source_reference_tasks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS source_reference_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, reference_id TEXT NOT NULL, data TEXT NOT NULL)')


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE name='source_reference_tasks' AND type='table'").fetchone() is not None


def _load(db, identity):
    if not exists(db):raise ValueError('reference_not_found')
    row=db.execute('SELECT data FROM source_reference_tasks WHERE id=?',(identity,)).fetchone()
    if not row:raise ValueError('reference_not_found')
    return json.loads(row[0])


def view(store, *, document_id=None, reference_id=None):
    with store.connect() as db:
        db.execute('BEGIN')
        if not exists(db):
            if reference_id:raise ValueError('reference_not_found')
            return {'items':[]}
        if reference_id:
            task=_load(db,reference_id)
            row=db.execute('SELECT data FROM documents WHERE id=?',(task['document_id'],)).fetchone()
            doc=json.loads(row[0]) if row else {}
            history=[json.loads(r[0]) for r in db.execute('SELECT data FROM source_reference_events WHERE reference_id=? ORDER BY sequence',(reference_id,))]
            return dict(task,guard=digest(task),history=history,
                        source_current=doc.get('eligible',False) and doc.get('source',{}).get('content_hash')==task['source']['content_hash'])
        rows=db.execute('SELECT data FROM source_reference_tasks WHERE document_id=? ORDER BY rowid DESC',(document_id,)).fetchall()
        return {'items':[{k:t[k] for k in ('id','page_index','supporting_pages','status','actor','revision','created_at','study_origin')}
                         for t in map(lambda r:json.loads(r[0]),rows)]}


def _validate(body, task, *, confirm=False):
    if not isinstance(body,dict) or set(body)-{'regions','relations','survey','prior_exposure','assistance','unresolved','note','form_draft'}:
        raise ValueError('invalid_reference_fields')
    result=deepcopy(body)
    for key in ('assistance','unresolved','note'):
        if not isinstance(result.get(key,''),str):raise ValueError('reference_notes_must_be_text')
        result.setdefault(key,'')
    draft=result.get('form_draft',{})
    if not isinstance(draft,dict) or len(encoded(draft))>500000:raise ValueError('invalid_reference_form_draft')
    regions=result.get('regions',[]);relations=result.get('relations',[])
    if not isinstance(regions,list) or len(regions)>2000 or not isinstance(relations,list) or len(relations)>4000:
        raise ValueError('reference_scope_too_large')
    by_id={}
    for region in regions:
        if not isinstance(region,dict):raise ValueError('invalid_reference_region')
        identity=region.get('id')
        if not isinstance(identity,str) or not identity or len(identity)>120 or identity in by_id:raise ValueError('invalid_reference_region_identity')
        by_id[identity]=region
        if region.get('role') not in ROLES or type(region.get('page_index')) is not int:raise ValueError('invalid_reference_region_role_or_page')
        size=task['dimensions'].get(str(region['page_index']));b=region.get('bbox')
        if (not size or not isinstance(b,list) or len(b)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in b)
                or not 0<=b[0]<b[2]<=size['width'] or not 0<=b[1]<b[3]<=size['height']):
            raise ValueError('reference_region_outside_original')
        if not isinstance(region.get('text',''),str) or len(region.get('text',''))>200000:raise ValueError('invalid_reference_text')
        if confirm and region['role'] not in {'figure','table','table_cell'} and not region.get('text','').strip():raise ValueError('transcribe_original_region_or_keep_pending')
        if confirm and region['role']=='unknown':raise ValueError('resolve_unknown_original_regions_before_confirmation')
        if region['role']=='table':
            if any(type(region.get(k)) is not int or region[k]<1 for k in ('row_count','column_count')) or region['row_count']*region['column_count']>10000:
                raise ValueError('invalid_reference_table_dimensions')
    occupied={}
    for region in regions:
        if region['role']!='table_cell':continue
        parent=by_id.get(region.get('table_id'))
        if not parent or parent['role']!='table' or parent['page_index']!=region['page_index']:raise ValueError('choose_reference_table_on_same_page')
        values=[region.get(k) for k in ('row','column','row_span','column_span')]
        if any(type(v) is not int for v in values) or min(values[:2])<0 or min(values[2:])<1:raise ValueError('invalid_reference_cell_geometry')
        r,c,rs,cs=values
        if r+rs>parent['row_count'] or c+cs>parent['column_count']:raise ValueError('reference_cell_outside_grid')
        slots={(a,b) for a in range(r,r+rs) for b in range(c,c+cs)}
        used=occupied.setdefault(parent['id'],set())
        if slots & used:raise ValueError('reference_cells_overlap')
        used.update(slots)
    if confirm:
        if any(result.get('form_draft',{}).get(k) for k in ('region_dirty','relation_dirty')):
            raise ValueError('stage_or_clear_reference_form_before_confirmation')
        for region in regions:
            if region['role']=='table' and len(occupied.get(region['id'],set()))!=region['row_count']*region['column_count']:
                raise ValueError('complete_reference_table_cells_or_keep_pending')
    link_ids=set()
    order_edges={}
    for link in relations:
        if not isinstance(link,dict):raise ValueError('invalid_reference_relation')
        if any(not isinstance(link.get(k),list) or any(not isinstance(v,str) for v in link[k]) for k in ('from_ids','to_ids')):raise ValueError('invalid_reference_relation_targets')
        if not isinstance(link.get('explanation',''),str):raise ValueError('reference_relation_evidence_must_be_text')
        identity=link.get('id')
        if not isinstance(identity,str) or not identity or identity in link_ids:raise ValueError('invalid_reference_relation_identity')
        link_ids.add(identity)
        if link.get('kind') not in LINKS or not link.get('from_ids') or not link.get('to_ids'):raise ValueError('invalid_reference_relation')
        if not set(link['from_ids']+link['to_ids'])<=by_id.keys():raise ValueError('reference_relation_target_missing')
        if set(link['from_ids']) & set(link['to_ids']):raise ValueError('reference_relation_self_link')
        if link['kind'] in {'footnote','caption'} and any(by_id[i]['role']!=link['kind'] for i in link['to_ids']):
            raise ValueError('reference_relation_target_role_mismatch')
        if link['kind'] in {'reading_order','continuation'}:
            for identity in link['from_ids']:order_edges.setdefault(identity,set()).update(link['to_ids'])
        if confirm and not str(link.get('explanation','')).strip():raise ValueError('reference_relation_evidence_required')
    remaining=set(order_edges)|{i for targets in order_edges.values() for i in targets}
    while remaining:
        roots=remaining-{i for source,targets in order_edges.items() if source in remaining for i in targets}
        if not roots:raise ValueError('reference_order_cycle')
        remaining-=roots
    if result.get('prior_exposure') not in {'unknown','source_only','seen_outputs'}:raise ValueError('record_prior_reference_exposure')
    survey=result.get('survey',{})
    if not isinstance(survey,dict):raise ValueError('invalid_reference_survey')
    result['survey']=survey
    if confirm:
        if result.get('prior_exposure')=='unknown':raise ValueError('record_prior_reference_exposure_before_confirmation')
        if not all(survey.get(k) is True for k in ('content','structure','relationships')) or str(result.get('unresolved','')).strip():
            raise ValueError('complete_original_survey_or_keep_reference_pending')
        if not str(result.get('note','')).strip():raise ValueError('reference_confirmation_note_required')
        if not any(r['page_index']==task['page_index'] for r in regions) and survey.get('blank_page') is not True:
            raise ValueError('annotate_original_regions_or_confirm_blank_page')
        if survey.get('blank_page') and any(r['page_index']==task['page_index'] for r in regions):raise ValueError('blank_page_conflicts_with_reference_regions')
    return result


def apply(store, request, *, source, dimensions=None, study_origin='operator_submission', assert_current=lambda:None):
    with store.transaction() as db:
        replay=store._request(db,request)
        if replay is not None:return replay
        row=db.execute('SELECT data FROM documents WHERE id=?',(request['document_id'],)).fetchone()
        doc=json.loads(row[0]) if row else {}
        if (not doc.get('eligible') or source['content_hash']!=request['source_sha256']
                or doc.get('source',{}).get('content_hash')!=source['content_hash'] or source.get('file_format')!='pdf'):
            raise ValueError('reference_source_is_not_current_and_eligible')
        action=request['action'];now=datetime.now(timezone.utc).isoformat();before=None
        if action=='create':
            p=request.get('page_index');support=request.get('supporting_pages',[])
            if not isinstance(support,list) or any(type(x) is not int for x in [p,*support]):raise ValueError('choose_valid_bounded_reference_pages')
            pages=[p,*support]
            if (len(pages)>3 or len(set(pages))!=len(pages) or any(type(x) is not int or not 0<=x<doc.get('total_pages',0) for x in pages)
                    or dimensions is None or set(dimensions)!=set(map(str,pages))):raise ValueError('choose_valid_bounded_reference_pages')
            initialize(db)
            task=dict(id='reference:'+request['request_id'],document_id=doc['id'],source=deepcopy(source),
                page_index=p,supporting_pages=support,dimensions=dimensions,actor=request['actor'],revision=1,status='draft',
                created_at=now,study_origin=study_origin,purpose='development',qualification='unqualified',
                body=dict(regions=[],relations=[],survey={},prior_exposure='unknown',assistance='',unresolved='',note=''))
        else:
            task=_load(db,request['reference_id']);before=deepcopy(task)
            if task['document_id']!=doc['id'] or task['source']['content_hash']!=source['content_hash']:raise ValueError('reference_source_version_changed')
            if task['actor']!=request['actor']:raise ValueError('reference_draft_belongs_to_another_operator')
            if request.get('guard')!=digest(task):raise ValueError('reference_changed_reload_and_compare')
            if action=='revise':
                if task['status']!='reference_saved' or not str(request.get('note','')).strip():raise ValueError('saved_reference_revision_reason_required')
                task['status']='draft';task['assessment_stale']=True
                task['body']['note']=request['note'];task['body']['survey']={}
            elif action in {'save','confirm'}:
                if task['status']!='draft':raise ValueError('start_a_new_reference_revision_before_editing')
                task['body']=_validate(request['body'],task,confirm=action=='confirm')
                if action=='confirm':
                    task['status']='reference_saved'
                    reference=dict(schema='pdf-source-reference/1',status='frozen_candidate',source_sha256=source['content_hash'],
                        pages=[task['page_index']],supporting_pages=task['supporting_pages'],page_dimensions=task['dimensions'],regions=task['body']['regions'],
                        relations=task['body']['relations'],origin=task['study_origin'],confirmed_by=request['actor'],confirmed_at=now,
                        prior_exposure=task['body']['prior_exposure'],assistance=task['body']['assistance'],note=task['body']['note'],
                        page_survey=[dict(page_index=task['page_index'],complete=True,blank_page=task['body']['survey'].get('blank_page',False),dimensions=['content','structure','relationships'],unverified_regions=[])])
                    task['reference']=reference;task['reference_sha256']=digest(reference)
            else:raise ValueError('unknown_reference_action')
            task['revision']+=1
        assert_current()
        event=dict(action=action,actor=request['actor'],at=now,request_id=request['request_id'],before=before,after=deepcopy(task))
        db.execute('INSERT OR REPLACE INTO source_reference_tasks VALUES(?,?,?)',(task['id'],doc['id'],encoded(task)))
        db.execute('INSERT INTO source_reference_events(reference_id,data) VALUES(?,?)',(task['id'],encoded(event)))
        return store._receipt(db,request,dict(status='saved',reference_id=task['id'],revision=task['revision'],
            reference_status=task['status'],guard=digest(task),qualification='unqualified',independent_acceptance='not_assessed'))
