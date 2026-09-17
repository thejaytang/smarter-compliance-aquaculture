"""Semantic input to an original check, independent of review/acceptance versions.

Structure packets bind relationships without spending the same text twice in
coverage checks. They are output claims, not independent source annotations.
"""
from copy import deepcopy

from ..contracts.hashing import digest
from ..domains.requirements.pdf_review_scope import pages
from . import effective


def cell_references(cell):
    return deepcopy(cell.get('source_regions') or [
        dict(page_index=cell.get('page_index'), bbox=cell.get('bbox'))])


def semantic(value):
    """Review-only version increments must not stale an unchanged source check."""
    if isinstance(value, dict):
        result = deepcopy(value)
        result.pop('version', None)
        if 'fragments' in result:
            result['fragments'] = semantic(result['fragments'])
        return result
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def table_claim(table):
    cells = []
    for cell in table['cells']:
        item = {k: deepcopy(cell[k]) for k in (
            'id', 'row', 'column', 'row_span', 'column_span', 'is_header',
            'source_table_id', 'source_cell_id', 'source_row') if k in cell}
        item.update(references=cell_references(cell), text_sha256=digest(effective.cell_text(cell)))
        cells.append(item)
    return {**{k: table[k] for k in ('row_count', 'column_count', 'selected_row') if k in table},
            'cells': sorted(cells, key=lambda c: c['id'])}


def comparison_input(doc, page_index):
    by_id = {u['id']: u for u in doc['units']}
    records = []
    for unit in doc['units']:
        if unit['kind'] == 'coverage' or unit.get('superseded_by') or unit.get('evidence_only'):
            continue
        if page_index not in pages(unit):
            continue
        view = effective.resolve(unit, by_id)
        owner = effective.table_owner(unit, by_id)
        table = view.get('table')
        structure = {'schema': 'pdf-output-structure/1', 'kind': view['kind'],
                     'reading_order_key': unit.get('reading_order_key', unit.get('source_order'))}
        for key in ('hierarchy', 'ancestors', 'related_content', 'table_scope',
                    'table_owner_id', 'table_assembly_id', 'table_assembly'):
            if key in view:
                structure[key] = semantic(view[key])
        for link in structure.get('related_content', []):
            target = by_id[link['target_unit_id']]
            from ..domains.requirements.review_hierarchy import value
            link['target_structure'] = dict(kind=target['kind'], hierarchy=value(target),
                structure=deepcopy(target.get('reviewed_structure', target['original'].get('structure', []))),
                superseded_by=target.get('superseded_by'), evidence_only=target.get('evidence_only', False))
            if effective.table_owner(target, by_id):
                link['target_structure']['table'] = table_claim(effective.resolve(target, by_id)['table'])
        if unit.get('table_assembly'):
            structure['assembly_definition'] = deepcopy(unit['table_assembly'])
        if table is not None:
            structure['table'] = table_claim(table)
        else:
            structure['structure'] = deepcopy(view.get('structure', []))
        # Row-specific/inherited relations and logical assemblies have their
        # own claims even though physical cell text has only one owner.
        records.append(dict(id=unit['id']+':structure', unit_id=unit['id'],
                            record_kind='structure_only', text='',
                            references=deepcopy(view['references']), structure=structure))
        if unit.get('table_assembly') or (owner and owner['id'] != unit['id']):
            continue
        if table is not None:
            for cell in table['cells']:
                refs = cell_references(cell)
                if any(r.get('page_index') == page_index for r in refs):
                    records.append(dict(id=unit['id']+':'+cell['id'], unit_id=unit['id'],
                                        text=effective.cell_text(cell), references=refs))
        else:
            # Linked notes are checked at their own original positions. Their
            # delivered/inherited wording stays bound in related_content.
            fields = dict(view['fields'])
            if any(link['role'] == 'notes' for link in view.get('related_content', [])):
                fields['notes'] = unit.get('edits', {}).get('notes', unit['original'].get('fields', {}).get('notes', ''))
            records.append(dict(id=unit['id'], unit_id=unit['id'],
                                text='\n'.join(str(v) for k, v in fields.items() if k != 'structure_note' and v != ''),
                                references=deepcopy(view['references'])))
    return sorted(records, key=lambda r: r['id'])
