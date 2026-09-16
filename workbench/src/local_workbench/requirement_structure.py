"""Source-bound clause containers and recursive quantified groups (version 1).

A clause binds fields; only a group counts direct children. NOT belongs to the
specific group, never to an inferred keyword or to its individual leaves.
"""
from copy import deepcopy
import uuid

SCHEMA = 'requirement-structure/1'
FIELDS = ('Subject', 'Modal Verb', 'Main Verb', 'Object', 'conditions', 'subrequirement')
ROLES = FIELDS + ('requirements',)


def walk(node, parent=None):
    yield node, parent
    for child in node.get('children', []):
        yield from walk(child, node)


def references(tree):
    return [n['target_id'] for n, _ in walk(tree) if n['kind'] == 'reference']


def group(identity, role, children=None, quantity=None, **extra):
    children = children or []
    return dict(id=identity, kind='group', role=role, quantity=quantity,
                negated=False, children=children, **extra)


def legacy(doc, uid):
    """Deterministic read projection. Never rewrites the saved legacy record."""
    if uid in doc.get('structures', {}):
        return deepcopy(doc['structures'][uid])
    u = doc['units'][uid]
    root = dict(id=uid + '/structure', kind='clause', span=[0, len(u['text'])], children=[])
    for field in FIELDS[:4]:
        if not u.get(field):
            continue
        span = doc.get('field_spans', {}).get(uid, {}).get(field)
        # Older unanchored fields stay visible but are not guessed in repeated text.
        leaf = dict(id=uid + '/' + field + '/value', kind='fragment', role=field, text=u[field])
        if span is not None:
            leaf['span'] = deepcopy(span)
        else:
            leaf['unanchored'] = True
        root['children'].append(group(uid + '/' + field, field, [leaf], 1))

    def convert(value, field, path):
        children = []
        for i, child in enumerate(value[1:], 1):
            identity = uid + '/' + path + '/' + str(i)
            if isinstance(child, list):
                children.append(convert(child, field, path + '/' + str(i)))
            else:
                children.append(dict(id=identity, kind='reference', role=field, target_id=child))
        return group(uid + '/' + path, field, children, deepcopy(value[0]))

    conditions = []
    if u.get('conditions'):
        conditions.append(convert(u['conditions'], 'conditions', 'conditions'))
    if u.get('exceptions'):
        exception = convert(u['exceptions'], 'conditions', 'exceptions')
        exception.update(negated=True, origin_role='exceptions')
        conditions.append(exception)
    if len(conditions) == 2:
        root['children'].append(group(uid + '/applicability', 'conditions', conditions, 2))
    else:
        root['children'].extend(conditions)
    if u.get('subrequirement'):
        root['children'].append(convert(u['subrequirement'], 'subrequirement', 'subrequirement'))
    return root


def views(doc):
    return {uid: legacy(doc, uid) for uid in doc['units']}


def response(doc):
    return dict(doc, structure_views=views(doc))


def validate(doc):
    structures = doc.get('structures', {})
    if not isinstance(structures, dict) or not set(structures) <= set(doc['units']):
        raise ValueError('Unknown Requirement structure owner.')
    if structures and doc.get('structure_schema') != SCHEMA:
        raise ValueError('Unsupported Requirement structure version.')
    all_ids=set()
    for uid, tree in structures.items():
        text = doc['units'][uid]['text']; ids = set(); count = 0
        def check(n, parent=None, enclosing=(0, len(text)), depth=0):
            nonlocal count
            count += 1
            if depth > 24 or count > 3000 or not isinstance(n, dict):
                raise ValueError('This structure exceeds the supported nesting or size.')
            nid = n.get('id')
            if not isinstance(nid, str) or not 1 <= len(nid) <= 250 or nid in ids or nid in all_ids:
                raise ValueError('Every structure node needs a distinct stable ID.')
            ids.add(nid);all_ids.add(nid)
            kind = n.get('kind'); role = n.get('role')
            allowed = {'id', 'kind', 'span', 'children'} if kind == 'clause' else {'id', 'kind', 'role', 'span'}
            allowed |= {'group': {'children', 'quantity', 'negated', 'origin_role'}, 'fragment': {'text', 'unanchored'}, 'reference': {'target_id'}}.get(kind, set())
            if kind not in ('clause', 'group', 'fragment', 'reference') or set(n) - allowed:
                raise ValueError('Invalid structure node.')
            if kind=='clause' and 'span' not in n:raise ValueError('A clause needs its source span.')
            if parent is None and n.get('span') != [0,len(text)]:raise ValueError('The root must cover its complete Requirement source.')
            if parent is None and kind != 'clause':
                raise ValueError('A Requirement needs a clause container.')
            if kind != 'clause' and role not in ROLES:
                raise ValueError('Unknown structure field.')
            if parent:
                if parent['kind'] == 'clause' and (kind != 'group' or role not in ROLES):
                    raise ValueError('A clause contains field groups, not a quantity over mixed fields.')
                if parent['kind'] == 'group':
                    if parent['role'] == 'requirements':
                        if kind not in ('clause', 'group', 'reference') or (kind != 'clause' and role != 'requirements'):
                            raise ValueError('Requirement groups contain complete clauses or references.')
                    elif kind == 'clause' or role != parent['role']:
                        raise ValueError('A field group must retain its field role.')
            bounds = enclosing
            if 'span' in n:
                s = n['span']
                if not isinstance(s, list) or len(s) != 2 or any(type(v) is not int for v in s) or not enclosing[0] <= s[0] < s[1] <= enclosing[1]:
                    raise ValueError('The selected wording must remain inside its source group.')
                bounds = s
            if kind == 'fragment':
                if 'span' in n:
                    if n.get('text') != text[bounds[0]:bounds[1]]:
                        raise ValueError('Field wording must match its exact source range.')
                elif not n.get('unanchored') or n.get('text') not in text or not n.get('text'):
                    raise ValueError('A field needs source evidence.')
            elif kind == 'reference':
                if not isinstance(n.get('target_id'), str):
                    raise ValueError('Choose an existing Requirement reference.')
            else:
                children = n.get('children')
                if not isinstance(children, list):
                    raise ValueError('Invalid group children.')
                if kind == 'clause' and len({c.get('role') for c in children}) != len(children):
                    raise ValueError('A clause has one group per field.')
                if kind == 'group':
                    if type(n.get('negated')) is not bool or n.get('origin_role') not in (None, 'exceptions'):
                        raise ValueError('Invalid group negation or provenance.')
                    q = n.get('quantity')
                    bounds_q = [q, q] if type(q) is int else q
                    if q is not None and (not isinstance(bounds_q, list) or len(bounds_q) != 2 or any(type(v) is not int for v in bounds_q) or not 0 <= bounds_q[0] <= bounds_q[1] <= len(children)):
                        raise ValueError('QC must be an integer or inclusive range within this group size.')
                for child in children:
                    check(child, n, bounds, depth + 1)
        check(tree)


def pending(tree):
    return any((n['kind']=='clause' and not n['children']) or (n['kind']=='group' and (not n['children'] or n['quantity'] is None)) for n, _ in walk(tree))


def edit(doc, r):
    uid = r['unit_id']
    tree = legacy(doc, uid)
    nodes = {n['id']: (n, p) for n, p in walk(tree)}
    target, parent = nodes.get(r.get('node_id'), (None, None))
    if target is None:
        raise ValueError('This group changed. Select it again.')
    op = r.get('operation')
    def identity(suffix):
        return str(uuid.uuid5(uuid.UUID(r['request_id']), suffix))
    def refresh(g):
        # Membership is a human decision: a new multi-item combination is unresolved.
        g['quantity'] = 1 if len(g['children']) == 1 else None
    def field_group(role):
        if target['kind'] == 'clause':
            found = next((c for c in target['children'] if c['role'] == role), None)
            if found is None:
                found = group(identity('field'), role)
                target['children'].append(found)
            return found
        if target['kind'] != 'group' or target['role'] != role:
            raise ValueError('Select the matching field group.')
        return target
    if op in ('add', 'add-group'):
        start, end = r.get('start'), r.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(doc['units'][uid]['text']):
            raise ValueError('Select source wording before adding a field or Group.')
        if not doc['units'][uid]['text'][start:end].strip():raise ValueError('Select nonempty source wording.')
        role = r.get('field')
        if op == 'add-group':
            role = ('conditions' if doc['roles'].get(uid)=='condition' else 'requirements') if target['kind'] == 'clause' else target.get('role')
            child = (dict(id=identity('clause'), kind='clause', span=[start, end], children=[]) if role == 'requirements'
                     else group(identity('group'), role, span=[start, end]))
        else:
            if role not in FIELDS:
                raise ValueError('Choose a source field.')
            child = dict(id=identity('fragment'), kind='fragment', role=role, span=[start, end], text=doc['units'][uid]['text'][start:end])
        dest = field_group(role); dest['children'].append(child); refresh(dest)
    elif op == 'link':
        role = 'subrequirement' if target['kind'] == 'clause' else target.get('role')
        if role not in ('subrequirement', 'requirements'):
            raise ValueError('Link complete Requirements in a requirement group.')
        dest = field_group(role)
        if any(c.get('target_id') == r.get('target_id') for c in dest['children']):
            raise ValueError('This Requirement is already in the group.')
        dest['children'].append(dict(id=identity('reference'), kind='reference', role=role, target_id=r.get('target_id'))); refresh(dest)
    elif op in ('quantity', 'not'):
        if target['kind'] != 'group':
            raise ValueError('QC and NOT apply to a combination, not to mixed fields.')
        target['quantity' if op == 'quantity' else 'negated'] = deepcopy(r.get('quantity' if op == 'quantity' else 'negated'))
    elif op == 'decompose':
        if target['kind'] != 'fragment' or 'span' not in target:
            raise ValueError('Only an anchored source fragment can be decomposed here.')
        original = deepcopy(target)
        target.clear(); target.update(group(original['id'], original['role'], span=original['span']))
    elif op == 'group':
        if target['kind'] != 'group':
            raise ValueError('Select siblings in one field or Requirement combination.')
        picked = r.get('selected')
        if not isinstance(picked, list) or len(picked) < 1 or len(picked) != len(set(picked)) or not set(picked) <= {c['id'] for c in target['children']}:
            raise ValueError('Select direct items in this group.')
        chosen = [c for c in target['children'] if c['id'] in picked]
        node = group(identity('group'), target['role'], chosen, 1 if len(chosen) == 1 else None)
        children = []
        for c in target['children']:
            if c is chosen[0]: children.append(node)
            if c['id'] not in picked: children.append(c)
        target['children'] = children; refresh(target)
    elif op in ('remove', 'ungroup'):
        if parent is None:
            raise ValueError('Remove the Requirement entry to remove its root.')
        if op == 'ungroup':
            if target['kind'] != 'group' or parent['kind'] != 'group' or target['negated'] or target['quantity'] != len(target['children']):
                raise ValueError('Only an All group without NOT can be expanded. Other groups would lose their meaning.')
            if parent['quantity'] != len(parent['children']) or parent['negated']:
                raise ValueError('Expand only inside an All group without NOT.')
        index = parent['children'].index(target)
        parent['children'][index:index+1] = target['children'] if op == 'ungroup' else []
        if parent['kind'] == 'group': refresh(parent)
    else:
        raise ValueError('Unknown structure operation.')
    before = set(references(legacy(doc, uid)))
    doc.setdefault('structures', {})[uid] = tree; doc['structure_schema'] = SCHEMA
    # Removing an existing local reference never destroys that saved unit.
    from .requirements import append, leaves
    for removed in before - set(references(tree)):
        if removed in doc['units'] and removed not in leaves(doc['roots']):
            doc['roots'] = append(doc['roots'], removed)
    validate(doc)
    doc['done'] = [x for x in doc['done'] if x != uid]
