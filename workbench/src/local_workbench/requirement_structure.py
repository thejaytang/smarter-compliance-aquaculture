"""Source-bound clause containers and recursive quantified groups (version 1).

A clause binds fields; only a group counts direct children. NOT belongs to the
specific group, never to an inferred keyword or to its individual leaves.
"""
from copy import deepcopy
import uuid

SCHEMA = 'requirement-structure/1'
FIELDS = ('Subject', 'Modal Verb', 'Main Verb', 'Object', 'conditions', 'exceptions', 'subrequirement')
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

    if u.get('conditions'):
        root['children'].append(convert(u['conditions'], 'conditions', 'conditions'))
    if u.get('exceptions'):
        root['children'].append(convert(u['exceptions'], 'exceptions', 'exceptions'))
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
                    if parent['role'] in ('requirements','exceptions'):
                        if kind not in ('clause', 'group', 'reference') or (kind != 'clause' and role != parent['role']):
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


def edit(doc, r, _clear_linked=True):
    uid = r['unit_id']
    tree = legacy(doc, uid)
    nodes = {n['id']: (n, p) for n, p in walk(tree)}
    target, parent = nodes.get(r.get('node_id'), (None, None))
    if target is None:
        raise ValueError('This group changed. Select it again.')
    op = r.get('operation')
    linked_before=[];queue=references(tree)
    while queue:
        child_uid=queue.pop()
        if child_uid not in doc['units'] or child_uid in linked_before or child_uid==uid:continue
        linked_before.append(child_uid);queue.extend(references(legacy(doc,child_uid)))
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
    def source_span(n):
        if n.get('span'):return n['span']
        if n['kind']=='reference' and n['target_id'] in doc['spans']:
            offset=doc['spans'][uid][0];return [x-offset for x in doc['spans'][n['target_id']]]
        spans=[source_span(c) for c in n.get('children',[])];spans=[x for x in spans if x]
        return [min(x[0] for x in spans),max(x[1] for x in spans)] if spans else None
    def all_items(n):return (not n.get('children') or n.get('quantity') in (len(n['children']),[len(n['children'])]*2)) and not n.get('negated')
    if op=='clear-range':
        start,end=r.get('start'),r.get('end')
        if type(start) is not int or type(end) is not int or not 0<=start<end<=len(doc['units'][uid]['text']):raise ValueError('Select original wording first.')
        def clear(n):
            if 'children' not in n:return
            result=[];changed=False
            for c in n['children']:
                span=source_span(c)
                if c['kind']=='fragment' and c['role'] in FIELDS[:5] and span and span[0]<end and start<span[1]:
                    remaining=[(span[0],min(start,span[1])),(max(end,span[0]),span[1])]
                    for j,(a,b) in enumerate(remaining):
                        if a<b:result.append(dict(c,id=c['id'] if not j else identity(c['id']+'/remaining'),span=[a,b],text=doc['units'][uid]['text'][a:b]))
                    changed=True
                elif c['kind']=='reference' and c['role']=='conditions' and span and start<=span[0]<span[1]<=end and c['target_id'] in doc['units'] and not legacy(doc,c['target_id'])['children']:
                    changed=True
                else:
                    trivial=c['kind']=='group' and not c.get('span') and len(c.get('children',[]))==1 and c.get('quantity')==1 and c['children'][0]['kind']=='fragment'
                    clear(c)
                    if not (trivial and not c['children']):result.append(c)
                    else:changed=True
            n['children']=result
            if changed and n['kind']=='group':refresh(n)
        clear(tree)
    elif op=='degroup-range':
        start,end=r.get('start'),r.get('end')
        candidates=[(n,p) for n,p in walk(tree) if p is not None and n['kind'] in ('group','clause') and n.get('span')==[start,end]]
        if not candidates:raise ValueError('Select the complete original range of the Group to degroup it.')
        node,container=candidates[-1]
        if node['kind']=='clause':
            outer=next((p for n,p in walk(tree) if n is container),None)
            if not outer or outer['kind']!='clause' or not all_items(container):raise ValueError('Resolve the surrounding alternative quantity before degrouping this clause.')
            for field in node['children']:
                existing=next((c for c in outer['children'] if c.get('role')==field['role']),None)
                if existing:
                    if not all_items(existing) or not all_items(field):raise ValueError('Degroup would change an existing field quantity or NOT. Resolve it first.')
                    existing['children'].extend(field['children']);refresh(existing)
                else:outer['children'].append(field)
            container['children'].remove(node)
            if container['children']:refresh(container)
            else:outer['children'].remove(container)
        elif container['kind']=='group' and all_items(node) and all_items(container):
            index=container['children'].index(node);container['children'][index:index+1]=node['children'];refresh(container)
            outer=next((p for n,p in walk(tree) if n is container),None)
            if not container['children'] and not container.get('span') and outer and outer['kind']=='clause':outer['children'].remove(container)
        else:raise ValueError('Degroup would lose a quantity or NOT. Resolve it first.')
    elif op in ('add', 'add-group', 'add-exception'):
        start, end = r.get('start'), r.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(doc['units'][uid]['text']):
            raise ValueError('Select source wording before adding a field or Group.')
        if not doc['units'][uid]['text'][start:end].strip():raise ValueError('Select nonempty source wording.')
        role = r.get('field')
        if op in ('add-group','add-exception'):
            role = 'exceptions' if op=='add-exception' else ('conditions' if doc['roles'].get(uid)=='condition' else 'requirements') if target['kind'] == 'clause' else target.get('role')
            child = (dict(id=identity('clause'), kind='clause', span=[start, end], children=[]) if role in ('requirements','exceptions')
                     else group(identity('group'), role, span=[start, end]))
        else:
            if role not in FIELDS:
                raise ValueError('Choose a source field.')
            child = dict(id=identity('fragment'), kind='fragment', role=role, span=[start, end], text=doc['units'][uid]['text'][start:end])
        if op=='add-group':
            def selected_children(holder):
                chosen=[]
                for c in holder['children']:
                    span=source_span(c)
                    if span and span[0]<end and start<span[1]:
                        if not start<=span[0]<span[1]<=end:raise ValueError('A Group boundary cuts an existing mark. Clear or adjust that mark first.')
                        chosen.append(c)
                if chosen and len(chosen)!=len(holder['children']) and not all_items(holder):raise ValueError('Grouping only part of this combination would change its quantity or NOT.')
                return chosen
            if target['kind']=='clause':
                for holder in list(target['children']):
                    if holder['role']=='requirements':continue
                    chosen=selected_children(holder)
                    if not chosen:continue
                    if len(chosen)==len(holder['children']):target['children'].remove(holder);child['children'].append(holder)
                    else:
                        child['children'].append(group(identity(holder['id']+'/moved'),holder['role'],chosen,len(chosen)))
                        holder['children']=[c for c in holder['children'] if c not in chosen];refresh(holder)
            elif target['kind']=='group':
                chosen=selected_children(target);child['children']=chosen;child['quantity']=len(chosen) if chosen else None
                target['children']=[c for c in target['children'] if c not in chosen]
        dest = field_group(role); dest['children'].append(child); refresh(dest)
    elif op == 'link':
        role = r.get('field','subrequirement') if target['kind'] == 'clause' else target.get('role')
        if role not in ('subrequirement', 'requirements', 'exceptions'):
            raise ValueError('Link complete Requirements in a requirement group.')
        dest = field_group(role)
        if any(c.get('target_id') == r.get('target_id') for c in dest['children']):
            raise ValueError('This Requirement is already in the group.')
        dest['children'].append(dict(id=identity('reference'), kind='reference', role=role, target_id=r.get('target_id'))); refresh(dest)
    elif op in ('quantity', 'not'):
        if target['kind'] != 'group':
            raise ValueError('QC and NOT apply to a combination, not to mixed fields.')
        if op=='not' and target['role']!='conditions':
            raise ValueError('NOT is available only for Conditions.')
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
            if target['kind'] != 'group' or parent['kind'] != 'group' or not all_items(target):
                raise ValueError('Only an All group without NOT can be expanded. Other groups would lose their meaning.')
            if parent['quantity'] != len(parent['children']) or parent['negated']:
                raise ValueError('Expand only inside an All group without NOT.')
        index = parent['children'].index(target)
        parent['children'][index:index+1] = target['children'] if op == 'ungroup' else []
        if parent['kind'] == 'group': refresh(parent)
        if op=='ungroup' and not parent.get('children') and not parent.get('span'):
            outer=next((p for n,p in walk(tree) if n is parent),None)
            if outer and outer['kind']=='clause':outer['children'].remove(parent)
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
    if op=='clear-range' and _clear_linked:
        offset=doc['spans'][uid][0]
        for child_uid in linked_before:
            a,b=doc['spans'][child_uid];left=max(a,offset+r['start']);right=min(b,offset+r['end'])
            if left<right:
                edit(doc,dict(r,unit_id=child_uid,node_id=legacy(doc,child_uid)['id'],start=left-a,end=right-a),_clear_linked=False)
