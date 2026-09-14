"""One source-backed effective view for review, classification and delivery."""
from copy import deepcopy
import json
import re


def table_source(unit):
    body=unit.get('original',{}).get('fields',{}).get('body','')
    if isinstance(body,str) and body.lstrip().startswith('{'):
        try: value=json.loads(body)
        except ValueError: return None
        if isinstance(value,dict) and isinstance(value.get('cells'),list): return value
    return None


def cell_text(cell):
    content=cell.get('content') or {}
    for key in ('review_text','resolved_text','native_text','ocr_text'):
        if content.get(key) is not None:return content[key]
    return ''


def table_owner(unit, units):
    if table_source(unit) is not None:return unit
    for identity in unit.get('dependencies',[]):
        candidate=units.get(identity)
        if candidate and table_source(candidate) is not None:
            ids={c['id'] for c in table_source(candidate)['cells']}|{c['id'] for c in candidate.get('reviewed_cells',[])}|set(candidate.get('table_cell_history',{}))
            refs={r.get('locator') for r in unit.get('reviewed_references',unit['original'].get('references',[]))}
            if refs and refs <= ids:return candidate
    return None


def table_view(owner):
    table=deepcopy(table_source(owner))
    if table is None:return None
    if 'reviewed_cells' in owner:table['cells']=deepcopy(owner['reviewed_cells'])
    geometry=owner.get('table_geometry')
    if geometry:
        table.update(row_count=geometry['row_count'],column_count=geometry['column_count'])
        by_id={c['id']:c for c in geometry['cells']}
        for cell in table['cells']:cell.update(by_id[cell['id']])
    for cell in table['cells']:
        if cell['id'] in owner.get('cell_edits',{}):
            cell.setdefault('content',{})['review_text']=owner['cell_edits'][cell['id']]
            cell['content']['resolved_text']=owner['cell_edits'][cell['id']]
    table['cells'].sort(key=lambda c:(c['row'],c['column']))
    table['html']=table_html(table)
    return table


def table_html(table):
    from html import escape
    # A row view displays the shared cell at its selected row, while the result
    # retains the original cell coordinates and span as evidence.
    if type(table.get('selected_row')) is int:
        r=table['selected_row']
        table=dict(table,row_count=1,cells=[dict(c,row=0,row_span=1) for c in table['cells'] if c['row']<=r<c['row']+c['row_span']])
    return '<table>'+''.join('<tr>'+''.join(
        '<{tag} rowspan="{rs}" colspan="{cs}">{text}</{tag}>'.format(tag='th' if c.get('is_header') else 'td',rs=escape(str(c.get('row_span',1))),cs=escape(str(c.get('column_span',1))),text=escape(cell_text(c)))
        for c in sorted(table['cells'],key=lambda c:c['column']) if c['row']==row)+'</tr>' for row in range(table['row_count']))+'</table>'


def resolve(unit, units=None):
    units=units or {unit['id']:unit}
    fields=dict(unit['original'].get('fields',{}))
    result=dict(unit['original'],id=unit['id'],kind=unit['kind'],
        references=unit.get('reviewed_references',unit['original'].get('references',[])),
        structure=unit.get('reviewed_structure',unit['original'].get('structure',[])))
    if unit.get('table_assembly'):
        from .table_assembly import view
        try:
            assembled=view(unit,units);table=assembled.pop('table')
            rows={}
            for cell in table['cells']:rows.setdefault(cell['row'],[]).append(cell_text(cell))
            fields['body']='\n'.join(' | '.join(values) for values in rows.values())
            return dict(result,fields=fields,table=table,table_scope='cross_page_table',table_assembly=assembled,
                        structure=[table],related_content=[])
        except ValueError as error:
            return dict(result,fields=fields,table_assembly={'id':unit['id'],'error':str(error),
                        'fragments':deepcopy(unit['table_assembly']['fragments'])},related_content=[])
    owner=table_owner(unit,units)
    if owner:
        table=table_view(owner)
        if owner['id']!=unit['id']:
            # Preserve source-bound header evidence before narrowing to selected
            # row cells. This is context, not a new editable business schema.
            result['source_table_headers']=deepcopy([c for c in table['cells'] if c.get('is_header')])
            ids={r.get('locator') for r in unit.get('reviewed_references',unit['original'].get('references',[]))}
            table['cells']=[c for c in table['cells'] if c['id'] in ids]
            row_numbers={c['row'] for c in table['cells']}
            selected=unit.get('table_row_binding',next(iter(row_numbers)) if len(row_numbers)==1 else None)
            if selected is not None:table['selected_row']=selected
            table['html']=table_html(table)
            result['table_scope']='selected_cells'
        else:
            result['table_scope']='whole_table'
        cells=sorted(table['cells'],key=lambda c:(c['column'],c['row']) if 'selected_row' in table else (c['row'],c['column']))
        all_ids={c['id'] for c in table_source(owner)['cells']}|set(owner.get('table_cell_history',{}))|{c['id'] for c in table['cells']}
        unrelated=[s for s in result['structure'] if not isinstance(s,dict) or (not isinstance(s.get('cells'),list) and s.get('id') not in all_ids)]
        result['structure']=unrelated+deepcopy([table] if owner['id']==unit['id'] else cells)
        texts=[cell_text(c) for c in cells]
        if owner['id']==unit['id']:
            rows={}
            for c in cells:rows.setdefault(c['row'],[]).append(cell_text(c))
            fields['body']='\n'.join(' | '.join(v) for v in rows.values())
        else:
            from ..domains.requirements.table_row_fields import project as row_fields
            projected,_=row_fields(texts)
            fields.pop('identifier',None)
            fields.update(projected)
        result['table']=table
        result['table_owner_id']=owner['id']
        result['table_owner_version']=owner.get('version',1)
        if 'table_row_dispositions' in owner:result['table_row_dispositions']=deepcopy(owner['table_row_dispositions'])
    fields.update(unit.get('edits',{}))
    from ..domains.requirements.review_hierarchy import value,ancestors
    hierarchy=value(unit)
    if hierarchy:
        result['hierarchy']=hierarchy
        result['ancestors']=[a for a in ancestors(unit,units) if not a.get('unresolved')]
        result['reading_order_key']=unit.get('reading_order_key',str(unit.get('source_order',0)))
        result['kind']={'heading':'source_heading','paragraph':'source_text','footnote':'source_note','list_item':'source_list_item','figure':'source_image','caption':'source_caption','header':'source_text','footer':'source_text'}.get(hierarchy.get('type'),result['kind'])
    related=[]
    links=deepcopy(unit.get('content_relations',[]))
    if owner and owner['id']!=unit['id']:
        explicit={(l['role'],l['target_unit_id']) for l in links}
        links.extend(dict(l,inherited_from_table=owner['id']) for l in owner.get('content_relations',[]) if (l['role'],l['target_unit_id']) not in explicit)
    from fractions import Fraction
    links.sort(key=lambda l:Fraction(str(units.get(l['target_unit_id'],{}).get('reading_order_key',units.get(l['target_unit_id'],{}).get('source_order',0)))))
    for link in links:
        target=units.get(link['target_unit_id'])
        if target is None:raise ValueError('related_content_not_loaded:'+link['target_unit_id'])
        target_fields=resolve(target,units)['fields'] if table_owner(target,units) else dict(target['original'].get('fields',{}),**target.get('edits',{}))
        related.append(dict(link,version=target.get('version',1),fields=target_fields,
            references=target.get('reviewed_references',target['original'].get('references',[]))))
    notes=[r['fields'].get('body') or r['fields'].get('notes') or r['fields'].get('title','') for r in related if r['role']=='notes']
    if notes:fields['notes']='\n'.join(dict.fromkeys([fields.get('notes',''),*notes])).strip()
    if unit.get('table_assembly_id'):
        result['table_assembly_id']=unit['table_assembly_id']
        assembly=units.get(unit['table_assembly_id'])
        if assembly and not assembly.get('superseded_by'):
            from .table_assembly import view
            try:
                assembled=view(assembly,units)
                result['table_assembly']={k:v for k,v in assembled.items() if k!='table'}
            except ValueError as error:result['table_assembly']={'id':assembly['id'],'error':str(error)}
    result.update(fields=fields,related_content=related)
    return result
