"""Conservative, server-owned review invalidation for immutable material ranges."""
from collections import defaultdict


def review_impact(material, blocks, issues):
    scopes = {s['id'] for s in material['scope']}
    old = {b['id']: b for b in material['blocks']}
    new = {b['id']: b for b in blocks}
    changed = {i for i in old.keys() | new.keys() if old.get(i) != new.get(i)}
    common = old.keys() & new.keys()
    before = [b['id'] for b in material['blocks'] if b['id'] in common]
    after = [b['id'] for b in blocks if b['id'] in common]
    moved = {a for a, b in zip(before, after) if a != b} | {b for a, b in zip(before, after) if a != b}
    changed |= moved
    shape = ('type', 'level', 'parent_id', 'numbering', 'dependencies', 'source_refs')
    structural = bool(moved or old.keys() != new.keys()) or any(
        any(old[i].get(k) != new[i].get(k) for k in shape)
        or (new[i]['type'] == 'heading' and old[i] != new[i]) for i in common)
    reason = None
    if material.get('source_stale'):
        reason = 'source_version_changed'
    elif issues != material['issues']:
        reason = 'material_issue_changed'
    elif any(s not in material.get('review_checks', {}) for s in material.get('checked_scope', [])):
        reason = 'historical_check_provenance_unavailable'
    links = defaultdict(set)
    for item in list(old.values()) + list(new.values()):
        dependencies = list(item.get('dependencies', []))
        if structural and item.get('parent_id'):
            dependencies.append(item['parent_id'])
        for other in dependencies:
            links[item['id']].add(other)
            links[other].add(item['id'])
    affected = set(changed)
    pending = list(changed)
    while pending:
        for other in links[pending.pop()]:
            if other not in affected:
                affected.add(other)
                pending.append(other)
    invalid = set()
    for identity in affected:
        for body in (old, new):
            block = body.get(identity)
            if block is None:
                continue
            refs = block.get('source_refs', [])
            image_ref = block.get('image', {}).get('source_ref')
            if image_ref:
                refs = refs + [image_ref]
            if not refs or any(ref.get('scope_id') not in scopes for ref in refs):
                reason = reason or 'unknown_original_association'
            invalid.update(ref['scope_id'] for ref in refs if ref.get('scope_id') in scopes)
    if reason:
        invalid = scopes
    retained = [s for s in material.get('checked_scope', []) if s not in invalid]
    return {'from_content_revision': material['content_revision'],
            'affected_scope': sorted(invalid), 'retained_scope': retained,
            'affected_blocks': sorted(affected), 'structural': structural,
            'full_review_required': bool(reason),
            'reason': reason or ('structure_or_dependency_changed' if structural else 'linked_content_changed')}


def stamp_checks(material, checked, actor, at):
    """Record an explicit saved check; never synthesize a historical decision."""
    previous = material.get('review_checks', {})
    return {scope: previous.get(scope) or {'actor': actor, 'at': at,
            'content_revision': material['content_revision'],
            'source_hash': material['source']['content_hash']} for scope in checked}
