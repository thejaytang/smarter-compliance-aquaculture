"""Explicit, read-only projection of retained effective legacy content.

This module never instantiates Workflow, recomputes acceptance, invokes a parser,
classifies, exports, or writes the owning database. Unmapped evidence is retained
for human association; historical decisions are provenance only.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sqlite3

from ..contracts.hashing import digest
from ..review import row_store, effective


def _reference(reference, material):
    scopes = {s['id']: s for s in material['scope']}
    result = deepcopy(reference)
    identity = reference.get('scope_id')
    if identity in scopes:
        return result
    page = reference.get('page')
    if type(reference.get('page_index')) is int:
        page = reference['page_index'] + 1
    if type(page) is int and f'page:{page}' in scopes:
        result.update(scope_id=f'page:{page}', page=page, page_index=page-1)
        box = result.get('bbox')
        if isinstance(box, dict) and all(k in box for k in ('x0','y0','x1','y1')):
            result['bbox'] = [box[k] for k in ('x0','y0','x1','y1')]
        return result
    locator = reference.get('locator', '')
    sheet = reference.get('sheet') or reference.get('sheet_name')
    for scope in material['scope']:
        location = scope.get('location', {})
        part = location.get('part')
        if scope['id'].startswith('sheet:') and ((sheet is not None and sheet == location.get('sheet')) or (part and locator.startswith(part + '#'))):
            result.update(scope_id=scope['id'], sheet=location.get('sheet'))
            if '#' in locator:
                result['cell_range'] = locator.split('#',1)[1]
            return result
    if 'html:document' in scopes and (locator.startswith('/') or reference.get('anchor')):
        result['scope_id'] = 'html:document'
        return result
    return None


def _table(table):
    height, width = table.get('row_count'), table.get('column_count')
    if type(height) is not int or type(width) is not int or min(height,width)<1 or height*width>1_000_000:
        raise ValueError('legacy_table_geometry_needs_repair')
    rows, merges = [['']*width for _ in range(height)], []
    occupied = set()
    for cell in table.get('cells', []):
        r,c,rs,cs = cell.get('row'),cell.get('column'),cell.get('row_span',1),cell.get('column_span',1)
        if any(type(v) is not int for v in (r,c,rs,cs)) or min(r,c)<0 or min(rs,cs)<1 or r+rs>height or c+cs>width:
            raise ValueError('legacy_table_cell_outside_geometry')
        area = {(rr,cc) for rr in range(r,r+rs) for cc in range(c,c+cs)}
        if area & occupied:
            raise ValueError('legacy_table_merged_cells_overlap')
        occupied |= area
        rows[r][c] = str(effective.cell_text(cell))
        if rs>1 or cs>1:
            merges.append({'row':r,'col':c,'rowspan':rs,'colspan':cs})
    return {'rows':rows, 'merges':merges, 'notes':[]}


def legacy_candidate(workflow_root, material, document_id=None):
    path = Path(workflow_root).resolve() / 'workflow.sqlite'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'").fetchone():
            raise ValueError('legacy_matching_snapshot_not_found')
        matches = []
        for row in db.execute('SELECT id,data FROM documents'):
            previous = json.loads(row['data'])
            if document_id is not None and row['id'] != document_id:
                continue
            if all(previous.get('source',{}).get(key) == material['source'].get(key) for key in ('source_id','snapshot_id','content_hash')):
                matches.append((previous.get('revision',0), row['id'], previous))
        if not matches:
            raise ValueError('legacy_matching_snapshot_not_found')
        _, identity, doc = max(matches, key=lambda item:(item[0],item[1]))
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_version'").fetchone():
            doc = row_store.load(db, identity)
    units = {u['id']:u for u in doc.get('units',[]) if not u.get('superseded_by')}
    mapped_ids = {uid:'legacy:'+digest([identity,uid])[:24] for uid in units}
    blocks, issues = [], []
    def issue(uid, message):
        issues.append({'id':'legacy:'+digest([identity,uid,message])[:20], 'message':message, 'resolved':False})
    for original_issue in doc.get('issues',[]):
        issue(identity,'Retained legacy issue needs human review: '+str(original_issue))
    def order(unit):
        try:
            return Fraction(str(unit.get('reading_order_key',unit.get('source_order',0))))
        except (ValueError,ZeroDivisionError):
            return Fraction(0)
    for unit in sorted(units.values(), key=order):
        uid = unit['id']
        if unit.get('kind') == 'coverage':
            continue
        owner = effective.table_owner(unit, units)
        assembly = units.get(unit.get('table_assembly_id'))
        if (owner and owner['id'] != uid) or (assembly and assembly['id'] != uid):
            if not unit.get('edits'):
                continue
            issue(uid,'A legacy derived row has separate manual edits. Reconcile this retained supplement with its whole table.')
        try:
            value = effective.resolve(unit, units)
        except (ValueError,KeyError,TypeError) as exc:
            value = dict(unit.get('original',{}),kind=unit.get('kind'),fields=dict(unit.get('original',{}).get('fields',{}),**unit.get('edits',{})))
            issue(uid,'Legacy effective view needs repair: '+str(exc))
        refs = [_reference(ref,material) for ref in value.get('references',[]) if isinstance(ref,dict)]
        mapped = [r for r in refs if r is not None]
        if not mapped or len(mapped) != len(value.get('references',[])):
            issue(uid,'One or more legacy source locations are unmapped. Associate this block with the original before confirmation.')
        fields = value.get('fields',{})
        hierarchy = value.get('hierarchy', {})
        kind = value.get('kind','text')
        block_type = 'heading' if kind in ('source_heading','heading') or hierarchy.get('type')=='heading' else 'image' if kind in ('source_image','image','figure') or hierarchy.get('type')=='figure' else 'text'
        text_parts = [str(v) for key,v in fields.items() if key!='identifier' and isinstance(v,(str,int,float)) and v!='']
        block = {'id':mapped_ids[uid], 'type':block_type, 'text':'\n\n'.join(dict.fromkeys(text_parts)),
            'level':hierarchy.get('heading_level') or 1, 'numbering':str(fields.get('identifier','')),
            'parent_id':mapped_ids.get(hierarchy.get('parent_id')), 'dependencies':[], 'source_refs':mapped,
            'legacy_provenance':{'document_id':identity,'document_revision':doc.get('revision'), 'unit_id':uid,
                'unit_version':unit.get('version',1), 'original':deepcopy(unit.get('original',{})),
                'effective':deepcopy(value), 'edits':deepcopy(unit.get('edits',{})),
                'dependencies':deepcopy(unit.get('dependencies',[])), 'hierarchy':deepcopy(hierarchy),
                'reading_order_key':unit.get('reading_order_key'), 'drafts':deepcopy(unit.get('drafts',{})),
                'historical_content_human':unit.get('content_human',False),
                'historical_requirement_human':unit.get('requirement_human',False)}}
        if value.get('table') and not (owner and owner['id'] != uid):
            try:
                block.update(type='table', text='', table=_table(value['table']))
                if fields.get('notes'):
                    block['table']['notes'] = [str(fields['notes'])]
            except ValueError as exc:
                issue(uid,str(exc)+'. Full original table retained in provenance.')
        if block_type == 'image':
            block['image'] = {'source_ref':mapped[0] if mapped else None,'attachment':None,
                              'attribution':'Image in the matched original snapshot; historical references retained.'}
        block['_legacy_dependencies'] = unit.get('dependencies',[])
        blocks.append(block)
    # Validate hierarchy and dependency associations against retained blocks only.
    by_id = {b['id']:b for b in blocks}
    prior = set()
    for block in blocks:
        parent = block['parent_id']
        if parent and (parent not in prior or by_id[parent]['type']!='heading' or (block['type']=='heading' and by_id[parent]['level']>=block['level'])):
            issue(block['id'],'Legacy hierarchy parent needs explicit reassociation; original hierarchy remains in provenance.')
            block['parent_id'] = None
        legacy_dependencies = block.pop('_legacy_dependencies')
        if any(d not in units for d in legacy_dependencies):
            issue(block['id'],'A legacy dependency is missing; inspect its retained provenance and reassociate it.')
        block['dependencies'] = [mapped_ids[d] for d in legacy_dependencies if d in mapped_ids and mapped_ids[d] in by_id and mapped_ids[d]!=block['id']]
        if block['type']=='heading' and (type(block['level']) is not int or not 1<=block['level']<=6):
            issue(block['id'],'Legacy heading level is outside editable range; original level retained in provenance.')
            block['level']=1
        prior.add(block['id'])
    # Cycles cannot become an editable dependency graph. Keep their evidence and
    # widen human association review, without discarding any block content.
    done, visiting = set(), set()
    def cyclic(identity):
        if identity in visiting:
            return True
        if identity in done:
            return False
        visiting.add(identity)
        if any(cyclic(dep) for dep in by_id[identity]['dependencies']):
            return True
        visiting.remove(identity)
        done.add(identity)
        return False
    if any(cyclic(b['id']) for b in blocks):
        issue(identity,'Legacy dependency cycle requires reassociation. Dependency originals are retained; full material scope requires review.')
        for block in blocks:
            block['dependencies']=[]
    return {'blocks':blocks, 'issues':issues,
        'provenance':{'origin':'legacy_effective_content','document_id':identity,'revision':doc.get('revision'),
            'source':deepcopy(doc['source']),'unit_versions':{u['id']:u.get('version',1) for u in units.values()},
            'history_digest':digest(doc.get('history',[])), 'legacy_issues':deepcopy(doc.get('issues',[])),
            'notice':'Historical decisions remain historical. New full original-scope human confirmation is required.'}}
