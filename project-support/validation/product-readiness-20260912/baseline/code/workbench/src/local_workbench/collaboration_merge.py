"""Deterministic three-way offline merge previews; no persistence or decisions by time.

Paths address normalized identity maps for blocks/issues, so `/blocks/a/text`
remains stable when ordinary blocks are inserted. Unresolved differences retain
current values. A preview is not permission to apply it or confirm a review.
"""
from copy import deepcopy
from hashlib import sha256
import json

_MISSING = object()


def _copy(value):
    return _MISSING if value is _MISSING else deepcopy(value)


def _equal(left, right):
    if left is _MISSING or right is _MISSING:
        return left is right
    if type(left) is not type(right): return False
    if isinstance(left,dict):
        return left.keys()==right.keys() and all(_equal(left[key],right[key]) for key in left)
    if isinstance(left,list):
        return len(left)==len(right) and all(_equal(a,b) for a,b in zip(left,right))
    return left == right


def _token(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def _json_clone(value):
    try:
        def pairs(items):
            result={}
            for key,item in items:
                if key in result: raise ValueError('duplicate_json_key')
                result[key]=item
            return result
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False),object_pairs_hook=pairs)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError('collaboration_document_must_be_finite_json') from exc


def _identities(items):
    if not isinstance(items, list):
        raise ValueError('collaboration_identity_list_required')
    identifiers = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
            raise ValueError('collaboration_item_identity_required')
        identifiers.append(item['id'])
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('collaboration_duplicate_item_identity')
    return identifiers


def _table_shape(table):
    if not isinstance(table, dict) or not isinstance(table.get('rows'), list):
        return None
    rows = table['rows']
    if any(not isinstance(row, list) for row in rows):
        return None
    return ([len(row) for row in rows], table.get('merges', []))


def merge_documents(base, current, incoming, decisions=None):
    """Return merged JSON, differences, and unresolved difference IDs.

    Each explicit decision is `{action: current|incoming|edit, value?: JSON}`.
    JSON null is a value; presence flags distinguish it from a removed property.
    Identity-list reordering and unknown split/merge patterns need whole-list
    review. Structural table changes need whole-table review, even on one side.
    """
    documents = [_json_clone(value) for value in (base, current, incoming)]
    if any(not isinstance(value, dict) for value in documents):
        raise ValueError('collaboration_document_object_required')
    decisions = _json_clone({} if decisions is None else decisions)
    if not isinstance(decisions, dict):
        raise ValueError('collaboration_decisions_object_required')
    differences = []
    used = set()

    def difference(before, ours, theirs, path, *, kind='value', force=False):
        if _equal(before, ours) and _equal(ours, theirs):
            return _copy(ours)
        conflict = force or (not _equal(ours, theirs) and not _equal(before, ours) and not _equal(before, theirs))
        if _equal(ours, theirs):
            chosen, resolution, conflict = ours, 'same', False
        elif conflict:
            chosen, resolution = ours, None
        elif _equal(before, ours):
            chosen, resolution = theirs, 'auto_incoming'
        else:
            chosen, resolution = ours, 'auto_current'
        identity = sha256(path.encode()).hexdigest()[:24]
        if identity in decisions:
            decision = decisions[identity]
            if not isinstance(decision, dict) or decision.get('action') not in {'current', 'incoming', 'edit'}:
                raise ValueError('collaboration_invalid_decision')
            action = decision['action']
            if set(decision) - {'action', 'value'} or (action == 'edit' and 'value' not in decision):
                raise ValueError('collaboration_invalid_decision')
            chosen = ours if action == 'current' else theirs if action == 'incoming' else decision['value']
            resolution = action
            used.add(identity)
        entry = dict(id=identity, path=path or '', label=path or 'Document', kind=kind,
                     base=None if before is _MISSING else _copy(before),
                     current=None if ours is _MISSING else _copy(ours),
                     incoming=None if theirs is _MISSING else _copy(theirs),
                     presence=dict(base=before is not _MISSING,current=ours is not _MISSING,incoming=theirs is not _MISSING),
                     conflict=conflict, resolution=resolution)
        differences.append(entry)
        return _copy(chosen)

    def identity_list(before, ours, theirs, path):
        ids = [_identities(value) for value in (before, ours, theirs)]
        base_ids, our_ids, their_ids = ids
        base_set = set(base_ids)
        structural = False
        for branch in (our_ids, their_ids):
            present = set(branch)
            structural |= [i for i in branch if i in base_set] != [i for i in base_ids if i in present]
            structural |= bool(base_set - present) and bool(present - base_set)
        # Simultaneous independent insertions into the same original gap have an
        # unknown relative order. Do not invent their intended reading sequence.
        def insertions(branch):
            result = {}; previous = None
            for identity in branch:
                if identity in base_set: previous = identity
                else: result.setdefault(previous, []).append(identity)
            return result
        ours_added, theirs_added = insertions(our_ids), insertions(their_ids)
        structural |= any(ours_added[gap] != theirs_added[gap] for gap in ours_added.keys() & theirs_added.keys())
        if structural:
            chosen = difference(before, ours, theirs, path, kind='structure', force=not _equal(before,theirs))
            _identities(chosen)
            return chosen
        maps = [{item['id']: item for item in branch} for branch in (before, ours, theirs)]
        values = {}
        for identity in dict.fromkeys(base_ids + our_ids + their_ids):
            value = walk(*(mapping.get(identity, _MISSING) for mapping in maps), path+'/'+_token(identity), identity=identity)
            if value is not _MISSING:
                if not isinstance(value, dict) or value.get('id') != identity:
                    raise ValueError('collaboration_item_identity_cannot_change')
                values[identity] = value
        order = [identity for identity in our_ids if identity in values]
        for position, identity in enumerate(their_ids):
            if identity not in values or identity in order: continue
            previous = next((i for i in reversed(their_ids[:position]) if i in order), None)
            following = next((i for i in their_ids[position+1:] if i in order), None)
            if previous is not None: order.insert(order.index(previous)+1, identity)
            elif following is not None: order.insert(order.index(following), identity)
            else: order.append(identity)
        order += [identity for identity in base_ids if identity in values and identity not in order]
        return [values[identity] for identity in order]

    def walk(before, ours, theirs, path, identity=None):
        if _equal(before, ours) and _equal(ours, theirs):
            return _copy(ours)
        if path in {'/blocks', '/issues'} and all(isinstance(v, list) for v in (before, ours, theirs)):
            return identity_list(before, ours, theirs, path)
        if identity is not None and all(isinstance(v, dict) for v in (before, ours, theirs)):
            if any(v.get('type') != before.get('type') for v in (ours, theirs)):
                return difference(before, ours, theirs, path, kind='structure', force=not _equal(before,theirs))
        if path.startswith('/blocks/') and path.count('/')==3 and path.endswith('/table') and all(isinstance(v, dict) for v in (before, ours, theirs)):
            shapes = [_table_shape(value) for value in (before, ours, theirs)]
            if shapes[0] is None or any(shape != shapes[0] for shape in shapes[1:]):
                return difference(before, ours, theirs, path, kind='table_structure', force=not _equal(before,theirs))
        if all(isinstance(value, dict) for value in (before, ours, theirs)):
            result = {}
            for key in dict.fromkeys([*before, *ours, *theirs]):
                value = walk(before.get(key,_MISSING), ours.get(key,_MISSING), theirs.get(key,_MISSING), path+'/'+_token(key))
                if value is not _MISSING: result[key] = value
            return result
        if path.startswith('/blocks/') and path.count('/')==4 and path.endswith('/table/rows') and all(isinstance(value,list) for value in (before,ours,theirs)):
            if [len(row) for row in before] == [len(row) for row in ours] == [len(row) for row in theirs]:
                return [[walk(before[r][c],ours[r][c],theirs[r][c],path+f'/{r}/{c}') for c in range(len(row))] for r,row in enumerate(before)]
        kind = 'addition' if before is _MISSING else 'deletion' if ours is _MISSING or theirs is _MISSING else 'value'
        return difference(before,ours,theirs,path,kind=kind)

    result = walk(*documents, '')
    if set(decisions) != used:
        raise ValueError('collaboration_unknown_difference_decision')
    for key in ('blocks','issues'):
        if key in result: _identities(result[key])
    return {'merged':result,'differences':differences,
            'unresolved':[item['id'] for item in differences if item['conflict'] and item['resolution'] is None]}
