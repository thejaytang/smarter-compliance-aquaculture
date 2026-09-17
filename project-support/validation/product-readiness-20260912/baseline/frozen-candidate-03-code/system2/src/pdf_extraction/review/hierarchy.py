"""Executable source hierarchy and reading-order repairs."""
from fractions import Fraction
from ..contracts.hashing import digest
from ..domains.requirements.review_hierarchy import value,ancestors

TYPES={'heading','paragraph','list_item','footnote','caption','figure','table','table_row','header','footer','equation','code'}


def ensure_order(doc):
    values=doc['units']
    key=lambda u:Fraction(str(u.get('reading_order_key',u['source_order'])))
    for i,u in enumerate(values):
        if 'source_order' in u:continue
        left=key(values[i-1]) if i else None
        right=next((key(v) for v in values[i+1:] if 'source_order' in v),None)
        u['source_order']=str((left+right)/2 if left is not None and right is not None else left+1 if left is not None else right-1 if right is not None else 0)


def ordered(units):
    return sorted(units,key=lambda u:Fraction(str(u.get('reading_order_key',u.get('source_order',0)))))


def affected_scopes(units,ids):
    ids=set(ids)
    ids.update(d for uid in list(ids) for d in units[uid].get('dependencies',[]) if units.get(d,{}).get('coverage_scope')=='pdf_page')
    return sorted(ids)


def repair(doc,unit,request):
    units={u['id']:u for u in doc['units']}
    if unit['kind']=='coverage' or unit.get('superseded_by'):raise ValueError('hierarchy_requires_current_content')
    patch=request.get('hierarchy')
    if not isinstance(patch,dict) or not patch or set(patch)-{'type','heading_level','parent_id'}:raise ValueError('invalid_hierarchy_patch')
    merged=dict(value(unit),**patch)
    if merged.get('type') not in TYPES:raise ValueError('invalid_content_type')
    level=merged.get('heading_level')
    if level is not None and (type(level)!=int or not 1<=level<=6):raise ValueError('heading_level_must_be_1_to_6_or_unknown')
    if 'parent_id' in patch and patch['parent_id'] is not None:
        target=units.get(patch['parent_id'])
        if not target or target['kind']=='coverage' or target.get('superseded_by'):raise ValueError('hierarchy_parent_invalid')
        if request.get('target_fingerprint')!=digest(target):raise ValueError('stale_hierarchy_parent')
    prior=value(unit).get('parent_id');unit.setdefault('hierarchy_edit',{}).update(patch,origin='human')
    ancestors(unit,units,doc.get('hierarchy_containers',{}))
    old=set(unit.get('hierarchy_dependencies',[]));base=set(unit.get('dependencies',[]))-old
    base.update(link['target_unit_id'] for link in unit.get('content_relations',[]))
    parent=value(unit).get('parent_id');new={parent} if parent in units else set()
    unit.update(dependencies=sorted(base|new),hierarchy_dependencies=sorted(new-base))
    # Check dependency cycles as well as parent cycles (for example a heading
    # already depending on its proposed child through a shared footnote).
    frontier=list(unit['dependencies']);seen=set()
    while frontier:
        uid=frontier.pop()
        if uid==unit['id']:raise ValueError('hierarchy_dependency_cycle')
        if uid in seen:continue
        seen.add(uid)
        if uid in units:frontier.extend(units[uid].get('dependencies',[]))
    return affected_scopes(units,[uid for uid in (unit['id'],prior,parent) if uid in units])


def move(doc,unit,request):
    ensure_order(doc)
    units={u['id']:u for u in doc['units']};target=units.get(request.get('target_unit_id'))
    if unit['kind']=='coverage' or unit.get('superseded_by') or not target or target['kind']=='coverage' or target.get('superseded_by'):raise ValueError('reading_order_target_invalid')
    if request.get('target_fingerprint')!=digest(target):raise ValueError('stale_order_target')
    mode=request.get('mode')
    if mode not in {'before','after'}:raise ValueError('reading_order_direction_required')
    selected={unit['id']}
    while True:
        extra={u['id'] for u in doc['units'] if value(u).get('parent_id') in selected}-selected
        if not extra:break
        selected.update(extra)
    if target['id'] in selected:raise ValueError('cannot_move_relative_to_own_subtree')
    original=ordered(doc['units']);moving=[u for u in original if u['id'] in selected];rest=[u for u in original if u['id'] not in selected]
    index=next(i for i,u in enumerate(rest) if u['id']==target['id'])+(mode=='after')
    key=lambda u:Fraction(str(u.get('reading_order_key',u.get('source_order',0))))
    left=key(rest[index-1]) if index else key(rest[0])-1
    right=key(rest[index]) if index<len(rest) else left+1
    if left>=right:raise ValueError('reading_order_needs_source_projection')
    for i,u in enumerate(moving):u['reading_order_key']=str(left+(right-left)*Fraction(i+1,len(moving)+1))
    doc['units']=ordered(doc['units'])
    return affected_scopes(units,selected|{target['id']})


def validate(doc):
    units={u['id']:u for u in doc['units']};positions={u['id']:i for i,u in enumerate(ordered(doc['units']))}
    for u in doc['units']:
        parent=value(u).get('parent_id');code='hierarchy_parent_after_child'
        u['blockers']=[b for b in u.get('blockers',[]) if b!=code]
        if parent in positions and positions[parent]>positions[u['id']]:u['blockers'].append(code)
