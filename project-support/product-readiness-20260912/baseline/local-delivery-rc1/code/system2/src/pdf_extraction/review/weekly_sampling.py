"""Durable A/B monitoring samples. Never a calibration or acceptance dataset."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import secrets

from ..contracts.hashing import digest, encoded
from ..verification.acceptance import accepted
from . import original_sampling, effective, repairs

SCHEMA = 'weekly-original-and-classification/1'
TARGETS = {'A':20, 'B':5}


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS sampling_batches(week TEXT,stage TEXT,data TEXT NOT NULL,PRIMARY KEY(week,stage))')
    db.execute('CREATE TABLE IF NOT EXISTS sampling_items(id TEXT PRIMARY KEY,week TEXT,stage TEXT,status TEXT,revision INTEGER,data TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS sampling_pending ON sampling_items(status,week,stage)')


def exists(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='sampling_batches'").fetchone())


def week_of(now, zone):
    if now.tzinfo is None: raise ValueError('sampling_clock_requires_timezone')
    day=now.astimezone(ZoneInfo(zone)).date()
    return (day-timedelta(days=day.weekday())).isoformat()


def mapped(doc, scope):
    by_id={u['id']:u for u in doc['units']}
    return [dict(unit_id=u['id'],unit_version=u['version'],view=effective.resolve(u,by_id),
                 content_status=u['content_status'],requirement_status=u['requirement_status'])
            for u in doc['units'] if u['kind']!='coverage' and not u.get('superseded_by') and not u.get('evidence_only')
            and original_sampling.matches(scope,u.get('reviewed_references',u['original'].get('references',[])))]


def create_due(store, source_root, *, enabled=False, zone='Europe/Oslo', now=None, assert_current=lambda:None):
    """Caller explicitly owns activation. Read/preview endpoints never create batches."""
    if not enabled:return {'status':'disabled','targets':TARGETS}
    week=week_of(now or datetime.now(timezone.utc),zone)
    with store.connect() as db:
        if exists(db) and db.execute('SELECT COUNT(*) FROM sampling_batches WHERE week=?',(week,)).fetchone()[0]==2:
            return {'status':'already_created','week':week}
        db.execute('BEGIN')
        meta=[json.loads(r[0]) for r in db.execute('SELECT data FROM documents ORDER BY id')]
        basis={d['id']:(d['revision'],d['source']['content_hash']) for d in meta}
    choices={'A':[],'B':[]};errors=[];documents={};seed=secrets.token_hex(16)
    source_root=Path(source_root).resolve()
    for doc in meta:
        if not doc['eligible']:continue
        try:
            path=(source_root/doc['source']['relative_path']).resolve()
            if not path.is_relative_to(source_root):raise ValueError('source_outside_governed_root')
            index=original_sampling.catalog(path,doc['source']['content_hash'])
            choices['A'].extend({'document_id':doc['id'],'source':doc['source'],'scope':scope,
                'title':scope['title'],'key':doc['id']+':'+scope['id']} for scope in index['scopes'])
        except Exception as error:
            errors.append({'source_id':doc['source']['source_id'],'reason':type(error).__name__+': '+str(error)})
        with store.connect() as db:
            rows=db.execute("SELECT data FROM review_units WHERE document_id=? AND content_ok=1 AND requirement_ok=1 AND kind!='coverage'",(doc['id'],)).fetchall()
            if rows:documents[doc['id']]=store._load(db,doc['id'])
        for raw in rows:
            unit=json.loads(raw[0])
            if unit.get('superseded_by') or unit.get('evidence_only') or unit.get('table_assembly') or unit['classification'] not in {'requirement','context','non_requirement'}:continue
            choices['B'].append({'document_id':doc['id'],'source':doc['source'],'unit_id':unit['id'],
                'unit_version':unit['version'],'classification':unit['classification'],
                'stratum':'requirement' if unit['classification']=='requirement' else 'non_requirement',
                'key':doc['id']+':'+unit['id']})
    selected={stage:sorted(pool,key=lambda p:digest([seed,stage,p['key']])) for stage,pool in choices.items()}
    selected['A']=selected['A'][:TARGETS['A']]
    positive=[c for c in selected['B'] if c['stratum']=='requirement']
    negative=[c for c in selected['B'] if c['stratum']=='non_requirement']
    balanced=positive[:3]+negative[:2]
    used={c['key'] for c in balanced}
    selected['B']=balanced+[c for c in selected['B'] if c['key'] not in used][:TARGETS['B']-len(balanced)]
    items=[]
    for stage in TARGETS:
        for candidate in selected[stage]:
            did=candidate['document_id']
            if did not in documents:
                with store.connect() as db:documents[did]=store._load(db,did)
            doc=documents[did]
            if (doc['revision'],doc['source']['content_hash'])!=basis[did]:raise ValueError('sampling_results_changed_during_selection')
            item=deepcopy(candidate);item.pop('key')
            if stage=='A':
                item['extracted']=mapped(doc,item['scope'])
                item['processed']=doc.get('parser_complete',False) or item['scope'].get('page_index') in doc.get('processed_pages',[])
                item['title']=item['scope']['title']
            else:
                unit=next(u for u in doc['units'] if u['id']==item['unit_id'])
                item['judgment']=deepcopy(unit)
                item['effective']=effective.resolve(unit,{u['id']:u for u in doc['units']})
                item['title']=item['effective']['fields'].get('identifier') or item['effective']['fields'].get('title') or item['unit_id']
            item.update(id=digest([SCHEMA,week,stage,candidate['key']])[:32],week=week,stage=stage,
                        status='pending',revision=1,verdict=None,actor=None,history=[])
            item['snapshot_sha256']=digest(item)
            items.append(item)
    assert_current()
    with store.transaction() as db:
        initialize(db)
        if db.execute('SELECT 1 FROM sampling_batches WHERE week=?',(week,)).fetchone():
            return {'status':'already_created','week':week}
        for did,expected in basis.items():
            row=db.execute('SELECT data FROM documents WHERE id=?',(did,)).fetchone()
            current=json.loads(row[0]) if row else None
            if not current or (current['revision'],current['source']['content_hash'])!=expected:
                raise ValueError('sampling_results_changed_during_selection')
        for stage,target in TARGETS.items():
            batch={'schema':SCHEMA,'week':week,'stage':stage,'timezone':zone,'requested':target,
                'sampled':len(selected[stage]),'population':len(choices[stage]),'seed':seed,
                'selection_method':'random_order' if stage=='A' else 'stratified_3_positive_2_negative_with_fill',
                'strata':({'requirement':len(positive),'non_requirement':len(negative)} if stage=='B' else {}),
                'missing_strata':([name for name,pool in [('requirement',positive),('non_requirement',negative)] if not pool] if stage=='B' else []),
                'source_catalog_errors':errors if stage=='A' else [],
                'created_at':datetime.now(timezone.utc).isoformat(),'purpose':'ongoing_monitoring_not_independent_acceptance'}
            db.execute('INSERT INTO sampling_batches VALUES(?,?,?)',(week,stage,encoded(batch)))
        for item in items:
            db.execute('INSERT INTO sampling_items VALUES(?,?,?,?,?,?)',(item['id'],week,item['stage'],item['status'],1,encoded(item)))
        store._event(db,None,'weekly_sampling_created',{'week':week,'targets':TARGETS,'sampled':{s:len(selected[s]) for s in TARGETS}})
    return {'status':'created','week':week,'sampled':{s:len(selected[s]) for s in TARGETS}}


def result_state(store, db, item):
    doc=store._load(db,item['document_id'])
    by_id={u['id']:u for u in doc['units']}
    units=mapped(doc,item['scope']) if item['stage']=='A' else [by_id[item['unit_id']]] if item['unit_id'] in by_id else []
    return doc, {'eligible':doc['eligible'],'source_sha256':doc['source']['content_hash'],
        'revision':doc['revision'],'units':units}


def read(store, item_id=None):
    with store.connect() as db:
        if not exists(db):return {'schema':SCHEMA,'targets':TARGETS,'batches':[]}
        if item_id:
            row=db.execute('SELECT data FROM sampling_items WHERE id=?',(item_id,)).fetchone()
            if not row:raise ValueError('weekly_sample_not_found')
            item=json.loads(row[0]);item['guard']=digest(item)
            _,current=result_state(store,db,item)
            item['current']=current;item['result_guard']=digest(current)
            return item
        batches=[]
        for row in db.execute('SELECT data FROM sampling_batches ORDER BY week DESC,stage'):
            batch=json.loads(row[0])
            items=[dict(r) for r in db.execute("""SELECT id,status,revision,json_extract(data,'$.title') AS title,
                json_extract(data,'$.source.source_id') AS source_id,json_extract(data,'$.verdict') AS verdict,
                json_extract(data,'$.actor') AS actor,json_extract(data,'$.classification') AS classification
                FROM sampling_items WHERE week=? AND stage=? ORDER BY rowid""",(batch['week'],batch['stage']))]
            pending=sum(i['status']!='complete' for i in items)
            short=max(0,batch['requested']-len(items))
            complete=not pending and not short and not batch['missing_strata'] and not batch['source_catalog_errors']
            batch.update(items=items,pending=pending,shortfall=short,complete=complete,
                agreement=(sum(i['verdict']=='CORRECT' for i in items)/len(items) if complete and items else None))
            batches.append(batch)
        return {'schema':SCHEMA,'targets':TARGETS,'batches':batches}


def open_finding(doc, item, note):
    """Bind a reported omission to original scope, even if no extracted unit exists."""
    code='weekly_qa:'+item['id']
    by_id={u['id']:u for u in doc['units']}
    if item['stage']=='B':
        target=by_id.get(item['unit_id'])
        if not target:raise ValueError('sampled_judgment_no_longer_exists')
        target['requirement_blockers']=list(dict.fromkeys(target.get('requirement_blockers',[])+[code]))
        target.setdefault('weekly_findings',{})[item['id']]={'note':note,'classification':item['classification']}
        target.update(requirement_human=False,requirement_parts=[])
        item['repair_unit_id']=target['id']
        return [target['id']]
    scope=item['scope']
    cid=('coverage:pdf-page:'+str(scope['page_index']) if scope.get('page_index') is not None
         else 'coverage:weekly-original:'+scope['id'])
    if cid not in by_id:
        target={'id':cid,'kind':'coverage','chapter':scope['title'],
            'original':{'fields':{'title':scope['title'],'body':'Inspect the full original scope and correct missing or inaccurate content.'},
                'references':deepcopy(scope['references']),'structure':[]},
            'version':1,'edits':{},'content_parts':[],'dependencies':[],'blockers':[],
            'content_status':'pending','requirement_status':'blocked','classification':'undetermined',
            'coverage_scope':'pdf_page' if scope.get('page_index') is not None else 'original_positions',
            'scope_version':'pdf-pages/1' if scope.get('page_index') is not None else original_sampling.SCHEMA}
        doc['units'].append(target);by_id[cid]=target
    target=by_id[cid]
    target['blockers']=list(dict.fromkeys(target.get('blockers',[])+[code]))
    target.setdefault('weekly_findings',{})[item['id']]={'note':note,'scope':deepcopy(scope)}
    for unit in doc['units']:
        if unit['kind']!='coverage' and original_sampling.matches(scope,unit.get('reviewed_references',unit['original'].get('references',[]))):
            unit['dependencies']=list(dict.fromkeys(unit.get('dependencies',[])+[cid]))
    item['repair_unit_id']=cid
    return repairs.invalidate(by_id,[cid])


def decide(store, request):
    with store.transaction() as db:
        replay=store._request(db,request)
        if replay is not None:return replay
        if not exists(db):raise ValueError('weekly_sample_not_found')
        row=db.execute('SELECT data FROM sampling_items WHERE id=?',(request['item_id'],)).fetchone()
        if not row:raise ValueError('weekly_sample_not_found')
        item=json.loads(row[0])
        if request.get('guard')!=digest(item):raise ValueError('stale_weekly_sample')
        doc,current=result_state(store,db,item)
        if request.get('result_guard')!=digest(current):raise ValueError('weekly_result_changed_refresh_required')
        note=request.get('note','').strip()
        if not note:raise ValueError('weekly_inspection_evidence_note_required')
        action=request.get('action');verdict=request.get('verdict')
        same_source=doc['eligible'] and doc['source']['content_hash']==item['source']['content_hash']
        if action=='inspect':
            if item['status']=='complete' or item['verdict']=='INCORRECT':raise ValueError('use_finding_followup_preserve_first_verdict')
            if verdict not in {'CORRECT','INCORRECT','UNVERIFIED'}:raise ValueError('invalid_weekly_verdict')
            if not same_source and verdict!='UNVERIFIED':raise ValueError('sample_source_changed_requires_followup')
            item.update(verdict=verdict,status='complete' if verdict=='CORRECT' else 'finding_open' if verdict=='INCORRECT' else 'unverified')
            if verdict=='INCORRECT':
                affected=open_finding(doc,item,note)
                doc['revision']+=1
                store._event(db,doc['id'],'weekly_finding',{'item_id':item['id'],'actor':request['actor'],'note':note,'affected':affected})
                store._recompute(db,doc,store.policy(db));store._save(db,doc)
        elif action=='resolve':
            if item['status']!='finding_open':raise ValueError('weekly_open_finding_required')
            if not same_source:raise ValueError('sample_source_changed_requires_followup')
            by_id={u['id']:u for u in doc['units']}
            target=by_id.get(item.get('repair_unit_id'))
            code='weekly_qa:'+item['id']
            if not target or code in target.get('blockers',[])+target.get('requirement_blockers',[]):
                raise ValueError('repair_and_recheck_before_closing_weekly_finding')
            affected=([target]+[u for u in doc['units'] if u['kind']!='coverage' and not u.get('superseded_by') and original_sampling.matches(item['scope'],u.get('reviewed_references',u['original'].get('references',[])))]) if item['stage']=='A' else [target]
            if any(not accepted(u['content_status']) or u.get('drafts') or (item['stage']=='B' and not accepted(u['requirement_status'])) for u in affected):
                raise ValueError('repair_and_recheck_before_closing_weekly_finding')
            item['status']='complete'
            item['resolution']={'note':note,'revision':doc['revision'],'result_guard':digest(current)}
        else:raise ValueError('invalid_weekly_action')
        entry={'request_id':request['request_id'],'actor':request['actor'],'action':action,'verdict':verdict,
            'note':note,'at':datetime.now(timezone.utc).isoformat(),'result_guard':digest(current),'document_revision':doc['revision']}
        item['history'].append(entry);item['actor']=request['actor'];item['revision']+=1
        db.execute('UPDATE sampling_items SET status=?,revision=?,data=? WHERE id=?',(item['status'],item['revision'],encoded(item),item['id']))
        store._event(db,doc['id'],'weekly_inspection',dict(entry,item_id=item['id'],status=item['status']))
        return store._receipt(db,request,{'status':'applied','item_id':item['id'],'item_status':item['status'],'revision':item['revision']})
