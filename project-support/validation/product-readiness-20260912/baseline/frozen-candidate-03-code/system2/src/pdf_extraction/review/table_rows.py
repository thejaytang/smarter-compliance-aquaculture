"""Explicit lifecycle of review items derived from a retained original table."""
from copy import deepcopy
from .effective import table_owner,table_view,resolve
from .hierarchy import ensure_order,affected_scopes
from ..contracts.hashing import digest
from ..domains.requirements.review_hierarchy import value


def current_rows(owner,units):
    return [u for u in units.values() if u['id']!=owner['id'] and not u.get('superseded_by') and table_owner(u,units)==owner]


def row_number(unit,owner):
    ids={r.get('locator') for r in unit.get('reviewed_references',unit['original'].get('references',[]))}
    rows={c['row'] for c in table_view(owner)['cells'] if c['id'] in ids}
    return unit.get('table_row_binding',next(iter(rows)) if len(rows)==1 else None)


def exclude_absent_row(doc,owner,table,rows,units,request):
    """Retire a reviewer-confirmed extraction artifact, retaining all source facts."""
    change=request['row_change'];r=change.get('row')
    if change.get('confirmed_absent') is not True:raise ValueError('confirm_row_absent_from_original')
    if type(r)!=int or not 0<=r<table['row_count']:raise ValueError('table_row_out_of_range')
    if table['row_count']<2:raise ValueError('cannot_remove_entire_table_as_one_row')
    affected_cells=[c for c in table['cells'] if c['row']<=r<c['row']+c['row_span']]
    if not affected_cells or any(c['row']!=r or c['row_span']!=1 for c in affected_cells):
        raise ValueError('repair_shared_cell_boundaries_before_removing_row')
    positions={u['id']:row_number(u,owner) for u in rows}
    if any(type(p)!=int for p in positions.values()):raise ValueError('bind_existing_rows_before_removing_row')
    fingerprints=change.get('row_fingerprints',{})
    if not isinstance(fingerprints,dict) or set(fingerprints)!=set(positions) or any(fingerprints[u['id']]!=digest(u) for u in rows):
        raise ValueError('stale_table_item')
    if any(u.get('drafts') for u in rows):raise ValueError('table_item_has_unsubmitted_draft')
    retired={uid for uid,p in positions.items() if p==r}
    for other in units.values():
        if other.get('superseded_by') or other['id'] in retired:continue
        if retired.intersection(other.get('dependencies',[])):
            raise ValueError('resolve_incoming_row_relationship_before_removing_row')
    # Originals remain in Canonical and each unit's original fields. The overlay
    # also keeps the exact removed effective cells and the named decision reason.
    owner.setdefault('table_row_exclusions',[]).append({'row_at_decision':r,'cells':deepcopy(affected_cells),
        'retired_unit_ids':sorted(retired),'actor':request['actor'],'reason':request['note'],
        'request_id':request['request_id'],'source_sha256':doc['source']['content_hash']})
    owner.setdefault('table_cell_history',{}).update({c['id']:deepcopy(c) for c in affected_cells})
    cells=[deepcopy(c) for c in table['cells'] if c not in affected_cells]
    for c in cells:
        if c['row']>r:c['row']-=1
    table=deepcopy(table);table.update(row_count=table['row_count']-1,cells=cells)
    owner['reviewed_cells']=deepcopy(cells);owner.pop('table_geometry',None)
    owner['table_row_dispositions']={str(int(k)-(int(k)>r)):v for k,v in owner.get('table_row_dispositions',{}).items() if int(k)!=r}
    remaining=[]
    for u in rows:
        if u['id'] in retired:
            u['superseded_by']=owner['id'];u['boundary_request_id']=request['request_id']
        else:
            u['table_row_binding']=positions[u['id']]-(positions[u['id']]>r);remaining.append(u)
    return table,remaining,retired


def repair(doc,unit,request):
    units={u['id']:u for u in doc['units']};owner=table_owner(unit,units)
    if owner is None or owner['id']!=unit['id'] or request.get('table_owner_id')!=owner['id']:raise ValueError('row_repair_requires_complete_table')
    if request.get('target_fingerprint')!=digest(owner):raise ValueError('stale_table_version')
    if set(owner.get('drafts',{}))-{request['actor']}:raise ValueError('table_has_unsubmitted_draft')
    change=request.get('row_change')
    if not isinstance(change,dict):raise ValueError('row_change_required')
    table=table_view(owner);rows=current_rows(owner,units);changed={owner['id']};created=[]
    dispositions=owner.setdefault('table_row_dispositions',{})
    mode=change.get('mode')
    if mode in {'create','table_only'}:
        r=change.get('row')
        if type(r)!=int or not 0<=r<table['row_count']:raise ValueError('table_row_out_of_range')
        if any(row_number(u,owner)==r for u in rows):raise ValueError('table_row_already_has_item')
        if mode=='table_only':
            dispositions[str(r)]={'mode':'table_only','reason':request['note'],'request_id':request['request_id']}
        else:
            cells=[c for c in table['cells'] if c['row']<=r<c['row']+c['row_span']]
            if not cells:raise ValueError('supplement_missing_cells_before_creating_row')
            refs=[dict(deepcopy(region),locator=c['id']) for c in cells for region in c.get('source_regions',[{'page_index':c['page_index'],'bbox':c['bbox']}])]
            identity='table-row:'+digest(request['request_id'])[:24]
            if identity in units:raise ValueError('table_row_identity_already_exists')
            ensure_order(doc)
            new={'id':identity,'kind':'source_table_row','original':{'fields':{},'references':refs,'structure':[]},
                 'evidence_only':bool(owner.get('evidence_only')),'dependencies':[owner['id']],'hierarchy_dependencies':[owner['id']],
                 'hierarchy_edit':{'type':'table_row','parent_id':owner['id'],'heading_level':None,'origin':'human'},
                 'table_row_binding':r,'source_order':owner['source_order'],'version':1,'edits':{},'drafts':{},
                 'content_human':False,'requirement_human':False,'touched':True,'classification':'undetermined',
                 'content_parts':[],'requirement_parts':[],'blockers':[],'chapter':owner.get('chapter','Original order'),
                 'provenance':{'origin':'human_table_row','actor':request['actor'],'request_id':request['request_id'],
                               'source_sha256':doc['source']['content_hash'],'table_id':owner['id'],'table_version':owner['version']}}
            if owner.get('table_assembly_id'):
                new['table_assembly_id']=owner['table_assembly_id']
                new['dependencies'].append(owner['table_assembly_id'])
            # Store the creation snapshot; subsequent views still resolve the effective cells.
            units[identity]=new;new['original']['fields']=deepcopy(resolve(new,units)['fields'])
            doc['units'].append(new);rows.append(new);created.append(identity);changed.add(identity);dispositions.pop(str(r),None)
    elif mode=='exclude_absent':
        table,rows,retired=exclude_absent_row(doc,owner,table,rows,units,request)
        changed.update(retired)
    elif mode=='retire_duplicate':
        old=units.get(change.get('unit_id'));keep=units.get(change.get('replacement_id'))
        if old not in rows or keep not in rows or old is keep:raise ValueError('choose_two_current_table_items')
        if change.get('fingerprint')!=digest(old) or change.get('replacement_fingerprint')!=digest(keep):raise ValueError('stale_table_item')
        if old.get('drafts') or keep.get('drafts'):raise ValueError('table_item_has_unsubmitted_draft')
        left=resolve(old,units);right=resolve(keep,units)
        if row_number(old,owner)!=row_number(keep,owner) or {c['id'] for c in left['table']['cells']}!={c['id'] for c in right['table']['cells']}:raise ValueError('duplicate_items_must_cover_same_original_cells')
        if left['fields']!=right['fields'] or old.get('content_relations',[])!=keep.get('content_relations',[]):raise ValueError('resolve_duplicate_text_or_relationship_conflict_first')
        for other in units.values():
            if other.get('superseded_by') or other['id']==old['id']:continue
            if old['id'] in other.get('dependencies',[]):
                if other.get('drafts') and other['id']!=owner['id']:raise ValueError('related_item_has_unsubmitted_draft')
                for key in ('dependencies','relation_dependencies','hierarchy_dependencies'):
                    if old['id'] in other.get(key,[]):other[key]=list(dict.fromkeys(keep['id'] if i==old['id'] else i for i in other[key]))
                for link in other.get('content_relations',[]):
                    if link['target_unit_id']==old['id']:link['target_unit_id']=keep['id']
                if value(other).get('parent_id')==old['id']:other.setdefault('hierarchy_edit',{}).update(parent_id=keep['id'],origin='human')
                changed.add(other['id'])
        old['superseded_by']=keep['id'];old['boundary_request_id']=request['request_id']
        keep['boundary_sources']=list(dict.fromkeys(keep.get('boundary_sources',[keep['id']])+old.get('boundary_sources',[old['id']])))
        keep['blockers']=list(dict.fromkeys(keep.get('blockers',[])+old.get('blockers',[])))
        changed.update([old['id'],keep['id']]);rows.remove(old)
    else:raise ValueError('unsupported_table_row_operation')
    # Keep every remaining unrepresented range explicitly pending. Whole-table scope
    # is a review location, never an automatic non-Requirement classification.
    from .table_geometry import repair as geometry_repair
    spec={'row_count':table['row_count'],'column_count':table['column_count'],'cells':[dict({k:c[k] for k in ('id','row','column','row_span','column_span')},is_header=bool(c.get('is_header'))) for c in table['cells']],
          'row_bindings':{u['id']:{'row':row_number(u,owner),'fingerprint':digest(u)} for u in rows},'allow_incomplete':True}
    changed.update(geometry_repair(doc,unit,dict(request,target_fingerprint=digest(owner),table_geometry=spec)))
    # Redirection must not create a dependency cycle.
    seen=set();visiting=set()
    def visit(uid):
        if uid in visiting:raise ValueError('table_row_dependency_cycle')
        if uid in seen or uid not in units:return
        visiting.add(uid)
        for dep in units[uid].get('dependencies',[]):visit(dep)
        visiting.remove(uid);seen.add(uid)
    for uid in changed:visit(uid)
    return affected_scopes(units,changed),created
