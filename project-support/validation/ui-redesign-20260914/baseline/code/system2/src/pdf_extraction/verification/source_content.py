"""Reconstruct v2 field ownership and structural references directly from Canonical.

This verifier does not import or execute the mapper. Raw-source fidelity is checked
separately before projection, using the version-bound source verification report.
"""
from collections import defaultdict

from ..contracts.html import HtmlDocument, HTML_PROFILES
from ..contracts.source_content import ASC_FIELDS, CONTENT_KINDS


def extend_expectations(document, refs, inventory, expected, profile, extra):
    if not isinstance(document, HtmlDocument) or document.profile not in HTML_PROFILES:
        return profile, extra, {}, {anchor: [] for anchor in expected}
    nodes = {n.id: n for n in document.nodes}
    ordinal = {n.id: i for i, n in enumerate(document.nodes)}
    ancestors = {}
    for n in document.nodes:
        chain = [n.id]
        while nodes[chain[-1]].parent_id is not None:
            chain.append(nodes[chain[-1]].parent_id)
        ancestors[n.id] = chain
    blocked = {nid for nid, chain in ancestors.items() if any(
        nodes[p].role in ('navigation', 'control', 'metadata')
        or 'share-paragraf' in nodes[p].attributes.get('class', []) for p in chain)}
    groups = {}; roots = {anchor: anchor for anchor in expected}
    if document.profile != 'lovdata':
        profile = 'asc_content' if document.profile == 'asc' else 'html_content'
        extra = []
    if document.profile == 'asc':
        rows = [n for n in document.nodes if 'indicator-row' in n.attributes.get('class', []) and n.id not in blocked]
        nearest_row = {nid: next((p for p in chain if 'indicator-row' in nodes[p].attributes.get('class', [])), None)
                       for nid, chain in ancestors.items()}
        atoms_by_row = defaultdict(list); fields_by_row = defaultdict(lambda: defaultdict(list))
        for i, atom in enumerate(document.atoms):
            if atom.node_id not in blocked:
                atoms_by_row[nearest_row[atom.node_id]].append(i)
        for n in document.nodes:
            for css, key in ASC_FIELDS.items():
                if css in n.attributes.get('class', []): fields_by_row[nearest_row[n.id]][key].append(n.id)
        for row in rows:
            field_groups = {}; issues = []
            appendix = 'table-row' in row.attributes.get('class', [])
            appendix_targets = {}
            if appendix:
                cells = [n.id for n in document.nodes if n.parent_id == row.id and 'table-cell' in n.attributes.get('class', [])]
                appendix_targets['identifier'] = [nid for nid in cells if 'indicator' in nodes[nid].attributes.get('class', [])]
                appendix_targets['body'] = [nid for nid in cells if 'indicator' not in nodes[nid].attributes.get('class', [])]
                paragraphs = [n.id for n in document.nodes if n.parent_id in appendix_targets['body'] and n.kind == 'paragraph']
                appendix_targets['applicability'] = [nid for nid in paragraphs if ''.join(
                    a.text for a in document.atoms if nid in ancestors[a.node_id]).strip().startswith('Indicator applicability:')]
            for key in ASC_FIELDS.values():
                targets = appendix_targets.get(key, []) if appendix else fields_by_row[row.id][key]; values = []
                for target in targets:
                    pointers = []
                    for i in atoms_by_row[row.id]:
                        chain = ancestors[document.atoms[i].node_id]
                        if target not in chain: continue
                        if key == 'body' and any(nodes[nid].kind == 'footnote' for nid in chain[:chain.index(target)]): continue
                        if appendix and key == 'body' and set(chain) & set(appendix_targets['applicability']): continue
                        pointers.append(f'/atoms/{i}/text')
                    values.append(pointers)
                field_groups[key] = values or [[]]
                if appendix and key == 'applicability' and not targets: issues.append('source_field_not_separately_stated:applicability')
                elif len(targets) != 1: issues.append('missing_or_ambiguous_field:' + key)
                elif not ''.join(refs[p][0] for p in values[0]).strip(): issues.append('missing_or_empty_field:' + key)
            if 'indicator-row--not-in-use' in row.attributes.get('class', []): issues.append('source_marked_not_in_use')
            fields = {key: [p for value in values for p in value] for key, values in field_groups.items()}
            expected[row.id] = ('standard_indicator', row.locator, fields, issues)
            roots[row.id] = row.id; groups[row.id] = field_groups

    used = {p for _, _, fields, _ in expected.values() for values in fields.values() for p in values}
    remaining = defaultdict(list)
    for i, atom in enumerate(document.atoms):
        if atom.node_id in blocked or f'/atoms/{i}/text' in used: continue
        chain = ancestors[atom.node_id]
        candidates = [(0 if nodes[nid].kind == 'footnote' else 1 if nodes[nid].kind == 'table_cell' else 2, depth, nid)
                      for depth, nid in enumerate(chain) if nodes[nid].kind in CONTENT_KINDS]
        owner = min(candidates)[2] if candidates else atom.node_id
        remaining[owner].append(i)
    for nid, indices in remaining.items():
        if not ''.join(document.atoms[i].text for i in indices).strip(): continue
        kind = CONTENT_KINDS.get(nodes[nid].kind, 'source_text')
        field = 'title' if kind == 'source_heading' else 'notes' if kind == 'source_note' else 'body'
        runs = []
        previous = None
        for i in indices:
            if previous is None or i != previous + 1: runs.append([])
            runs[-1].append(f'/atoms/{i}/text'); previous = i
        anchor = nid + ':content'
        expected[anchor] = (kind, nodes[nid].locator, {field: [p for run in runs for p in run]}, [])
        roots[anchor] = nid; groups[anchor] = {field: runs}

    def structure(anchor):
        involved = set(ancestors[roots[anchor]])
        for values in expected[anchor][2].values():
            for ptr in values:
                involved.update(ancestors[document.atoms[int(ptr.split('/')[2])].node_id])
        result = [{'pointer': f'/nodes/{ordinal[nid]}', 'locator': nodes[nid].locator}
                  for nid in sorted(involved, key=ordinal.get)]
        for name, collection in [('tables', document.tables), ('lists', document.lists), ('links', document.links)]:
            for i, item in enumerate(collection):
                if item.node_id not in involved: continue
                result.append({'pointer': f'/{name}/{i}', 'locator': nodes[item.node_id].locator})
                if name == 'tables':
                    for j, cell in enumerate(item.cells):
                        if cell.node_id in involved:
                            result.append({'pointer': f'/tables/{i}/cells/{j}', 'locator': nodes[cell.node_id].locator})
        return result

    structures = {anchor: structure(anchor) for anchor in expected}
    linked = {p['pointer'] for values in structures.values() for p in values if p['pointer'].startswith('/links/')}
    for n in document.nodes:
        if n.kind != 'image' or n.id in blocked: continue
        anchor = n.id + ':image'; roots[anchor] = n.id
        expected[anchor] = ('source_image', n.locator, {}, ['image_content_not_transcribed'])
        groups[anchor] = {}; structures[anchor] = structure(anchor)
        linked.update(p['pointer'] for p in structures[anchor] if p['pointer'].startswith('/links/'))
    for i, link in enumerate(document.links):
        if link.node_id in blocked or f'/links/{i}' in linked: continue
        anchor = link.node_id + f':link:{i}'; roots[anchor] = link.node_id
        expected[anchor] = ('source_link', nodes[link.node_id].locator, {}, [])
        groups[anchor] = {}; structures[anchor] = structure(anchor)
    ordered = sorted(expected, key=lambda anchor: (ordinal[roots[anchor]], anchor))
    contents = {anchor: expected[anchor] for anchor in ordered}
    expected.clear(); expected.update(contents)
    if not expected: extra = list(dict.fromkeys([*extra, 'no_source_records']))
    return profile, extra, groups, structures
