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


def empty_design():
    return {'schema': 'requirement-check-design/1', 'groups': {k: None for k in GROUPS}}


def validate_design(value):
    """Accept explicit typed mappings only, with bounded AND/OR trees and stable IDs."""
    if value is None:
        return empty_design()
    if not isinstance(value, dict) or set(value) != {'schema', 'groups'} or value['schema'] != 'requirement-check-design/1':
        raise ValueError('Unsupported check design format.')
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
            if set(item) != {'id', 'condition', 'rules'} or item['condition'] not in ('AND', 'OR'):
                raise ValueError('Groups must explicitly use AND or OR; negation belongs to an explicit operator.')
            if not isinstance(item['rules'], list) or not item['rules']:
                raise ValueError('A group must contain at least one rule.')
            return dict(id=identity, condition=item['condition'], rules=[node(x, depth+1) for x in item['rules']])
        if set(item) != {'id', 'field', 'operator', 'value', 'type', 'interpretation_field'}:
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
    return dict(schema=value['schema'], groups={k: node(v) if v is not None else None for k,v in value['groups'].items()})


def querybuilder_projection(design):
    """Strip provenance extension keys for downstream Filter(models, query).

    These are independent filters, not a compiled compliance verdict. Site Model
    must validate its field allowlist, joins, event context and evidence semantics.
    """
    design = validate_design(design)
    def project(n):
        if 'rules' in n: return dict(condition=n['condition'], rules=[project(x) for x in n['rules']])
        return {k:n[k] for k in ('field', 'operator', 'value')}
    return {k: project(v) if v else None for k,v in design['groups'].items()}
