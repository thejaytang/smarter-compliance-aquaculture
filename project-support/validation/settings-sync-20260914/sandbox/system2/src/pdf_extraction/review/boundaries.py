"""Original-boundary repairs using immutable originals plus reversible overlays."""
from copy import deepcopy
from .effective import resolve,table_owner
from .hierarchy import ordered,ensure_order,validate,affected_scopes,TYPES
from ..domains.requirements.review_hierarchy import value
from ..contracts.hashing import digest


def merge(doc,unit,request):
    units={u['id']:u for u in doc['units']}
    ids=request.get('merge_ids',[]);fingerprints=request.get('merge_fingerprints',{})
    if not isinstance(ids,list) or len(ids)<2 or len(set(ids))!=len(ids) or unit['id'] not in ids:
        raise ValueError('merge_requires_unique_ordered_source_units')
    selected=[units.get(uid) for uid in ids]
    if any(u is None or u['kind']=='coverage' or u.get('superseded_by') or u.get('evidence_only') for u in selected):
        raise ValueError('merge_requires_current_source_content')
    if not isinstance(fingerprints,dict) or any(fingerprints.get(u['id'])!=digest(u) for u in selected if u['id']!=unit['id']):
        raise ValueError('stale_merge_target')
    if any(u.get('drafts') and (u['id']!=unit['id'] or set(u['drafts'])-{request['actor']}) for u in selected):
        raise ValueError('merge_target_has_unsubmitted_draft')
    if any(table_owner(u,units) for u in selected):raise ValueError('table_boundaries_require_table_geometry_repair')
    ensure_order(doc)
    active=[u for u in ordered(doc['units']) if u['kind']!='coverage' and not u.get('superseded_by') and value(u).get('type') not in {'header','footer'}]
    picked=[u['id'] for u in active if u['id'] in ids]
    if picked!=ids:raise ValueError('merge_order_must_match_original_reading_order')
    start=next(i for i,u in enumerate(active) if u['id']==ids[0])
    if [u['id'] for u in active[start:start+len(ids)]]!=ids:raise ValueError('merge_requires_adjacent_content_or_explicit_order_repair')
    parent_ids={value(u).get('parent_id') for u in selected}
    if len(parent_ids)>1 or parent_ids.intersection(ids):raise ValueError('align_source_parents_before_merging')
    if any(link['target_unit_id'] in ids for u in selected for link in u.get('content_relations',[])):
        raise ValueError('resolve_internal_relationship_before_merging')
    hierarchy=request.get('hierarchy',{})
    if not isinstance(hierarchy,dict) or set(hierarchy)-{'type','heading_level'} or hierarchy.get('type') not in TYPES-{'table','table_row'}:
        raise ValueError('merged_content_type_required')
    level=hierarchy.get('heading_level')
    if level is not None and (type(level)!=int or not 1<=level<=6):raise ValueError('heading_level_must_be_1_to_6_or_unknown')
    if hierarchy['type']!='heading' and level is not None:raise ValueError('heading_level_requires_heading_type')
    views=[resolve(u,units) for u in selected];fields={}
    source_fields=[dict(u['original'].get('fields',{}),**u.get('edits',{})) for u in selected]
    for key in {k for f in source_fields for k in f} - {'body'}:
        values=list(dict.fromkeys(f[key] for f in source_fields if f.get(key)))
        if len(values)>1:raise ValueError('merge_field_conflict:'+key)
        if values:fields[key]=values[0]
    if any(not v['fields'].get('body','').strip() for v in views):raise ValueError('merge_requires_source_body_text')
    fields['body']='\n'.join(v['fields']['body'] for v in views)
    retired=set(ids)-{unit['id']}
    # Preserve every original region. No merged text is substituted for a source image.
    refs=[];seen=set()
    for v in views:
        for ref in v['references']:
            h=digest(ref)
            if h not in seen:refs.append(deepcopy(ref));seen.add(h)
    unit.setdefault('edits',{}).update(fields)
    unit['reviewed_references']=refs
    unit['boundary_sources']=list(dict.fromkeys(s for u in selected for s in u.get('boundary_sources',[u['id']])))
    unit['boundary_request_id']=request['request_id']
    unit.setdefault('hierarchy_edit',{}).update(hierarchy,origin='human')
    first=selected[0];unit['reading_order_key']=str(first.get('reading_order_key',first['source_order']))
    unit['blockers']=list(dict.fromkeys(b for u in selected for b in u.get('blockers',[])))
    unit['content_relations']=list({(l['role'],l['target_unit_id']):deepcopy(l) for u in selected for l in u.get('content_relations',[])}.values())
    for key in ('dependencies','relation_dependencies','hierarchy_dependencies'):
        unit[key]=sorted({d for u in selected for d in u.get(key,[])}-set(ids))
    changed=set(ids)
    for other in doc['units']:
        if other['id'] in retired:
            other['superseded_by']=unit['id']
            continue
        for key in ('dependencies','relation_dependencies','hierarchy_dependencies'):
            old=other.get(key,[])
            if retired.intersection(old):
                other[key]=list(dict.fromkeys(unit['id'] if uid in retired else uid for uid in old));changed.add(other['id'])
        if value(other).get('parent_id') in retired:
            other.setdefault('hierarchy_edit',{}).update(parent_id=unit['id'],origin='human');changed.add(other['id'])
        for link in other.get('content_relations',[]):
            if link['target_unit_id'] in retired:link['target_unit_id']=unit['id'];changed.add(other['id'])
    # All dependency paths must remain acyclic after redirecting identities.
    visiting=set();done=set()
    def visit(uid):
        if uid in visiting:raise ValueError('merge_dependency_cycle')
        if uid in done or uid not in units:return
        visiting.add(uid)
        for dep in units[uid].get('dependencies',[]):visit(dep)
        visiting.remove(uid);done.add(uid)
    for uid in changed:visit(uid)
    doc['units']=ordered(doc['units']);validate(doc)
    return affected_scopes(units,changed)
