"""Versioned cross-page table views over unchanged physical table fragments."""
from copy import deepcopy
from fractions import Fraction

from ..contracts.hashing import digest
from .effective import table_source, table_view, table_html, cell_text, table_owner


def parts(assembly, units):
    result=[]
    for item in assembly['table_assembly']['fragments']:
        owner=units.get(item['unit_id'])
        if owner is None or owner.get('superseded_by') or owner.get('evidence_only'):
            raise ValueError('table_assembly_fragment_unavailable')
        table=table_view(owner)
        if table is None or table['column_count']!=assembly['table_assembly']['column_count']:
            raise ValueError('table_assembly_columns_changed')
        result.append((owner, table))
    return result


def view(assembly, units):
    fragments=parts(assembly,units);cells=[];offset=0;metadata=[];headers=[]
    for owner, table in fragments:
        metadata.append({'unit_id':owner['id'],'version':owner['version'],'row_offset':offset,
                         'row_count':table['row_count'],'references':deepcopy(owner.get('reviewed_references',owner['original'].get('references',[])))})
        for source in table['cells']:
            cell=deepcopy(source)
            cell.update(id=owner['id']+'::'+source['id'],row=offset+source['row'],
                        source_cell_id=source['id'],source_table_id=owner['id'],source_row=source['row'])
            cells.append(cell)
        if owner['id']==assembly['table_assembly']['header_source_id']:
            # Bind header identities, not a row number that later geometry could move.
            ids=assembly['table_assembly']['header_cell_ids']
            selected=[c for c in table['cells'] if c['id'] in ids]
            if len(selected)!=len(ids):raise ValueError('table_assembly_header_changed')
            if sorted(c['column'] for c in selected)!=list(range(table['column_count'])) or len({c['row'] for c in selected})!=1 or any(c['column_span']!=1 or c['row_span']!=1 or not cell_text(c).strip() for c in selected):
                raise ValueError('table_assembly_header_changed')
            headers=[{'column':c['column'],'text':cell_text(c),'source_table_id':owner['id'],
                      'source_cell_id':c['id'],'page_index':c.get('page_index'),'bbox':c.get('bbox')} for c in sorted(selected,key=lambda c:c['column'])]
        offset+=table['row_count']
    table={'row_count':offset,'column_count':assembly['table_assembly']['column_count'],'cells':cells}
    table['html']=table_html(table)
    return {'id':assembly['id'],'version':assembly['version'],'fragments':metadata,'column_headers':headers,'table':table}


def reconcile(doc):
    """Keep newly created row items gated by their assembly; never accept geometry drift."""
    units={u['id']:u for u in doc['units']}
    for assembly in list(units.values()):
        if not assembly.get('table_assembly') or assembly.get('superseded_by'):continue
        try:view(assembly,units);issue=None
        except ValueError as error:issue=str(error)
        old=[b for b in assembly.get('blockers',[]) if b.startswith('table_assembly_')]
        assembly['blockers']=[b for b in assembly.get('blockers',[]) if b not in old]+([issue] if issue else [])
        if old!=([issue] if issue else []):
            from .repairs import invalidate
            invalidate(units,[assembly['id']])
        ids={p['unit_id'] for p in assembly['table_assembly']['fragments']}
        for row in units.values():
            if row['id'] in ids or row.get('superseded_by') or row.get('table_assembly'):continue
            owner=table_owner(row,units)
            if owner and owner['id'] in ids and assembly['id'] not in row.get('dependencies',[]):
                row['dependencies']=list(dict.fromkeys(row.get('dependencies',[])+[assembly['id']]))
                row['table_assembly_id']=assembly['id']
                from .repairs import invalidate
                invalidate(units,[row['id']])


def repair(doc, unit, request):
    units={u['id']:u for u in doc['units']};spec=request.get('table_assembly')
    if doc['source'].get('file_format')!='pdf':raise ValueError('table_assembly_requires_pdf')
    if not isinstance(spec,dict) or not isinstance(spec.get('fragments'),list) or len(spec['fragments'])<2:
        raise ValueError('choose_at_least_two_table_fragments')
    ids=[p.get('unit_id') for p in spec['fragments']]
    if ids[0]!=unit['id'] or len(set(ids))!=len(ids):raise ValueError('table_assembly_fragment_order_invalid')
    owners=[];last_page=-1;columns=None
    for item in spec['fragments']:
        owner=units.get(item['unit_id'])
        if owner is None or table_source(owner) is None or owner.get('superseded_by') or owner.get('evidence_only'):
            raise ValueError('choose_current_primary_table_fragments')
        if item.get('fingerprint')!=digest(owner):raise ValueError('stale_table_assembly_fragment')
        if owner.get('table_assembly_id'):raise ValueError('table_fragment_already_assembled')
        if set(owner.get('drafts',{}))-({request['actor']} if owner is unit else set()):raise ValueError('table_fragment_has_unsubmitted_draft')
        table=table_view(owner)
        pages={c.get('page_index') for c in table['cells']}
        if not pages or any(type(p)!=int for p in pages) or min(pages)<=last_page:raise ValueError('choose_nonoverlapping_pages_in_original_order')
        last_page=max(pages)
        if columns is not None and table['column_count']!=columns:raise ValueError('repair_fragment_columns_before_assembly')
        columns=table['column_count'];owners.append(owner)
    header_source=units.get(spec.get('header_source_id'));header_ids=spec.get('header_cell_ids',[])
    if header_source not in owners or not header_ids or len(set(header_ids))!=len(header_ids):raise ValueError('choose_source_header_cells')
    identity='table-assembly:'+digest(request['request_id'])[:24]
    if identity in units:raise ValueError('table_assembly_identity_already_exists')
    from .hierarchy import ensure_order, ordered
    ensure_order(doc)
    key=lambda u:Fraction(str(u.get('reading_order_key',u['source_order'])))
    first=key(unit);previous=[key(u) for u in doc['units'] if key(u)<first]
    order=(max(previous)+first)/2 if previous else first-1
    refs=[deepcopy(r) for owner in owners for r in owner.get('reviewed_references',owner['original'].get('references',[]))]
    title='Combined table · pages '+', '.join(str(p+1) for p in sorted({c['page_index'] for o in owners for c in table_view(o)['cells']}))
    new={'id':identity,'kind':'source_table_assembly','original':{'fields':{'title':title,'body':''},'references':refs,'structure':[]},
         'dependencies':ids,'source_order':unit['source_order'],'reading_order_key':str(order),'version':1,'edits':{},'drafts':{},
         'content_human':False,'requirement_human':False,'touched':True,'classification':'context',
         'content_parts':[],'requirement_parts':[],'blockers':[],'chapter':unit.get('chapter','Original order'),
         'table_assembly':{'fragments':[{'unit_id':i} for i in ids],'column_count':columns,'header_source_id':header_source['id'],'header_cell_ids':header_ids},
         'provenance':{'origin':'human_table_assembly','actor':request['actor'],'request_id':request['request_id'],'source_sha256':doc['source']['content_hash']}}
    units[identity]=new;view(new,units)
    changed={identity,*ids}
    for row in units.values():
        if row.get('superseded_by') or row is new:continue
        owner=table_owner(row,units)
        if owner and owner['id'] in ids:
            if row.get('drafts') and row is not unit:raise ValueError('table_fragment_has_unsubmitted_draft')
            row['table_assembly_id']=identity;changed.add(row['id'])
            if row['id'] not in ids:row['dependencies']=list(dict.fromkeys(row.get('dependencies',[])+[identity]))
    seen=set();visiting=set()
    def visit(uid):
        if uid in visiting:raise ValueError('table_assembly_dependency_cycle')
        if uid in seen or uid not in units:return
        visiting.add(uid)
        for dep in units[uid].get('dependencies',[]):visit(dep)
        visiting.remove(uid);seen.add(uid)
    for uid in changed:visit(uid)
    doc['units'].append(new);doc['units']=ordered(doc['units'])
    return sorted(changed),[identity]
