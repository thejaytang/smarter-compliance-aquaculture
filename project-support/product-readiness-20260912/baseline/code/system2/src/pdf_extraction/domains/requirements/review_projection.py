"""Read-only cross-format evidence projection for two-stage review."""
from hashlib import sha256
import json
import re

from ...contracts.hashing import digest


def pointer(document, reference):
    value = document
    for part in reference.lstrip('/').split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def content_units(output, result, source):
    """Build a read-only projection. Preserve every unmapped source reference."""
    canonical_path = output / result.canonical_path
    raw = canonical_path.read_bytes()
    document = json.loads(raw)
    canonical_ref = {'path': str(canonical_path.resolve()), 'sha256': sha256(raw).hexdigest()}
    units = []

    def add(identity, kind, fields, references, issues=(), structure=(), dependencies=()):
        units.append({'id': identity, 'kind': kind,
                      'original': {'fields': fields, 'references': references, 'structure': list(structure)},
                      'blockers': list(issues), 'dependencies': list(dependencies),
                      'content_parts': [{'confidence': None, 'calibration_version': None, 'evidence': references}]})

    mapping_path = output / 'source-records.json'
    if mapping_path.is_file():
        mapping = json.loads(mapping_path.read_bytes())
        if mapping['canonical_sha256'] != canonical_ref['sha256']:
            raise ValueError('mapping_version_mismatch')
        for record in mapping['records']:
            fields = {key: '\n'.join(str(v['text']) for v in values if v.get('text') is not None)
                      for key, values in record['fields'].items()}
            references = [dict(ref, canonical_sha256=canonical_ref['sha256'])
                          for values in record['fields'].values() for value in values for ref in value['references']]
            if not references:
                references = [{'locator': record['locator'], 'canonical_sha256': canonical_ref['sha256']}]
            add(record['id'], record['kind'], fields, references, record.get('issues', []), record.get('structure', []))
        for residual in mapping['residual']:
            ref = residual['reference']
            value = pointer(document, ref['pointer'])
            add('residual:' + digest(ref)[:24], 'source_text',
                {'body': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)},
                [dict(ref, canonical_sha256=canonical_ref['sha256'])], ['unclassified_residual'])
    elif result.format == 'html':
        for node in document.get('atoms', document.get('nodes', [])):
            text = node.get('text', '')
            if text:
                add(node['id'], 'source_text', {'body': text},
                    [{'locator': node.get('locator', node['id']), 'canonical_sha256': canonical_ref['sha256']}], ['mapping_unavailable'])
    elif result.format == 'excel':
        for sheet in document['sheets']:
            for cell in sheet['cells']:
                add('cell:' + digest([sheet.get('name'), cell])[:24], 'source_text',
                    {'body': json.dumps(cell, ensure_ascii=False)},
                    [{'locator': sheet.get('name', '') + '!' + str(cell.get('address', '')), 'canonical_sha256': canonical_ref['sha256']}],
                    ['column_mapping_required'])
    elif result.format == 'pdf':
        for identity, block in document['blocks'].items():
            if block['type'] in {'document', 'section'}:
                continue
            refs = [dict(segment, canonical_sha256=canonical_ref['sha256'], block_id=identity)
                    for segment in block.get('segments', [])]
            content = block.get('content') or {}
            body = content.get('resolved_text') or content.get('native_text') or content.get('ocr_text') or ''
            if block.get('table'):
                # Table geometry is retained intact; classification must resolve its rows/columns.
                body = json.dumps(block['table'], ensure_ascii=False)
            block_id='pdf:' + digest([canonical_ref['sha256'], identity])[:24]
            kind='context' if block.get('table') else ('source_note' if block['type']=='note' else 'source_text')
            add(block_id, kind, {'body': body}, refs,
                block.get('quality', {}).get('issues', []), [block.get('table')] if block.get('table') else [])
            if block.get('table'):
                cells=block['table']['cells']
                for row in sorted({c['row'] for c in cells}):
                    current=sorted([c for c in cells if c['row']==row],key=lambda c:c['column'])
                    texts=[(c.get('content') or {}).get('resolved_text') or (c.get('content') or {}).get('native_text') or '' for c in current]
                    from .table_row_fields import project as row_fields
                    fields,number=row_fields(texts)
                    rowrefs=[{'canonical_sha256':canonical_ref['sha256'],'block_id':identity,
                        'locator':c['id'],'page_index':c['page_index'],'bbox':c['bbox']} for c in current]
                    add(block_id+':row:'+str(row),'standard_indicator' if number else 'source_text',fields,rowrefs,
                        ['merged_cell_relationship_review_required'] if any(c['row_span']>1 or c['column_span']>1 for c in current) else [],
                        current,[block_id])
    coverage_id = 'coverage:' + canonical_ref['sha256'][:20]
    # Parser findings remain explicit review blockers even when parsing returned review_required.
    coverage_issues=[code for code in result.reason_codes if code not in {'uncalibrated_template_extraction','document_window_only'}]
    for conflict in document.get('conflicts',[]):
        if conflict.get('status') not in {'resolved','accepted'}:
            coverage_issues.append('canonical_conflict:'+str(conflict.get('id','unresolved')))
    add(coverage_id, 'coverage', {'body': 'Verify completeness, reading order, tables, notes and non-text regions against this source range.'},
        [{'canonical_sha256': canonical_ref['sha256'], 'locator': 'whole parsed range'}],
        coverage_issues)
    for unit in units:
        if unit['id'] != coverage_id:
            unit['dependencies'].append(coverage_id)
    from .review_groups import group_units, order_units
    return group_units(order_units(units,{canonical_ref['sha256']:document})), [canonical_ref]
