"""Validated repair operations; callers commit patches, invalidation and events together."""
from copy import deepcopy
import math
import re
from .effective import table_owner, table_source
from ..contracts.hashing import digest

PATCH_KEYS=('edits','reviewed_references','reviewed_structure','content_relations','relation_dependencies','dependencies','cell_edits','reviewed_cells','table_cell_history','table_geometry','table_row_binding','table_row_dispositions','table_row_exclusions','table_assembly','table_assembly_id','blockers','hierarchy_edit','hierarchy_dependencies','reading_order_key','superseded_by','boundary_sources','boundary_request_id')


def patch_state(unit):
    return {k:deepcopy(unit[k]) for k in PATCH_KEYS if k in unit}


def invalidate(units, identities):
    affected=set(identities)
    while True:
        more={u['id'] for u in units.values() if affected.intersection(u.get('dependencies',[]))}-affected
        if not more:break
        affected.update(more)
    for uid in affected:
        u=units[uid]
        u.update(content_human=False,requirement_human=False,touched=True,requirement_parts=[])
        u['version']+=1
    return sorted(affected)


def source_reference(locator, doc):
    if not isinstance(locator,str) or not locator.strip():raise ValueError('source_location_required')
    locator=locator.strip();ref={'locator':locator,'source_sha256':doc['source']['content_hash']}
    page=re.fullmatch(r'page\s+(\d+)(?:\s*:\s*([0-9., ]+))?',locator,re.I)
    if page:
        ref['page_index']=int(page[1])-1
        if ref['page_index']<0 or ('total_pages' in doc and ref['page_index']>=doc['total_pages']):raise ValueError('original_page_out_of_range')
        if page[2]:
            coords=[float(v.strip()) for v in page[2].split(',')]
            if len(coords)!=4 or not all(math.isfinite(v) for v in coords) or min(coords)<0 or coords[2]<=coords[0] or coords[3]<=coords[1]:raise ValueError('invalid_region_coordinates')
            ref['bbox']=coords
    elif doc['source'].get('file_format')=='pdf':raise ValueError('pdf_location_requires_page_and_optional_box')
    elif not ('nth-of-type(' in locator or re.fullmatch(r'xl/worksheets/[^#]+#[A-Z]+[0-9]+',locator)):
        # Preserve the existing non-PDF locator contract.
        if not locator:raise ValueError('source_location_required')
    return ref


def relation(unit, units, request):
    target=units.get(request.get('target_unit_id'))
    if target is None or target['id']==unit['id'] or target['kind']=='coverage' or target.get('superseded_by'):raise ValueError('relation_target_invalid')
    if request.get('target_fingerprint')!=digest(target):raise ValueError('stale_relation_target')
    role=request.get('role');mode=request.get('mode','attach')
    if role not in {'notes','context','reference'} or mode not in {'attach','detach'}:raise ValueError('invalid_relation_operation')
    owner=table_owner(unit,units)
    if mode=='detach' and owner and owner['id']!=unit['id'] and any(l['target_unit_id']==target['id'] and l['role']==role for l in owner.get('content_relations',[])):
        raise ValueError('edit_inherited_relationship_on_complete_table')
    previous=unit.get('content_relations',[])
    links=[l for l in previous if (l['target_unit_id'],l['role'])!=(target['id'],role)]
    if mode=='attach':links.append({'role':role,'target_unit_id':target['id']})
    old=set(unit.get('relation_dependencies',[]));new={l['target_unit_id'] for l in links}
    base=set(unit.get('dependencies',[]))-old
    from ..domains.requirements.review_hierarchy import value
    parent=value(unit).get('parent_id')
    if parent in units:base.add(parent)
    # A typed edge must not introduce a dependency cycle.
    frontier=list(base|new);seen=set()
    while frontier:
        uid=frontier.pop()
        if uid==unit['id']:raise ValueError('content_relation_cycle')
        if uid in seen:continue
        seen.add(uid)
        if uid not in units:raise ValueError('related_content_not_loaded')
        frontier.extend(units[uid].get('dependencies',[]))
    unit.update(content_relations=links,relation_dependencies=sorted(new-base),dependencies=sorted(base|new))
    return [unit['id']]


def cell(unit, units, request):
    owner=table_owner(unit,units)
    if owner is None or request.get('table_owner_id')!=owner['id']:raise ValueError('table_owner_invalid')
    if request.get('target_fingerprint')!=digest(owner):raise ValueError('stale_table_version')
    identity=request.get('cell_id');text=request.get('text')
    from .effective import table_view
    if not isinstance(text,str) or identity not in {c['id'] for c in table_view(owner)['cells']}:raise ValueError('table_cell_invalid')
    owner.setdefault('cell_edits',{})[identity]=text
    for u in units.values():
        related=table_owner(u,units)
        if related and related['id']==owner['id'] and any(k in u.get('edits',{}) for k in ('body','criteria','identifier')):
            u['blockers']=list(dict.fromkeys(u.get('blockers',[])+['human_table_text_conflict']))
    return [owner['id']]


def restore(units, history):
    before=history.get('repair_before');after=history.get('repair_after')
    if not before or not after:raise ValueError('this_history_entry_cannot_be_restored')
    if history.get('action')=='merge':
        survivor=history['unit_id']
        if any(uid not in after and survivor in u.get('dependencies',[]) for uid,u in units.items()):
            raise ValueError('restore_conflicts_with_later_relationships')
    created=history.get('created_ids',[])
    if created and any(uid not in after and set(created).intersection(u.get('dependencies',[])) for uid,u in units.items()):
        raise ValueError('restore_conflicts_with_later_relationships')
    for uid,state in after.items():
        if uid not in units or patch_state(units[uid])!=state:raise ValueError('restore_conflicts_with_later_repairs')
    for uid,state in before.items():
        for key in PATCH_KEYS:units[uid].pop(key,None)
        units[uid].update(deepcopy(state))
    for uid in created:units[uid]['superseded_by']=history['unit_id']
    return list(before)+created


def use_table_values(unit, units, request):
    owner=table_owner(unit,units)
    if owner is None or request.get('table_owner_id')!=owner['id']:raise ValueError('table_owner_invalid')
    if request.get('target_fingerprint')!=digest(owner):raise ValueError('stale_table_version')
    for key in ('body','criteria','identifier'):unit.get('edits',{}).pop(key,None)
    unit['blockers']=[b for b in unit.get('blockers',[]) if b!='human_table_text_conflict']
    return [unit['id']]
