"""Display-only side-specific relationships and narrow preview decision guards."""
from copy import deepcopy


def relationship_path(path):
    parts = [p.replace('~1', '/').replace('~0', '~') for p in str(path).split('/')[1:]]
    if len(parts) == 3 and parts[0] == 'blocks' and parts[2] in ('parent_id', 'dependencies'):
        return parts[1], parts[2]
    return None


def _references(value, kind=None):
    if kind == 'parent_id':
        return {value} if isinstance(value, str) and value else set()
    if kind == 'dependencies':
        return {v for v in value if isinstance(v, str) and v} if isinstance(value, list) else set()
    result = set()
    if isinstance(value, list):
        for item in value:
            result.update(_references(item))
    elif isinstance(value, dict):
        for key in ('parent_id', 'dependencies'):
            result.update(_references(value.get(key), key))
    return result


def display_context(base, current, incoming, differences):
    """Never use merged text to name historical or incoming references."""
    references = set()
    for diff in differences:
        if diff.get('kind') == 'order' and diff['path'] == '/blocks':
            for side in ('base', 'current', 'incoming'):
                references.update(diff[side])
            continue
        path = relationship_path(diff['path'])
        if path or diff['path'] == '/blocks' or diff['path'].startswith('/blocks/') and diff['path'].count('/') == 2:
            for side in ('base', 'current', 'incoming'):
                references.update(_references(diff[side], path[1] if path else None))
    context = {}
    for side, document in (('base', base), ('current', current), ('incoming', incoming)):
        context[side] = {
            b['id']: {key: deepcopy(b[key]) for key in ('id', 'type', 'numbering', 'text', 'source_refs') if key in b}
            for b in document.get('blocks', []) if b['id'] in references
        }
        for item in context[side].values():
            # Labels are navigational summaries; exact original values stay in the diff.
            item['text'] = ' '.join(str(item.get('text') or '').split())[:160]
    return context


def validate_decisions(differences, decisions, blocks):
    """Reject unavailable relation targets before recording explicit choices.

    Unresolved candidates remain reviewable. Other field/structure editing keeps
    its existing validation path; the owning material store still validates all
    structure before application.
    """
    by_id = {b['id']: b for b in blocks}
    positions = {b['id']: i for i, b in enumerate(blocks)}
    if any(d.get('kind') == 'order' and d['id'] in decisions for d in differences):
        for block in blocks:
            parent = block.get('parent_id')
            if not parent:
                continue
            target = by_id.get(parent)
            if (not target or target.get('type') != 'heading'
                    or positions[parent] >= positions[block['id']]
                    or block.get('type') == 'heading' and target.get('level', 6) >= block.get('level', 1)):
                raise ValueError('This order places content outside its heading. Keep the heading before its content, or correct the heading relationship first.')
    for diff in differences:
        path = relationship_path(diff['path'])
        if not path or diff['id'] not in decisions:
            continue
        identity, kind = path
        block = by_id.get(identity)
        if block is None:
            # A later explicit whole-block deletion makes this relation moot.
            continue
        value = block.get(kind)
        if kind == 'parent_id':
            if value is None or value == '':
                continue
            target = by_id.get(value) if isinstance(value, str) else None
            if not target or target.get('type') != 'heading':
                raise ValueError('The selected heading is not in the combined content. Resolve its addition or removal first, or choose another heading.')
            if positions[value] >= positions[identity]:
                raise ValueError('Choose a heading that appears before this content in the combined version.')
            if block.get('type') == 'heading' and target.get('level', 6) >= block.get('level', 1):
                raise ValueError('Choose a heading with a higher hierarchy level than this heading.')
        else:
            value = block.get('dependencies', [])
            if not isinstance(value, list) or any(not isinstance(v, str) or v not in by_id or v == identity for v in value):
                raise ValueError('Some related content is no longer available in the combined version. Choose available content before saving this decision.')
            # Only a cycle through this changed block invalidates this decision.
            pending = list(value); visited = set()
            while pending:
                target = pending.pop()
                if target == identity:
                    raise ValueError('These related-content choices create a circular relationship. Remove the link that leads back to this content.')
                if target in visited:
                    continue
                visited.add(target)
                other = by_id.get(target)
                if other:
                    pending.extend(v for v in other.get('dependencies', []) if isinstance(v, str))
