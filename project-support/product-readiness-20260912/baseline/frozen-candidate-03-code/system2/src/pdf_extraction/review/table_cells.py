"""Versioned cell boundary repairs with retained source text and regions."""
from copy import deepcopy
from .effective import table_owner,table_view,cell_text
from .repairs import source_reference
from ..contracts.hashing import digest


def regions(cell):
    return deepcopy(cell.get('source_regions',[{'page_index':cell['page_index'],'bbox':cell['bbox'],'source_cell_id':cell['id']}]))


def preview_regions(detail,cell_id,region_index,guard):
    if guard!=detail['guard']:raise ValueError('cell_evidence_version_changed')
    cell=next((c for c in detail['effective'].get('table',{}).get('cells',[]) if c['id']==cell_id),None)
    if cell is None:raise ValueError('current_source_cell_not_found')
    refs=regions(cell)
    if region_index is None:return refs
    if type(region_index)!=int or not 0<=region_index<len(refs):raise ValueError('source_cell_region_out_of_range')
    return [refs[region_index]]


def repair(doc,unit,request):
    units={u['id']:u for u in doc['units']};owner=table_owner(unit,units)
    if owner is None or owner['id']!=unit['id'] or request.get('table_owner_id')!=owner['id']:raise ValueError('cell_boundary_requires_complete_table')
    if request.get('target_fingerprint')!=digest(owner):raise ValueError('stale_table_version')
    change=request.get('cell_change')
    if not isinstance(change,dict):raise ValueError('cell_change_required')
    mode=change.get('mode');current=table_view(owner);by={c['id']:c for c in current['cells']}
    selected=change.get('cell_ids',[])
    if not isinstance(selected,list) or any(not isinstance(i,str) or i not in by for i in selected) or len(set(selected))!=len(selected):raise ValueError('invalid_source_cell_selection')
    old=[by[i] for i in selected];texts=[];source_regions=[]
    if mode=='split':
        if len(old)!=1:raise ValueError('split_one_source_cell')
        parts=change.get('parts');text=cell_text(old[0]);available=regions(old[0])
        if not isinstance(parts,list) or len(parts)<2 or any(not isinstance(p,dict) or not isinstance(p.get('text'),str) for p in parts) or ''.join(p['text'] for p in parts)!=text:raise ValueError('cell_split_must_preserve_every_character')
        offset=0
        for part in parts:
            indices=part.get('reference_indices')
            if not isinstance(indices,list) or not indices or any(type(i)!=int or not 0<=i<len(available) for i in indices) or len(set(indices))!=len(indices):raise ValueError('assign_original_regions_to_every_cell_part')
            chosen=[deepcopy(available[i]) for i in indices]
            for ref in chosen:ref['cell_text_range']={'source_cell_id':old[0]['id'],'body_sha256':digest(text),'start':offset,'end':offset+len(part['text']),'offset_unit':'unicode_codepoint'}
            texts.append(part['text']);source_regions.append(chosen);offset+=len(part['text'])
    elif mode=='merge':
        if len(old)<2 or change.get('separator') not in ('',' ','\n'):raise ValueError('choose_cells_and_original_separator')
        texts=[change['separator'].join(cell_text(c) for c in old)];source_regions=[[r for c in old for r in regions(c)]]
    elif mode=='supplement':
        if old or not isinstance(change.get('text'),str):raise ValueError('missing_cell_text_required')
        ref=source_reference(change.get('locator'),doc)
        if 'page_index' not in ref or 'bbox' not in ref:raise ValueError('missing_cell_requires_original_page_region')
        texts=[change['text']];source_regions=[[ref]]
    else:raise ValueError('unsupported_cell_boundary_operation')
    spec=deepcopy(request.get('table_geometry'))
    if not isinstance(spec,dict) or not isinstance(spec.get('cells'),list):raise ValueError('corrected_grid_required')
    layout=spec['cells'];aliases={f'new:{i}':'cell:'+digest([request['request_id'],i])[:24] for i in range(len(texts))}
    if any(not isinstance(c,dict) or not isinstance(c.get('id'),str) for c in layout) or {c['id'] for c in layout}!=(set(by)-set(selected))|set(aliases):raise ValueError('boundary_grid_must_account_for_every_cell')
    created=[]
    for i,text in enumerate(texts):
        position=next(c for c in layout if c['id']==f'new:{i}');refs=source_regions[i]
        boxes=[r['bbox'] if isinstance(r['bbox'],list) else [r['bbox'][k] for k in ('x0','y0','x1','y1')] for r in refs if r['page_index']==refs[0]['page_index']]
        box=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
        c=dict(deepcopy(position),id=aliases[f'new:{i}'],page_index=refs[0]['page_index'],bbox=box,
               content={'review_text':text,'resolved_text':text,'resolution_status':'human_repair_pending'},source_regions=refs,
               provenance={'origin':'human_cell_'+mode,'request_id':request['request_id'],'source_sha256':doc['source']['content_hash'],
                           'source_cells':[{'id':c['id'],'sha256':digest(c)} for c in old]})
        created.append(c)
    owner.setdefault('table_cell_history',{}).update({c['id']:deepcopy(c) for c in old})
    owner['reviewed_cells']=[deepcopy(c) for c in current['cells'] if c['id'] not in selected]+created
    owner.pop('table_geometry',None)
    for c in layout:c['id']=aliases.get(c['id'],c['id'])
    if mode=='supplement':
        owner['reviewed_references']=deepcopy(owner.get('reviewed_references',owner['original'].get('references',[])))+source_regions[0]
    from .table_geometry import repair as geometry_repair
    # The external request remains unchanged for receipt idempotency. Grid validation and
    # related-row guards run before the transaction can commit this proposed overlay.
    changed=geometry_repair(doc,unit,dict(request,table_geometry=spec,target_fingerprint=digest(owner)))
    return changed
