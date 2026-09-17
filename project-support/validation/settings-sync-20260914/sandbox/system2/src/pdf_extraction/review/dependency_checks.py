"""Read-only prerequisite explanations using the already loaded dependency graph."""
from collections import deque

from ..verification.acceptance import accepted
from . import task_model


def pending(unit, related):
    queue = deque((uid, 1) for uid in unit.get('dependencies', []))
    seen, result = set(), []
    while queue:
        uid, depth = queue.popleft()
        if uid in seen:
            continue
        seen.add(uid)
        target = related.get(uid)
        if uid == unit['id'] or target is None:
            result.append(dict(unit_id=uid, depth=depth, available=target is not None,
                title='Cyclic dependency' if target else 'Missing source dependency',
                status='blocked', scope=[],
                reason='The source dependency graph needs repair before this item can proceed.'))
            continue
        queue.extend((child, depth + 1) for child in target.get('dependencies', []))
        if accepted(target.get('content_status')):
            continue
        fields = {**target.get('original', {}).get('fields', {}), **target.get('edits', {})}
        description = task_model.describe(target, related)
        refs = target.get('reviewed_references', target.get('original', {}).get('references', []))
        scope = list(dict.fromkeys(
            'Original page ' + str(ref['page_index'] + 1) if type(ref.get('page_index')) is int
            else ref.get('locator', '') for ref in refs))
        result.append(dict(unit_id=uid, depth=depth, available=True,
            title=fields.get('identifier') or fields.get('title') or description['title'],
            kind=target.get('kind'), status=target.get('content_status', 'pending'),
            scope=[s for s in scope if s], reason=description['reason']))
    # An accepted ancestor can itself belong to a dependency cycle. The review
    # gate still blocks it; expose that cause even when no node is Pending.
    active, done, stack = set(), set(), [(unit['id'], False)]
    while stack:
        uid, exiting = stack.pop()
        if exiting:
            active.discard(uid)
            done.add(uid)
            continue
        if uid in active:
            if not any(item['unit_id'] == uid for item in result):
                result.append(dict(unit_id=uid, depth=0, available=True,
                    title='Cyclic dependency', status='blocked', scope=[],
                    reason='The source dependency graph needs repair before this item can proceed.'))
            continue
        if uid in done or uid not in related:
            continue
        active.add(uid)
        stack.append((uid, True))
        stack.extend((child, False) for child in reversed(related[uid].get('dependencies', [])))
    return result
