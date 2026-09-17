"""Literal source roles and table-header evidence, never inferred business fields."""
import re

CONTEXT_TITLE = re.compile(r'^(?:rationale|how do i interpret this requirement\?)$', re.I)
CONTEXT_PREFIX = re.compile(r'^\s*(?:rationale(?:\s*[:–—-]\s*|\s*\n\s*)|how do i interpret this requirement\?\s*)', re.I)
FORMAL_BOUNDARY = re.compile(r'(?:^|\n)\s*(?:(?:\d+\.){2,}\d+[a-z]?\s+|(?:indicator|requirement|required (?:client|cab|auditor) actions)\s*:)', re.I)


def context_role(unit):
    """Only explicit local labels/nearest real heading identify source context.

    A sentence merely mentioning rationale is not a section label. A supplied
    source unit mixing a context label and a formal clause stays undetermined.
    """
    fields=unit.get('fields',{})
    body=str(fields.get('body','')).strip()
    marker=CONTEXT_PREFIX.match(body)
    evidence=None
    if marker:
        evidence=dict(kind='literal_context_prefix',text=marker.group(),field='body',start=0,end=marker.end())
    elif CONTEXT_TITLE.fullmatch(str(fields.get('title','')).strip()):
        evidence=dict(kind='literal_context_title',text=fields['title'],field='title')
    else:
        nearest=next((a for a in unit.get('ancestors',[]) if a.get('type')=='heading'),None)
        if nearest and nearest.get('id') and CONTEXT_TITLE.fullmatch(str(nearest.get('title','')).strip()):
            evidence=dict(kind='source_heading_context',text=nearest['title'],heading_id=nearest['id'],heading_version=nearest.get('version'))
    if evidence is None:return None
    rest=body[marker.end():] if marker else body
    separate_fields=any(str(fields.get(k,'')).strip() for k in ('criteria','notes','context'))
    mixed=bool(FORMAL_BOUNDARY.search(rest) or separate_fields or unit.get('kind') in {'standard_indicator','standard_principle'})
    return dict(evidence=evidence,mixed_roles=mixed)


def _text(cell):
    content=cell.get('content') or {}
    for key in ('review_text','resolved_text','native_text','ocr_text'):
        if content.get(key) is not None:return str(content[key])
    return ''


def indicator_row(unit):
    """Find a complete selected row beneath explicit Indicator/Requirement labels.

    Header evidence comes from the retained effective owning table. Numbering,
    a bare Yes, or a table elsewhere in the unit cannot establish this role.
    Ambiguous spans, multiple header cells or missing source locations abstain.
    """
    table=unit.get('table') or {}
    selected=table.get('selected_row')
    if type(selected) is not int:return None
    headers=[]
    for cell in unit.get('source_table_headers',[]):
        label=_text(cell).strip().rstrip(':').strip().casefold()
        if (cell.get('is_header') is True and label in {'indicator','requirement'}
                and all(type(cell.get(k)) is int for k in ('row','column','row_span','column_span'))
                and cell['row_span']>0 and cell['column_span']>0 and cell['row']+cell['row_span']<=selected
                and cell.get('id') and cell.get('bbox') and type(cell.get('page_index')) is int):
            headers.append((label,cell))
    header_rows=sorted({cell['row'] for _,cell in headers},reverse=True)
    if not header_rows:return None
    # The nearest labelled header boundary governs this row; do not fall back
    # past a malformed newer boundary to a convenient earlier header.
    candidates=[(label,c) for label,c in headers if c['row']==header_rows[0]]
    if len(candidates)!=2 or {label for label,_ in candidates}!={'indicator','requirement'}:return None
    by_role=dict(candidates)
    ranges={role:set(range(c['column'],c['column']+c['column_span'])) for role,c in candidates}
    if ranges['indicator'] & ranges['requirement']:return None
    cells=table.get('cells',[])
    refs={r.get('locator') for r in unit.get('references',[])}
    groups={role:[] for role in by_role}
    for cell in cells:
        if (cell.get('is_header') or cell.get('row')!=selected or cell.get('row_span')!=1
                or type(cell.get('column')) is not int or type(cell.get('column_span')) is not int
                or cell['column_span']<1 or not cell.get('id') or cell['id'] not in refs):return None
        occupied=set(range(cell['column'],cell['column']+cell['column_span']))
        roles=[role for role,columns in ranges.items() if occupied<=columns]
        if len(roles)!=1:return None
        groups[roles[0]].append(cell)
    if not all(groups.values()):return None
    for group in groups.values():
        occupied=[]
        for cell in group:occupied.extend(range(cell['column'],cell['column']+cell['column_span']))
        if len(occupied)!=len(set(occupied)):return None
    texts={role:'\n'.join(_text(c) for c in sorted(group,key=lambda c:c['column'])).strip() for role,group in groups.items()}
    if not all(texts.values()) or not re.search(r'[^\W\d_]',texts['indicator'],re.UNICODE):return None
    if texts['indicator'].casefold() in {'indicator','yes','no'}:return None
    return dict(kind='source_indicator_requirement_row',selected_row=selected,indicator=texts['indicator'],requirement_value=texts['requirement'],
                headers=[dict(id=c['id'],text=_text(c),row=c['row'],column=c['column'],column_span=c['column_span'],page_index=c['page_index'],bbox=c['bbox']) for _,c in candidates],
                source_cell_ids=[c['id'] for c in cells])
