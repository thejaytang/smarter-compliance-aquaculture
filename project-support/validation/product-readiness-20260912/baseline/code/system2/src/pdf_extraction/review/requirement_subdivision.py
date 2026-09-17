"""Provisional B decisions over accepted A text; never an A structural repair."""
from copy import deepcopy
from ..contracts.hashing import digest

SCHEMA = 'requirement-subdivision/1'
FIELDS = ('body', 'criteria', 'title', 'notes', 'context', 'applicability', 'level')


def basis(unit, view, source):
    # Exclude review flags/drafts, but include source version, A version, location
    # and resolved shared context. Returning to older wording requires re-review.
    return digest({'source': source, 'version': unit['version'], 'view': view})


def residual(fields, children):
    result = []
    for field in FIELDS:
        text = fields.get(field, '')
        spans = sorted((c['start'], c['end']) for c in children if c['field'] == field)
        cursor = 0
        for start, end in [*spans, (len(text), len(text))]:
            if text[cursor:start].strip():
                result.append({'field': field, 'start': cursor, 'end': start, 'text': text[cursor:start]})
            cursor = end
    return result


def apply(unit, view, source, request):
    if unit['kind'] == 'coverage' or unit.get('table_assembly') or unit.get('evidence_only') or unit.get('superseded_by'):
        raise ValueError('subdivision_requires_current_requirement_content')
    if not view.get('references'):
        raise ValueError('subdivision_requires_original_location')
    if request.get('subdivision_schema') != SCHEMA:
        raise ValueError('subdivision_policy_version_changed')
    count_basis = request.get('count_basis')
    if count_basis not in {'subitems', 'parent'}:
        raise ValueError('choose_provisional_count_basis')
    if request.get('complete_range_reviewed') is not True or not request.get('note', '').strip():
        raise ValueError('subdivision_requires_complete_parent_review_and_reason')
    parts = request.get('subitems')
    if not isinstance(parts, list) or not 2 <= len(parts) <= 100:
        raise ValueError('subdivision_requires_2_to_100_source_spans')
    children = []
    for i, part in enumerate(parts, 1):
        if not isinstance(part, dict) or set(part) - {'field', 'start', 'end', 'text', 'original_number'} or not {'field','start','end','text'} <= set(part):
            raise ValueError('subitem_requires_exact_original_span')
        field, start, end = part['field'], part['start'], part['end']
        text = view['fields'].get(field, '')
        if field not in FIELDS or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError('subitem_span_out_of_range')
        if not isinstance(part['text'], str) or not part['text'].strip() or part['text'] != text[start:end]:
            raise ValueError('subitem_must_match_accepted_original_text')
        if any(c['field'] == field and start < c['end'] and c['start'] < end for c in children):
            raise ValueError('subitem_spans_overlap')
        number = part.get('original_number') or None
        if number is not None:
            import re
            if not isinstance(number, str) or not re.fullmatch(r'[0-9A-Za-z.()\-]+', number) or not part['text'].lstrip().startswith(number):
                raise ValueError('original_number_must_be_selected_original_prefix')
            tail = part['text'].lstrip()[len(number):]
            if tail and not tail[0].isspace():
                raise ValueError('original_number_must_be_complete')
        children.append(dict(part, generated_label=f'Subitem {i}', original_number=number,
                             original_number_span=({'field':field,'start':start+len(part['text'])-len(part['text'].lstrip()),
                                 'end':start+len(part['text'])-len(part['text'].lstrip())+len(number),'text':number} if number else None)))
    remaining = residual(view['fields'], children)
    if remaining and not request.get('remainder_reason', '').strip():
        raise ValueError('explain_unassigned_original_text')
    return {'schema': SCHEMA, 'status': 'PROVISIONAL',
            'revision': unit.get('requirement_subdivision_revision', 0) + 1,
            'policy': {'count_basis': count_basis, 'parent_delivery': 'full_parent_with_linked_subitems',
                       'peer_confirmation': 'pending'},
            'basis_sha256': basis(unit, view, source), 'parent_original_number': view['fields'].get('identifier'),
            'parent_context': deepcopy(view), 'subitems': children, 'unassigned_spans': remaining,
            'remainder_reason': request.get('remainder_reason', '').strip(), 'actor': request['actor'],
            'request_id': request['request_id'], 'reason': request['note'].strip()}


def stale(unit, view, source):
    item = unit.get('requirement_subdivision')
    return bool(item and (item.get('schema') != SCHEMA or item['basis_sha256'] != basis(unit, view, source)))


def delivery(row, subdivision):
    """A single persisted parent envelope; counted rows are explicitly projected."""
    row = dict(row)
    count_parent = subdivision['policy']['count_basis'] == 'parent'
    row.update(delivery_role='requirement_parent', requirement_count=1 if count_parent else 0,
               subdivision=deepcopy(subdivision), subitems=[])
    for index, child in enumerate(subdivision['subitems'], 1):
        identity = f"{row['requirement_id']}:b{subdivision['revision']}:{index}"
        row['subitems'].append({'requirement_id': identity, 'parent_requirement_id': row['requirement_id'],
            'delivery_role': 'requirement_subitem', 'requirement_count': 0 if count_parent else 1,
            'fields': {'body': child['text']}, 'generated_label': child['generated_label'],
            'original_number': child['original_number'], 'original_number_span': child['original_number_span'],
            'parent_original_number': subdivision['parent_original_number'],
            'source': row['source'], 'unit_version': row['unit_version'], 'references': row['references'],
            'evidence_span': {k: child[k] for k in ('field', 'start', 'end', 'text')},
            'binding_scope': 'exact_accepted_text_span_with_parent_source_region',
            'parent_context': subdivision['parent_context'], 'decision_origin': 'human',
            'subdivision_schema': subdivision['schema'], 'subdivision_revision': subdivision['revision'],
            'provisional_policy': subdivision['policy'], 'canonical': row['canonical']})
    return row


def counted_rows(row):
    return [r for r in [row, *row.get('subitems', [])] if r.get('requirement_count', 1)]


def count(published):
    return sum(len(counted_rows(row)) for row in published.values())
