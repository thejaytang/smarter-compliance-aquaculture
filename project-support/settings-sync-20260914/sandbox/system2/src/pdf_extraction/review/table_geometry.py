"""Source-preserving grid coordinates and explicit existing-row bindings."""
from copy import deepcopy
from fractions import Fraction
from .effective import table_owner, table_view
from ..contracts.hashing import digest


def context(db,did,owner):
    import json
    rows=[]
    for r in db.execute('SELECT u.data FROM review_units u JOIN review_dependencies d ON u.document_id=d.document_id AND u.id=d.unit_id WHERE d.document_id=? AND d.dependency_id=?',(did,owner['id'])):
        u=json.loads(r[0])
        if u.get('superseded_by') or table_owner(u,{owner['id']:owner,u['id']:u}) is None:continue
        refs=u.get('reviewed_references',u['original'].get('references',[]));ids={r.get('locator') for r in refs}
        cells=[c for c in table_view(owner)['cells'] if c['id'] in ids]
        row_numbers=sorted({c['row'] for c in cells})
        rows.append({'id':u['id'],'title':u['original']['fields'].get('identifier') or u['original']['fields'].get('body','')[:100],
                     'fingerprint':digest(u),'row':u.get('table_row_binding',row_numbers[0] if len(row_numbers)==1 else None)})
    return {'owner_id':owner['id'],'fingerprint':digest(owner),'table':table_view(owner),'rows':rows,'row_dispositions':owner.get('table_row_dispositions',{}),
            'row_exclusions':deepcopy(owner.get('table_row_exclusions',[]))}


def repair(doc,unit,request):
    units={u['id']:u for u in doc['units']};owner=table_owner(unit,units)
    if owner is None or request.get('table_owner_id')!=owner['id']:raise ValueError('table_owner_invalid')
    if request.get('target_fingerprint')!=digest(owner):raise ValueError('stale_table_version')
    if set(owner.get('drafts',{}))-{request['actor']}:raise ValueError('table_has_unsubmitted_draft')
    spec=request.get('table_geometry')
    if not isinstance(spec,dict):raise ValueError('table_geometry_required')
    rows=spec.get('row_count');cols=spec.get('column_count');layout=spec.get('cells')
    if type(rows)!=int or type(cols)!=int or min(rows,cols)<1 or rows*cols>100000:raise ValueError('invalid_table_dimensions')
    original=table_view(owner);ids={c['id'] for c in original['cells']}
    if not isinstance(layout,list) or len(layout)!=len(ids) or any(not isinstance(c,dict) or not isinstance(c.get('id'),str) for c in layout) or {c['id'] for c in layout}!=ids:raise ValueError('preserve_every_table_cell_identity')
    occupied={};clean=[]
    for c in layout:
        if any(type(c.get(k))!=int for k in ('row','column','row_span','column_span')) or type(c.get('is_header'))!=bool:raise ValueError('invalid_table_cell_geometry')
        if min(c['row'],c['column'])<0 or min(c['row_span'],c['column_span'])<1 or c['row']+c['row_span']>rows or c['column']+c['column_span']>cols:raise ValueError('table_cell_outside_grid')
        for r in range(c['row'],c['row']+c['row_span']):
            for col in range(c['column'],c['column']+c['column_span']):
                if (r,col) in occupied:raise ValueError('table_cells_overlap')
                occupied[r,col]=c['id']
        clean.append({k:c[k] for k in ('id','row','column','row_span','column_span','is_header')})
    gaps=len(occupied)!=rows*cols
    if gaps and spec.get('allow_incomplete') is not True:raise ValueError('table_grid_has_unresolved_gaps')
    bindings=spec.get('row_bindings')
    if not isinstance(bindings,dict):raise ValueError('explicit_table_row_bindings_required')
    related=[u for u in doc['units'] if u['id']!=owner['id'] and not u.get('superseded_by') and table_owner(u,units)==owner]
    if set(bindings)!={u['id'] for u in related}:raise ValueError('bind_every_existing_table_row')
    assigned=[]
    for u in related:
        b=bindings[u['id']]
        if not isinstance(b,dict) or b.get('fingerprint')!=digest(u):raise ValueError('stale_table_row_binding')
        if set(u.get('drafts',{}))-{request['actor']}:raise ValueError('table_row_has_unsubmitted_draft')
        if u['id']!=unit['id'] and u.get('drafts'):raise ValueError('table_row_has_unsubmitted_draft')
        r=b.get('row')
        if type(r)!=int or not 0<=r<rows:raise ValueError('table_row_binding_outside_grid')
        assigned.append(r)
    if len(set(assigned))!=len(assigned):raise ValueError('multiple_items_bound_to_same_table_row')
    if 'table_row_dispositions' in owner:
        dispositions=owner['table_row_dispositions']
        if any(not k.isdigit() or not 0<=int(k)<rows or v.get('mode')!='table_only' for k,v in dispositions.items()):raise ValueError('table_row_disposition_outside_grid')
        if set(assigned)&{int(k) for k in dispositions}:raise ValueError('table_row_disposition_conflicts_with_item')
        uncovered=set(range(rows))-set(assigned)-{int(k) for k in dispositions}
        owner['blockers']=[b for b in owner.get('blockers',[]) if b!='human_table_row_gaps']
        if uncovered:owner['blockers'].append('human_table_row_gaps')
    elif related and set(assigned)!=set(range(rows)):raise ValueError('row_creation_or_retirement_requires_explicit_boundary_repair')
    owner['table_geometry']={'row_count':rows,'column_count':cols,'cells':clean}
    owner['blockers']=[b for b in owner.get('blockers',[]) if b!='human_table_grid_gaps']
    if gaps:owner['blockers'].append('human_table_grid_gaps')
    current=table_view(owner);cells=current['cells'];changed=[owner['id']]
    from .hierarchy import ensure_order,ordered,affected_scopes,validate
    ensure_order(doc)
    left=Fraction(str(owner.get('reading_order_key',owner['source_order'])))
    related_ids={u['id'] for u in related}
    right=min((Fraction(str(u.get('reading_order_key',u['source_order']))) for u in doc['units'] if u['id'] not in related_ids and Fraction(str(u.get('reading_order_key',u['source_order'])))>left),default=left+1)
    for u in related:
        r=bindings[u['id']]['row'];u['table_row_binding']=r
        u['reading_order_key']=str(left+(right-left)*Fraction(r+1,rows+1))
        chosen=sorted([c for c in cells if c['row']<=r<c['row']+c['row_span']],key=lambda c:c['column'])
        # References are replaced only in the overlay. Original row projections remain immutable.
        old={x.get('locator'):x for x in u['original'].get('references',[])}
        u['reviewed_references']=[{**deepcopy(old.get(c['id'],{})),**deepcopy(region),'locator':c['id']} for c in chosen for region in c.get('source_regions',[{'page_index':c['page_index'],'bbox':c['bbox']}])]
        if any(k in u.get('edits',{}) for k in ('body','criteria','identifier')):
            u['blockers']=list(dict.fromkeys(u.get('blockers',[])+['human_table_text_conflict']))
        changed.append(u['id'])
    if doc.get('pdf_scope_version'):
        from .pdf_scope import refresh
        changed.extend(refresh(doc))
    doc['units']=ordered(doc['units'])
    if doc.get('hierarchy_version'):validate(doc)
    return affected_scopes(units,changed)
