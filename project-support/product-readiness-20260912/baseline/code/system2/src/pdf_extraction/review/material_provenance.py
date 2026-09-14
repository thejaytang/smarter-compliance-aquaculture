"""Attribution on real writes; specific paths override unchanged ancestor evidence."""
from copy import deepcopy


def _part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def pointer(identity):
    return '/blocks/' + _part(identity)


def _under(path, parent):
    return path == parent or path.startswith(parent + '/')


def _shape_changed(old, new):
    keys = ('type', 'parent_id', 'level', 'dependencies', 'source_refs', 'numbering')
    if any(old.get(k) != new.get(k) for k in keys):
        return True
    if old.get('image', {}).get('source_ref') != new.get('image', {}).get('source_ref'):
        return True
    if new['type'] == 'table':
        before, after = old.get('table', {}), new.get('table', {})
        left, right = before.get('rows', []), after.get('rows', [])
        return (len(left) != len(right) or [len(r) for r in left] != [len(r) for r in right]
                or before.get('merges', []) != after.get('merges', []))
    return False


def _changed_paths(old, new, path):
    """Opaque list order is one field; rectangular table cells have stable slots."""
    if old == new:
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(old.keys() | new.keys()):
            child = path + '/' + _part(key)
            if key not in old or key not in new:
                result.append(child)
            elif key == 'rows' and path.endswith('/table'):
                result.extend(child + '/' + str(r) + '/' + str(c)
                              for r, row in enumerate(new[key]) for c, cell in enumerate(row)
                              if old[key][r][c] != cell)
            else:
                result.extend(_changed_paths(old[key], new[key], child))
        return result
    return [path]


def record_changes(previous, material, kind, actor, at):
    old = {b['id']: b for b in (previous or {}).get('blocks', [])}
    records = deepcopy(material.get('collaboration_provenance', []))
    previous_records = (previous or {}).get('collaboration_provenance', [])
    has_supplied_choices = records != previous_records
    new_ids = {b['id'] for b in material['blocks']}
    for deleted in old.keys() - new_ids:
        records = [r for r in records if not _under(str(r.get('path', '')), pointer(deleted))]
    for block in material['blocks']:
        path = pointer(block['id'])
        supplied = [r for r in records if _under(str(r.get('path', '')), path)]
        # Explicit per-choice evidence has its own authors. Mark only the newly
        # selected entries, preserving earlier adopter/revision/actor records.
        explicit = (kind == 'collaboration_adopted' or
                    (kind == 'candidate_merge' and has_supplied_choices)) and supplied
        if explicit:
            for entry in supplied:
                if entry.get('status') == 'pending_adoption':
                    entry['status'] = 'machine_unreviewed' if entry.get('origin') == 'machine' else 'human_unreviewed'
                    entry['adopter'] = actor
                    entry['adopted_revision'] = material['revision']
            continue
        prior = old.get(block['id'])
        if prior == block:
            continue
        structural = prior is not None and _shape_changed(prior, block)
        changed = [path] if prior is None or structural or kind == 'candidate_adopt' else _changed_paths(prior, block, path)
        machine = kind in ('candidate_adopt', 'candidate_draft')
        human_actor = actor if actor not in (None, '', 'machine', 'system', 'source_intake', 'local_parser', 'system_reuse') else None
        for changed_path in changed:
            # Preserve ancestor/base evidence for untouched fields. Remove only
            # evidence overridden by this particular field/cell or whole block.
            records = [r for r in records if not _under(str(r.get('path', '')), changed_path)]
            record = {'path': changed_path, 'origin': 'machine' if machine else ('human' if human_actor else 'unknown'),
                'actor': None if machine else human_actor, 'selected_by': actor if machine else None,
                'candidate_id': material.get('last_candidate_id') if machine else None,
                'content_revision': material['content_revision'], 'at': at,
                'source_hash': material['source']['content_hash'],
                'source_refs': deepcopy(block.get('source_refs', [])),
                'status': 'machine_unreviewed' if machine else 'human_unreviewed'}
            if structural:
                record.update(scope_review_required=True, attribution_scope='whole_block',
                              reason='Structure or original association changed; finer correspondence is not assumed.')
            records.append(record)
    material['collaboration_provenance'] = records
    material['provenance_version'] = 1
