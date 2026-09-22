"""Logical Requirement exchange with immutable evidence and additive imports.

Actor bundles are atomic merge units. Import retains authorship and rebinds local
revision numbers if needed, while keeping the complete received artifact intact.
No credentials, SQL, database files, schedules or working copies are accepted.
"""
from copy import deepcopy
from contextlib import nullcontext
import json
import uuid
from backend.shared.identities import named
from backend.shared.records import fingerprint, encoded, now
from backend.system3.requirements import Requirements, FIELDS, RELATIONS, leaves
from backend.system3 import requirement_structure as tree_structure
from backend.system3.interpretations import Interpretations, KEYS, checking_logic
from backend.system3 import interpretation_lineage as lineage
from backend.system3.requirement_relations import project as project_relations
from backend.system3.check_design import validate_design, logic_fields, concept_issues
from backend.system3.interpretation_continuity import review_ready

SCHEMA='requirement-delivery/2'
RELATIONSHIP_SCHEMA='requirement-delivery/3'
LEGACY_SCHEMA='requirement-delivery/1'
SHARED_SCHEMA='requirement-delivery/4'
SHARED_KEY='requirements:shared'


def key_for(actor):return SHARED_KEY if actor == 'shared' else 'requirements:'+fingerprint(named(actor))


class Delivery:
    def __init__(self,c):
        self.c=c;self.s=Interpretations(c);self.r=self.s.r
        with c.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS requirement_delivery_receipts(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requirement_delivery_archives(digest TEXT PRIMARY KEY,body TEXT NOT NULL);
            ''')

    def capture(self, connection=None):
        items=[]
        with (nullcontext(connection) if connection is not None else self.c.db()) as db:
            actors=[r[0] for r in db.execute('SELECT DISTINCT actor FROM requirement_sessions ORDER BY actor')]
            for actor in actors:
                sessions=[];interpretations=[]
                for sid,raw in db.execute('SELECT id,body FROM requirement_sessions WHERE actor=? ORDER BY id',(actor,)):
                    steps=[dict(document=json.loads(r[0]),action=r[1],at=r[2]) for r in db.execute('SELECT body,action,at FROM requirement_steps WHERE session_id=? ORDER BY revision',(sid,))]
                    sessions.append(dict(document=json.loads(raw),steps=steps))
                for uid,revision in db.execute('SELECT unit_id,revision FROM requirement_interpretations WHERE actor=? ORDER BY unit_id',(actor,)):
                    lineage.backfill(db,actor,uid);history=[]
                    for raw,action,at in db.execute('SELECT body,action,at FROM interpretation_history WHERE actor=? AND unit_id=? ORDER BY revision',(actor,uid)):
                        d=json.loads(raw);t=lineage.read(db,actor,uid,d['revision'])
                        if t['status']!='saved':raise ValueError('A saved interpretation has no source-bound history. Repair its provenance before export.')
                        anchor=dict(session_id=t['session_id'],session_revision=t['session_revision'],material_id=t['material_id'],material_revision=t['material_revision'],block_id=t['block_id'],source=t['source'],chapter=t['chapter'],span=[t['start'],t['end']],text=t['original_text'],source_refs=t['source_refs'],quality=t['quality'],**({'source_segments':t['source_segments']} if t.get('source_segments') else {}))
                        history.append(dict(document=d,action=action,at=at,anchor=anchor,citations=d.get('context_snapshot',{}).get('citations',[])))
                    interpretations.append(dict(unit_id=uid,head_revision=revision,history=history))
                # Candidate output and its frozen context travel as evidence, never as an active request.
                candidates=[json.loads(r[0]) for r in db.execute('SELECT body FROM interpretation_runs WHERE actor=? ORDER BY id',(actor,))]
                has_groups=any(step['document'].get('structures') for item in sessions for step in item['steps'])
                has_relationships=any(step['document'].get('structure_schema')==tree_structure.RELATIONSHIP_SCHEMA for item in sessions for step in item['steps'])
                value=dict(schema=RELATIONSHIP_SCHEMA if has_relationships else SCHEMA if has_groups else LEGACY_SCHEMA,actor=actor,sessions=sessions,interpretations=interpretations,candidates=candidates)
                items.append(dict(key=key_for(actor),value=value,branch=actor,actor=actor,guard=fingerprint(value)))
        if self.r.shared and items:
            value = dict(schema=SHARED_SCHEMA, actor='shared', sessions=[], interpretations=[], candidates=[], owners={})
            for item in items:
                bundle = item['value']; owner = bundle['actor']
                for session in bundle['sessions']:
                    value['owners'][session['document']['id']] = owner
                value['sessions'].extend(bundle['sessions'])
                value['interpretations'].extend(bundle['interpretations'])
                value['candidates'].extend(dict(run, requested_by=owner) for run in bundle['candidates'])
            return [dict(key=SHARED_KEY, value=value, branch='shared', actor='shared', guard=fingerprint(value))]
        return items

    def validate(self,value):
        try:self._validate(value)
        except (KeyError,TypeError,IndexError,AttributeError,RecursionError) as e:raise ValueError('Invalid Requirement delivery structure.') from e
        return value

    def _validate(self,v):
        shared=isinstance(v,dict) and v.get('schema')==SHARED_SCHEMA
        keys={'schema','actor','sessions','interpretations','candidates'} | ({'owners'} if shared else set())
        if not isinstance(v,dict) or set(v)!=keys or v['schema'] not in (SCHEMA,LEGACY_SCHEMA,RELATIONSHIP_SCHEMA,SHARED_SCHEMA):raise ValueError('Unsupported Requirement delivery.')
        if shared:
            if v['actor']!='shared' or not isinstance(v['owners'],dict):raise ValueError('Invalid shared Requirement ownership.')
            for owner in v['owners'].values():named(owner)
        else:named(v['actor'])
        for k in ('sessions','interpretations','candidates'):
            if not isinstance(v[k],list) or len(v[k])>10000:raise ValueError('Requirement delivery exceeds the supported size.')
        if len(encoded(v).encode())>64000000:raise ValueError('Requirement delivery exceeds the supported size.')
        steps={};current={};uids=set()
        for item in v['sessions']:
            if set(item)!={'document','steps'} or not isinstance(item['steps'],list) or len(item['steps'])>10000:raise ValueError('Invalid splitting history.')
            d=item['document'];sid=d['id'];uuid.UUID(sid)
            if sid in current:raise ValueError('Duplicate splitting session.')
            current[sid]=d
            for step in item['steps']:
                if set(step)!={'document','action','at'} or not isinstance(step['action'],str) or not isinstance(step['at'],str):raise ValueError('Invalid splitting step.')
                x=step['document'];rev=x['revision']
                if x['id']!=sid or type(rev) is not int or rev<1 or (sid,rev) in steps:raise ValueError('Invalid splitting version.')
                if not isinstance(x['text'],str) or len(x['text'])>100000 or not isinstance(x['units'],dict) or not 1<=len(x['units'])<=1000:raise ValueError('Invalid source passage.')
                if x['material_id']!=d['material_id'] or x['block_id']!=d['block_id'] or x['text']!=d['text'] or x['source']!=d['source']:raise ValueError('A splitting session cannot change its source binding.')
                if x.get('source_segments'):
                    parts=x['source_segments'];offset=0
                    if not isinstance(parts,list) or len(parts)>100:raise ValueError('Invalid source segments.')
                    ids=set()
                    for part in parts:
                        if set(part)!={'block_id','start','end','text','source_refs'} or part['block_id'] in ids or part['start']!=offset or part['end']!=offset+len(part['text']) or not isinstance(part['source_refs'],list):raise ValueError('Invalid source segment range.')
                        ids.add(part['block_id']);offset=part['end']+2
                    if '\n\n'.join(part['text'] for part in parts)!=x['text'] or parts!=d.get('source_segments'):raise ValueError('Source segment binding differs.')
                if x.get('structures') and v['schema']==LEGACY_SCHEMA:raise ValueError('Unified groups require Requirement delivery version 2 or later.')
                if x.get('structure_schema')==tree_structure.RELATIONSHIP_SCHEMA and v['schema'] not in (RELATIONSHIP_SCHEMA,SHARED_SCHEMA):raise ValueError('Group relationships require Requirement delivery version 3.')
                tree_structure.validate(x)
                leaves(x['roots'])
                for uid,u in x['units'].items():
                    uuid.UUID(uid)
                    if u['id']!=uid:raise ValueError('Requirement identity differs.')
                    a,b=x['spans'][uid]
                    if type(a) is not int or type(b) is not int or not 0<=a<b<=len(x['text']) or x['text'][a:b]!=u['text']:raise ValueError('Requirement source range differs.')
                    for field in FIELDS:
                        if u[field] is not None and (not isinstance(u[field],str) or u[field] not in u['text']):raise ValueError('Invalid source field.')
                    for field,span in x.get('field_spans',{}).get(uid,{}).items():
                        a,b=span
                        if field not in FIELDS or type(a) is not int or type(b) is not int or not 0<=a<b<=len(u['text']) or u['text'][a:b]!=u[field]:raise ValueError('Invalid field anchor.')
                    for rel in RELATIONS:leaves(u[rel])
                if not set(x['done'])<=set(x['units']):raise ValueError('Unknown completed Requirement.')
                steps[sid,rev]=x
            if steps.get((sid,d['revision']))!=d:raise ValueError('Current splitting does not match its immutable history.')
            if uids&set(d['units']):raise ValueError('Requirement identity occurs in more than one session.')
            uids.update(d['units'])
        if shared and set(v['owners'])!=set(current):raise ValueError('Missing Requirement ownership.')
        graph={uid:(tree_structure.references(d['structures'][uid]) if uid in d.get('structures',{}) else sum((leaves(u[r]) for r in RELATIONS),[])) for d in current.values() if not d.get('deleted') for uid,u in d['units'].items()}
        visiting=set();seen=set()
        def walk(uid):
            if uid not in graph:raise ValueError('A Requirement relationship is missing its target.')
            if uid in visiting:raise ValueError('Circular Requirement relationship.')
            if uid in seen:return
            visiting.add(uid)
            for child in graph[uid]:walk(child)
            visiting.remove(uid);seen.add(uid)
        for uid in graph:walk(uid)
        for d in steps.values():
            for uid,ref in d.get('reference_evidence',{}).items():
                bound=steps.get((ref['session_id'],ref['revision']))
                if not bound or uid not in bound['units'] or bound['units'][uid]['text']!=ref['text']:raise ValueError('Cross-reference evidence is missing or changed.')
        seen_units=set()
        for item in v['interpretations']:
            if set(item)!={'unit_id','head_revision','history'} or item['unit_id'] in seen_units:raise ValueError('Duplicate interpretation.')
            seen_units.add(item['unit_id']);heads=[]
            if not isinstance(item['history'],list) or len(item['history'])>10000:raise ValueError('Invalid interpretation history.')
            for entry in item['history']:
                if set(entry)!={'document','action','at','anchor','citations'}:raise ValueError('Invalid interpretation evidence.')
                d=entry['document'];a=entry['anchor'];split=steps.get((d['session_id'],d['session_revision']))
                if not split or d['unit_id'] not in split['units'] or d['unit_id']!=item['unit_id'] or d['actor']!=(v['owners'].get(d['session_id']) if shared else v['actor']) or d['schema']!='requirement-interpretation/1':raise ValueError('Interpretation origin differs.')
                if type(d['revision']) is not int or d['revision']<1 or d['revision'] in heads:raise ValueError('Invalid interpretation version.')
                heads.append(d['revision'])
                expected=lineage.source_anchor(d,split,a['quality'])
                # Material revision may advance without changing the source passage.
                expected['material_revision']=a['material_revision']
                if a!=expected:raise ValueError('Interpretation source anchor differs from the saved splitting.')
                ctx={'citations':entry['citations']}
                if ctx['citations']:
                    self.s.validate_fields(d['fields'],ctx)
                else:
                    # Legacy citations do not carry complete quoted blocks. Retain
                    # their evidence with that limitation, never upgrade their quality.
                    legacy=deepcopy(d['fields'])
                    for f in legacy.values():f['references']=[];f['basis']='interpretation'
                    self.s.validate_fields(legacy,ctx)
                validate_design(d.get('check_design'), ctx['citations'] if ctx['citations'] else None)
                logic=d.get('logic',{})
                structure=logic.get('source_structure',{})
                if structure.get('requirement') is not None and structure['requirement']!=split['units'][d['unit_id']]:raise ValueError('Checking logic points to different Requirement structure.')
                if (structure.get('structure') is not None and structure['structure']!=tree_structure.legacy(split,d['unit_id'])) or (d['unit_id'] in split.get('structures',{}) and structure.get('structure') is None):raise ValueError('Checking logic differs from the saved group structure.')
                if logic!=checking_logic(d['fields'],logic.get('exceptions',[]),structure,
                    design=d.get('check_design'), context_fingerprint=d.get('context_fingerprint',''), catalog=d.get('catalog_snapshot')):raise ValueError('Imported checking logic must be the deterministic, non-executable design.')
                if type(d.get('reviewed')) is not bool or d['reviewed'] and (not all(review_ready(f) for f in logic_fields(d['fields'],d.get('check_design')).values()) or concept_issues(d.get('check_design') or {})):raise ValueError('Invalid interpretation review state.')
            if item['head_revision'] not in heads:raise ValueError('Missing interpretation head.')
        seen_runs=set()
        for run in v['candidates']:
            if shared:named(run.get('requested_by'))
            uuid.UUID(run['id'])
            if run['id'] in seen_runs or run['unit_id'] not in {u for d in steps.values() for u in d['units']}:raise ValueError('Invalid candidate identity.')
            seen_runs.add(run['id'])
            if run.get('check_design'): validate_design(run['check_design'], run['context']['citations'])
            if run.get('suggestions'):
                fields={k:run['suggestions'].get(k,dict(value='',basis='unresolved',references=[],gaps=[])) for k in KEYS}
                self.s.validate_fields(fields,run['context'])

    def apply(self,value,request_id,expected_digest=False):
        self.validate(value);actor=value['actor'];digest=fingerprint(value)
        owners=value.get('owners', {s['document']['id']:actor for s in value['sessions']})
        with self.c.lock,self.c.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT body FROM requirement_delivery_receipts WHERE id=?',(request_id,)).fetchone()
            if old:return json.loads(old[0])
            if self.r.shared and value['schema']!=SHARED_SCHEMA and self.capture(db):
                raise ValueError('This older package uses private Requirement versions. Re-export it with the updated app before merging into existing shared work.')
            if expected_digest is not False:
                current=next((item['guard'] for item in self.capture(db) if item['actor']==actor),None)
                if current!=expected_digest:raise ValueError('Requirement work changed after the import preview. Refresh the comparison.')
            db.execute('INSERT OR IGNORE INTO requirement_delivery_archives VALUES(?,?)',(digest,encoded(value)))
            # Retain unselected local sessions. A received version never deletes work.
            revision_map={};pending=[];heads={}
            for item in value['sessions']:
                sid=item['document']['id'];old=db.execute('SELECT actor,body FROM requirement_sessions WHERE id=?',(sid,)).fetchone()
                if old and old[0]!=owners[sid]:raise ValueError('Splitting identity belongs to another reviewer.')
                maximum=db.execute('SELECT MAX(revision) FROM requirement_steps WHERE session_id=?',(sid,)).fetchone()[0] or 0
                for step in item['steps']:
                    d=step['document'];prior=db.execute('SELECT body FROM requirement_steps WHERE session_id=? AND revision=?',(sid,d['revision'])).fetchone()
                    if prior and json.loads(prior[0])==d:revision_map[sid,d['revision']]=d['revision']
                    else:
                        maximum+=1;revision_map[sid,d['revision']]=maximum;pending.append((step,maximum))
                head=item['document']
                # Append the selected current version after all retained steps,
                # so subsequent manual edits cannot collide with older history.
                maximum+=1;revision_map[sid,head['revision']]=maximum
                pending.append((dict(document=head,action='synchronize',at=now()),maximum));heads[sid]=head
            def rebound(d,revision):
                d=deepcopy(d);original=d['revision'];d['revision']=revision
                for ref in d.get('reference_evidence',{}).values():ref['revision']=revision_map[ref['session_id'],ref['revision']]
                if revision!=original:d['delivery_origin']=dict(digest=digest,revision=original)
                return d
            for step,revision in pending:
                d=rebound(step['document'],revision)
                db.execute('INSERT INTO requirement_steps VALUES(?,?,?,?,?)',(d['id'],revision,encoded(d),step['action'],step['at']))
            for sid,raw in heads.items():
                d=rebound(raw,revision_map[sid,raw['revision']])
                db.execute('INSERT INTO requirement_sessions VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(sid,owners[sid],d['material_id'],d['revision'],encoded(d)))
                db.execute('DELETE FROM requirement_units WHERE session_id=?',(sid,))
                for uid,u in ([] if d.get('deleted') else d['units'].items()):
                    db.execute('INSERT INTO requirement_units VALUES(?,?,?,?,?,?,?)',(uid,sid,owners[sid],d['material_id'],u['text'],d['chapter'],encoded(dict(source=d['source'],source_refs=d['source_refs'],block_id=d['block_id'],span=d['spans'][uid],material_revision=d['material_revision'],source_segments=d.get('source_segments',[])))))
            for sid in heads:
                d=self.r.load(db,owners[sid],sid);self.r.validate(db,owners[sid],d);project_relations(db,d)
            for item in value['interpretations']:
                owner=item['history'][0]['document']['actor']
                uid=item['unit_id'];maximum=db.execute('SELECT MAX(revision) FROM interpretation_history WHERE actor=? AND unit_id=?',(owner,uid)).fetchone()[0] or 0
                ordered=sorted(item['history'],key=lambda e:(e['document']['revision']==item['head_revision'],e['document']['revision']))
                for entry in ordered:
                    original=entry['document'];d=deepcopy(original);maximum+=1;d['revision']=maximum
                    d['session_revision']=revision_map[d['session_id'],d['session_revision']]
                    d['delivery_origin']=dict(digest=digest,actor=owner,revision=original['revision'])
                    # Keep the original reviewed evidence, but require local context
                    # review if the saved dependency fingerprint no longer matches.
                    db.execute('INSERT INTO interpretation_history VALUES(?,?,?,?,?,?)',(owner,uid,maximum,encoded(d),entry['action'],entry['at']))
                    a=deepcopy(entry['anchor']);a['session_revision']=d['session_revision']
                    lineage.project(db,d,a,entry['citations'])
                db.execute('INSERT OR REPLACE INTO requirement_interpretations VALUES(?,?,?,?)',(owner,uid,maximum,encoded(d)))
            for run in value['candidates']:
                # Candidate identities are immutable; conflicting candidates remain
                # in the received archive rather than overwriting local evidence.
                db.execute('INSERT OR IGNORE INTO interpretation_runs VALUES(?,?,?)',(run.get('requested_by',actor),run['id'],encoded(run)))
            receipt=dict(status='synchronized',actor=actor,sessions=len(heads),interpretations=len(value['interpretations']),archive_digest=digest)
            db.execute('INSERT INTO requirement_delivery_receipts VALUES(?,?)',(request_id,encoded(receipt)))
        return receipt
