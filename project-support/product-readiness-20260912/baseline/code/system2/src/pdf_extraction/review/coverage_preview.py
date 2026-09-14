"""Resolve generic PDF range previews from verified Canonical page inventories.

This is a display projection only. It never changes original facts, dependencies
or acceptance, and includes inventoried pages even when no unit was extracted.
"""
from hashlib import sha256
import json
from pathlib import Path


def references(store, doc, unit, original_refs):
    if doc['source'].get('file_format') != 'pdf' or unit['kind'] != 'coverage':
        return original_refs
    result = []
    for ref in original_refs:
        if ref.get('locator') != 'whole parsed range' or 'page_index' in ref:
            result.append(ref)
            continue
        match = next((c for c in doc.get('canonical', [])
                      if c['sha256'] == ref.get('canonical_sha256')), None)
        if not match:
            result.append(ref)
            continue
        path = Path(match['path']).resolve()
        if not path.is_relative_to(store.root) or not path.is_file():
            result.append(ref)
            continue
        try:
            raw = path.read_bytes()
            canonical = json.loads(raw)
        except (OSError, ValueError):
            result.append(ref)
            continue
        if sha256(raw).hexdigest() != match['sha256']:
            result.append(ref)
            continue
        pages = canonical.get('pages', []) if isinstance(canonical, dict) else []
        indices = sorted({p['page_index'] for p in pages if isinstance(p, dict)
                          and type(p.get('page_index')) is int and p['page_index'] >= 0})
        result.extend([dict(ref, page_index=p) for p in indices] or [ref])
    return result
