"""Durable working copies and conservative, source-bound change impact."""
from copy import deepcopy
import json
import uuid
from .collaboration import named, now, fingerprint, encoded

STATES = ('specified', 'not_stated', 'unresolved')


def field_state(f):
    return f.get('state', 'specified' if f.get('value', '').strip() and f.get('basis') != 'unresolved' else 'unresolved')


def review_ready(f):
    state = field_state(f)
    return not f.get('gaps') and ((state == 'specified' and bool(f.get('value', '').strip()) and f.get('basis') != 'unresolved') or
        (state == 'not_stated' and bool(f.get('absence_reason', '').strip()) and not f.get('value', '').strip()))


def context_snapshot(ctx):
    return dict(citations=deepcopy(ctx['citations']), materials=deepcopy(ctx['materials']),
                sessions=deepcopy(ctx['sessions']), origin=deepcopy(ctx['origin']))


def impact(service, actor, doc, material_cache=None):
    """Compare saved dependencies, never relocate a changed quote by guessing."""
    saved = doc.get('context_snapshot')
    if not saved:
        return {'status': 'legacy', 'items': [], 'message': 'This version predates detailed dependency capture. Review all six fields against the current material.'}
    current = {}; unavailable = []; context_changed=False
    material_cache={} if material_cache is None else material_cache
    for old in saved['materials']:
        try:
            if old['id'] not in material_cache:material_cache[old['id']]=service.r.material(actor,old['id'])
            m=material_cache[old['id']]
            context_changed=context_changed or m['revision']!=old['revision'] or m.get('source_stale',False)!=old.get('source_stale',False)
            for b in m['blocks']:
                text = b.get('markdown', {}).get('source') or b.get('markdown_source') or b.get('text', '')
                current[old['id']+':'+b['id']] = dict(text=text, source=m['source'], source_refs=b.get('source_refs', []))
        except (ValueError, OSError):
            unavailable.append(old['id'])
    sources = {m['id']: m['source'] for m in saved['materials']}
    rule_links = {}
    def walk(n):
        if not n: return
        if 'rules' in n:
            for child in n['rules']: walk(child)
        else: rule_links.setdefault(n['interpretation_field'], []).append(n['id'])
    for n in doc.get('check_design', {}).get('groups', {}).values(): walk(n)
    items = []
    for old in saved['citations']:
        new = current.get(old['id'])
        if old.get('block_id') is None: continue  # metadata checked separately below
        if new and (new['text'], new['source'], new['source_refs']) == (old['text'], sources[old['material_id']], old.get('source_refs', [])): continue
        fields = [k for k, f in doc['fields'].items() if any(r['id'] == old['id'] for r in f['references'])]
        origin = saved['origin']; own = old['material_id'] == origin['material_id'] and old['block_id'] in [p['block_id'] for p in origin.get('source_segments',[])] + [origin['block_id']]
        if own: fields = list(doc['fields'])
        items.append(dict(citation_id=old['id'],material_id=old['material_id'],block_id=old['block_id'],
            before=old['text'],after=new['text'] if new else None,
            reason='unavailable' if old['material_id'] in unavailable else 'changed' if new else 'removed',
            unit_id=doc['unit_id'],fields=fields,rules=sorted({r for k in fields for r in rule_links.get(k, [])}),
            scope='requirement' if own else 'citation' if fields else 'context'))
    for old in saved['sessions']:
        with service.c.db() as db:row=db.execute('SELECT revision FROM requirement_sessions WHERE actor=? AND id=?',(actor,old['id'])).fetchone()
        if not row or old['revision'] != row[0]:
            items.append(dict(reason='splitting_changed',session_id=old['id'],unit_id=doc['unit_id'],fields=list(doc['fields']),rules=sorted({r for rs in rule_links.values() for r in rs}),scope='requirement'))
    # Metadata changes affect the available context even if no paragraph moved.
    if context_changed and not items:
        items.append(dict(reason='context_changed',unit_id=doc['unit_id'],fields=list(doc['fields']),rules=sorted({r for rs in rule_links.values() for r in rs}),scope='context'))
    return dict(status='changed' if items else 'current',items=items,
        message='Review affected fields and mappings. Uncited context changes still require a contextual review; no automatic semantic decision is made.')


class Drafts:
    def __init__(self, c):
        self.c = c
        with c.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS interpretation_drafts(actor TEXT NOT NULL, unit_id TEXT NOT NULL,
                revision INTEGER NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(actor,unit_id));
            CREATE TABLE IF NOT EXISTS interpretation_draft_requests(actor TEXT NOT NULL, id TEXT NOT NULL,
                digest TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(actor,id));
            ''')

    def listing(self, actor, uid=None):
        actor = named(actor)
        with self.c.db() as db:
            rows = db.execute('SELECT unit_id,revision,body,updated_at FROM interpretation_drafts WHERE actor=? ORDER BY updated_at DESC', (actor,)).fetchall()
        drafts = [dict(unit_id=u,revision=r,body=json.loads(b),updated_at=t) for u,r,b,t in rows if uid is None or u==uid]
        if uid is not None: return drafts[0] if drafts else dict(unit_id=uid,revision=0,body=None)
        return dict(drafts=[dict(unit_id=d['unit_id'],revision=d['revision'],updated_at=d['updated_at'],
            material_id=d['body']['material_id'],title=d['body'].get('title',''),base_revision=d['body']['revision']) for d in drafts if d['body']])

    def save(self, actor, req):
        actor=named(actor);rid=str(uuid.UUID(req['request_id']));digest=fingerprint(req);uid=req['unit_id']
        body=req.get('body')
        if body is not None:
            allowed={'fields','check_design','linked_material_ids','context_fingerprint','revision','material_id','title','retry'}
            if not isinstance(body,dict) or set(body)-allowed or len(encoded(body).encode())>4000000:
                raise ValueError('Working copy is invalid or too large.')
            from .interpretations import KEYS
            if not isinstance(body.get('fields'),dict) or set(body['fields'])!=set(KEYS) or type(body.get('revision')) is not int:
                raise ValueError('Working copy needs six fields and its saved base revision.')
            for f in body['fields'].values():
                if not isinstance(f,dict) or not isinstance(f.get('value'),str) or f.get('basis') not in ('source','interpretation','unresolved') or field_state(f) not in STATES:raise ValueError('Invalid working field.')
                if not isinstance(f.get('references'),list) or not isinstance(f.get('gaps'),list) or any(not isinstance(g,str) for g in f['gaps']):raise ValueError('Invalid working evidence.')
                if any(not isinstance(r,dict) or not isinstance(r.get('id'),str) or not isinstance(r.get('quote'),str) for r in f['references']):raise ValueError('Invalid working quotation.')
            if not isinstance(body.get('title',''),str) or not isinstance(body.get('linked_material_ids',[]),list):raise ValueError('Invalid working context.')
            design=body.get('check_design')
            if design is not None:
                if not isinstance(design,dict) or design.get('schema')!='requirement-check-design/1' or set(design.get('groups',{}))!={'scope','condition','demand'}:raise ValueError('Invalid working rule design.')
                count=[0]
                def check(n,depth=0):
                    if n is None:return
                    count[0]+=1
                    if not isinstance(n,dict) or depth>8 or count[0]>200 or not isinstance(n.get('id'),str):raise ValueError('Invalid working rule tree.')
                    if 'rules' in n:
                        if n.get('condition') not in ('AND','OR') or not isinstance(n['rules'],list):raise ValueError('Invalid working group.')
                        for child in n['rules']:check(child,depth+1)
                    elif not all(isinstance(n.get(k),str) for k in ('field','operator','type','interpretation_field')) or 'value' not in n:raise ValueError('Invalid working comparison.')
                for n in design['groups'].values():check(n)
        with self.c.lock,self.c.db() as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT digest,response FROM interpretation_draft_requests WHERE actor=? AND id=?',(actor,rid)).fetchone()
            if prior:
                if prior[0]!=digest:raise ValueError('Working-copy request identity was reused.')
                return json.loads(prior[1])
            unit=db.execute('SELECT material_id FROM requirement_units WHERE actor=? AND id=?',(actor,uid)).fetchone()
            # Retired units may retain/discard their existing drafts, never be reassigned.
            old=db.execute('SELECT revision FROM interpretation_drafts WHERE actor=? AND unit_id=?',(actor,uid)).fetchone()
            if not unit and not old:raise ValueError('Requirement is not available to this reviewer.')
            if unit and body is not None and body.get('material_id')!=unit[0]:raise ValueError('Working copy belongs to another material.')
            revision=old[0] if old else 0
            if req.get('expected_revision')!=revision:return dict(status='conflict',error='A working copy changed in another window. Your local edits remain available; reopen to compare.')
            result=dict(status='saved',revision=revision+1)
            db.execute('INSERT OR REPLACE INTO interpretation_drafts VALUES(?,?,?,?,?)',(actor,uid,revision+1,encoded(body),now()))
            db.execute('INSERT INTO interpretation_draft_requests VALUES(?,?,?,?)',(actor,rid,digest,encoded(result)))
            return result
