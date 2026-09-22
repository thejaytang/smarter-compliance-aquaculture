"""Validated QueryBuilder interchange. Never executes SQL or infers mappings."""
import math
import re
from copy import deepcopy

GROUPS = ('scope', 'condition', 'demand')
FIELD_KEYS = ('scope', 'scope_information', 'condition', 'condition_information', 'demand', 'verification')
OPERATORS = {'equal', 'not_equal', 'less', 'less_or_equal', 'greater', 'greater_or_equal',
             'in', 'not_in', 'between', 'not_between', 'is_null', 'is_not_null',
             'contains', 'not_contains', 'begins_with', 'ends_with', 'is_empty', 'is_not_empty'}
IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$')


def empty_design(version=1):
    value = {'schema': 'requirement-check-design/'+str(version), 'groups': {k: None for k in GROUPS}}
    if version == 2:
        value.update(object_type='', identity_field='', assessment_context='', based_on=None)
    return value


def validate_design(value, citations=None):
    """Accept explicit typed mappings only, with bounded AND/OR trees and stable IDs."""
    if value is None:
        return empty_design()
    if not isinstance(value, dict):
        raise ValueError('Unsupported check design format.')
    modern = value.get('schema') == 'requirement-check-design/2'
    extra = {'object_type', 'identity_field', 'assessment_context', 'based_on'} if modern else set()
    if modern and 'concepts' in value: extra.add('concepts')
    concepts = value.get('concepts', [])
    if not isinstance(concepts, list) or len(concepts) > 200: raise ValueError('Use at most 200 concepts.')
    concept_ids = set()
    for concept in concepts:
        if not isinstance(concept, dict) or set(concept) != {'id', 'label', 'kind', 'status', 'references'}:
            raise ValueError('A concept needs an ID, label, kind, status and references.')
        identity = concept['id']
        if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', identity) or identity in concept_ids:
            raise ValueError('Concept IDs must be unique and stable.')
        concept_ids.add(identity)
        if not isinstance(concept['label'], str) or not 1 <= len(concept['label'].strip()) <= 200 or concept['kind'] not in ('concept', 'relation', 'property', 'event', 'action') or concept['status'] not in ('proposed', 'confirmed'):
            raise ValueError('Invalid concept name, type or confirmation status.')
        refs = concept['references']
        if not isinstance(refs, list) or len(refs) > 100: raise ValueError('Invalid concept references.')
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {'id', 'quote'} or not isinstance(ref['id'], str) or not isinstance(ref['quote'], str) or not 1 <= len(ref['quote']) <= 30000:
                raise ValueError('A concept reference needs an exact source quotation.')
            if citations is not None and not any(c['id'] == ref['id'] and ref['quote'] in c['text'] for c in citations):
                raise ValueError('Concept quotation is not present in the supplied source context.')
    if set(value) != {'schema', 'groups'} | extra or value.get('schema') not in ('requirement-check-design/1', 'requirement-check-design/2'):
        raise ValueError('Unsupported check design format.')
    if modern:
        for key in ('object_type', 'identity_field', 'assessment_context'):
            if not isinstance(value[key], str) or len(value[key]) > 4000:
                raise ValueError('Use bounded text for the object domain and assessment context.')
        if value['identity_field'] and not IDENTIFIER.fullmatch(value['identity_field']):
            raise ValueError('Object identity needs a table.column mapping, or leave it unmapped.')
        basis = value['based_on']
        if basis is not None:
            if not isinstance(basis, dict) or set(basis) != {'fields', 'context_fingerprint', 'catalog_revision', 'design'}:
                raise ValueError('Invalid mapping confirmation.')
            if not isinstance(basis['fields'], dict) or set(basis['fields']) != set(FIELD_KEYS) or any(not isinstance(v, str) or len(v) > 30000 for v in basis['fields'].values()):
                raise ValueError('Mapping confirmation needs the six interpreted values.')
            if not isinstance(basis['context_fingerprint'], str) or len(basis['context_fingerprint']) > 200 or type(basis['catalog_revision']) is not int or basis['catalog_revision'] < 0:
                raise ValueError('Invalid mapping context or catalog version.')
            if not isinstance(basis['design'], dict) or set(basis['design']) != ({'schema', 'groups', 'object_type', 'identity_field', 'assessment_context'} | ({'concepts'} if 'concepts' in basis['design'] else set())) or basis['design'].get('schema') != 'requirement-check-design/2':
                raise ValueError('Invalid confirmed rule snapshot.')
            validate_design(dict(basis['design'], based_on=None))
    if not isinstance(value['groups'], dict) or set(value['groups']) != set(GROUPS):
        raise ValueError('Check design needs Scope, Condition and Demand groups.')
    seen = set()

    def node(item, depth=0):
        if not isinstance(item, dict) or depth > 8 or len(seen) >= 200:
            raise ValueError('Rule design is too large or deeply nested.')
        identity = item.get('id')
        if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', identity) or identity in seen:
            raise ValueError('Every rule and group needs a unique stable ID.')
        seen.add(identity)
        if 'rules' in item:
            allowed = {'id', 'condition', 'rules'} | ({'not'} if modern and 'not' in item else set())
            if set(item) != allowed or item['condition'] not in ('AND', 'OR') or ('not' in item and type(item['not']) is not bool):
                raise ValueError('Groups must explicitly use AND or OR; negation belongs to an explicit operator.')
            if not isinstance(item['rules'], list) or not item['rules']:
                raise ValueError('A group must contain at least one rule.')
            result = dict(id=identity, condition=item['condition'], rules=[node(x, depth+1) for x in item['rules']])
            if 'not' in item: result['not'] = item['not']
            return result
        term_keys = {'concept_ids'} if modern and 'concept_ids' in item else set()
        if term_keys and (not isinstance(item['concept_ids'], list) or any(not isinstance(i, str) or i not in concept_ids for i in item['concept_ids']) or len(set(item['concept_ids'])) != len(item['concept_ids'])):
            raise ValueError('Rule concepts must refer to unique IDs in this design.')
        if modern and 'expression' in item:
            if set(item) - term_keys != {'id', 'expression', 'interpretation_field'} or not isinstance(item['expression'], str) or not 1 <= len(item['expression'].strip()) <= 4000 or item['interpretation_field'] not in FIELD_KEYS:
                raise ValueError('An unmapped predicate needs an expression and its interpretation field.')
            return deepcopy(item)
        if set(item) - term_keys != {'id', 'field', 'operator', 'value', 'type', 'interpretation_field'}:
            raise ValueError('A rule needs a field mapping, operator, typed value and interpretation field.')
        field, op, kind, val = item['field'], item['operator'], item['type'], item['value']
        if not isinstance(field, str) or len(field) > 200 or not IDENTIFIER.fullmatch(field):
            raise ValueError('Use an explicit table.column mapping, not SQL or source prose.')
        if not isinstance(op,str) or op not in OPERATORS or kind not in ('string', 'integer', 'double', 'boolean') or item['interpretation_field'] not in FIELD_KEYS:
            raise ValueError('Unsupported operator, value type or interpretation field.')
        def scalar(x):
            if kind == 'string': return isinstance(x, str) and len(x) <= 4000
            if kind == 'integer': return type(x) is int and abs(x) <= 9007199254740991
            if kind == 'double': return type(x) in (int, float) and math.isfinite(x)
            return type(x) is bool
        if op in ('is_null', 'is_not_null', 'is_empty', 'is_not_empty'):
            if val is not None: raise ValueError('This operator does not take a value.')
        elif op in ('in', 'not_in', 'between', 'not_between'):
            if not isinstance(val, list) or not 1 <= len(val) <= 100 or not all(scalar(x) for x in val):
                raise ValueError('Use a nonempty list of values of the selected type.')
            if op in ('between', 'not_between') and (len(val) != 2 or kind == 'boolean' or val[0] > val[1]):
                raise ValueError('Between needs an ordered pair of endpoints.')
        elif not scalar(val): raise ValueError('Rule value does not match its selected type.')
        if op in ('contains', 'not_contains', 'begins_with', 'ends_with', 'is_empty', 'is_not_empty') and kind != 'string':
            raise ValueError('Text operators require a string mapping.')
        if kind == 'boolean' and op not in ('equal', 'not_equal', 'is_null', 'is_not_null', 'in', 'not_in'):
            raise ValueError('This comparison is not defined for a boolean mapping.')
        return deepcopy(item)
    for v in value['groups'].values():
        if v is not None and (not isinstance(v,dict) or 'rules' not in v):
            raise ValueError('Each mapped section must start with an AND or OR group.')
    return dict(schema=value['schema'], groups={k: node(v) if v is not None else None for k,v in value['groups'].items()}, **{k: deepcopy(value[k]) for k in extra})


def logic_text(node):
    if not node: return ''
    if 'rules' in node:
        body = (' '+node['condition']+' ').join(logic_text(child) for child in node['rules'])
        return ('NOT ' if node.get('not') else '')+'('+body+')'
    if 'expression' in node: return node['expression']
    import json
    return node['field']+' '+node['operator']+' '+json.dumps(node['value'], ensure_ascii=False, separators=(',', ':'))


def logic_fields(fields, design):
    """Project edited rules without rewriting the saved contextual explanations."""
    result = deepcopy(fields)
    if design and 'concepts' in design:
        for key, node in design['groups'].items():
            if node: result[key].update(value=logic_text(node), basis='interpretation', state='specified', absence_reason='')
    return result


def concept_issues(design):
    if 'concepts' not in design: return []
    issues = [c['label']+': concept meaning needs confirmation.' for c in design['concepts'] if c['status'] != 'confirmed']
    def walk(n):
        if not n: return
        if 'rules' in n:
            for child in n['rules']: walk(child)
        elif not n.get('concept_ids'): issues.append('Link concepts to rule: '+logic_text(n))
    for node in design['groups'].values(): walk(node)
    return issues


def unmapped_nodes(node):
    if not node: return ['No rules defined.']
    if 'expression' in node: return ['Unmapped predicate: '+node['expression']]
    return (['Group negation needs a consumer mapping.'] if node.get('not') else []) + [gap for child in node.get('rules', []) for gap in unmapped_nodes(child)]


def querybuilder_projection(design):
    """Strip provenance extension keys for downstream Filter(models, query).

    These are independent filters, not a compiled compliance verdict. Site Model
    must validate its field allowlist, joins, event context and evidence semantics.
    """
    design = validate_design(design)
    def project(n):
        if 'rules' in n: return dict(condition=n['condition'], rules=[project(x) for x in n['rules']])
        return {k:n[k] for k in ('field', 'operator', 'value')}
    # An unsupported child blocks the entire filter, including OR/NOT branches.
    return {k: project(v) if v and not unmapped_nodes(v) else None for k,v in design['groups'].items()}


def set_handoff(fields, design, context_fingerprint, catalog):
    """Derive a non-executable set contract; no prose-to-SQL inference."""
    from backend.system3.interpretation_continuity import field_state
    design = validate_design(design)
    original_fields = fields
    fields = logic_fields(fields, design)
    sets = {}
    gaps = []
    for letter, key, domain in zip('ABC', GROUPS, ('U', 'A', 'U')):
        field = fields[key]
        resolved = field_state(field) == 'specified' and bool(field['value'].strip()) and field.get('basis') != 'unresolved' and not field.get('gaps')
        sets[letter] = dict(input=domain, interpretation_field=key, definition=logic_text(design['groups'][key]) if 'concepts' in design and design['groups'][key] else field['value'],
                            resolved=resolved, rules=deepcopy(design['groups'][key]), references=deepcopy(field.get('references', [])))
        if not resolved: gaps.append('Set '+letter+' definition needs review.')
        gaps.extend(key+': '+gap for gap in unmapped_nodes(design['groups'][key]))
    for key in ('object_type', 'identity_field', 'assessment_context'):
        if not design[key].strip(): gaps.append(key.replace('_', ' ').capitalize()+' is not specified.')
    for key in ('scope_information', 'condition_information', 'verification'):
        field = fields[key]
        if field_state(field) != 'specified' or not field['value'].strip() or field.get('basis') == 'unresolved' or field.get('gaps'):
            gaps.append(key.replace('_', ' ').capitalize()+' needs review.')
    gaps.extend(concept_issues(design))
    allowed = {f['field'] for f in catalog.get('fields', [])}
    if design['identity_field'] and design['identity_field'] not in allowed:
        gaps.append('Object identity is not in the Site Model catalog.')
    from backend.system3.site_catalog import mapping_issues
    gaps.extend(item['message'] for item in mapping_issues(design, catalog))
    expected = dict(fields={k: original_fields[k]['value'] for k in FIELD_KEYS}, context_fingerprint=context_fingerprint,
                    catalog_revision=catalog.get('revision', 0), design={k: v for k, v in design.items() if k != 'based_on'})
    confirmed = design['based_on'] == expected
    if not confirmed: gaps.append('Confirm mappings against the current Logic, source context and catalog.')
    return dict(schema='requirement-set-handoff/1', object_type=design['object_type'], identity_field=design['identity_field'],
                assessment_context=design['assessment_context'], sets=sets, **({'concepts': deepcopy(design['concepts'])} if 'concepts' in design else {}), composition=dict(operator='subset_of', left='B', right='C'),
                querybuilder=querybuilder_projection(design), mapping_status='incomplete' if gaps else 'ready_for_consumer_validation',
                gaps=list(dict.fromkeys(gaps)), executable=False)
