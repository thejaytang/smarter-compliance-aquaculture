"""Literal HTML fields and remaining content, bound to the original DOM graph."""
from collections import Counter, defaultdict

from ...contracts.html import HtmlDocument, HTML_PROFILES
from ...contracts.source_content import ASC_FIELDS, CONTENT_KINDS, ContentRecord, ContentRecords
from ...contracts.source_records import TextReference
from .source_records import map_source_records, record_id, _field


class HtmlIndex:
    def __init__(self, document):
        self.document = document
        self.nodes = {n.id: n for n in document.nodes}
        self.positions = {n.id: i for i, n in enumerate(document.nodes)}
        self.chains = {}
        self.descendant_atoms = defaultdict(list)
        for n in document.nodes:
            self.chains[n.id] = [n, *self.chains.get(n.parent_id, [])]
        for i, atom in enumerate(document.atoms):
            for n in self.chains[atom.node_id]:
                self.descendant_atoms[n.id].append(i)

    def blocked(self, nid):
        return any(n.role != 'content' or 'share-paragraf' in n.attributes.get('class', [])
                   for n in self.chains[nid])

    def field(self, indices):
        return _field(''.join(self.document.atoms[i].text for i in indices), [
            TextReference(pointer=f'/atoms/{i}/text',
                          locator=self.nodes[self.document.atoms[i].node_id].locator
                          + f'::text({self.document.atoms[i].text_index})') for i in indices])

    def structure(self, record):
        ids = {n.id for n in self.chains[record.source_anchor]}
        for values in record.fields.values():
            for field in values:
                for ref in field.references:
                    atom = self.document.atoms[int(ref.pointer.split('/')[2])]
                    ids.update(n.id for n in self.chains[atom.node_id])
        refs = [TextReference(pointer=f'/nodes/{self.positions[nid]}', locator=self.nodes[nid].locator)
                for nid in sorted(ids, key=self.positions.get)]
        for collection in ('tables', 'lists', 'links'):
            for i, obj in enumerate(getattr(self.document, collection)):
                if obj.node_id in ids:
                    refs.append(TextReference(pointer=f'/{collection}/{i}', locator=self.nodes[obj.node_id].locator))
                    if collection == 'tables':
                        refs.extend(TextReference(pointer=f'/tables/{i}/cells/{j}', locator=self.nodes[c.node_id].locator)
                                    for j, c in enumerate(obj.cells) if c.node_id in ids)
        return refs


def map_content_records(document, canonical_sha256, verification_sha256):
    legacy = map_source_records(document, canonical_sha256, verification_sha256)
    records = [ContentRecord(**r.model_dump()) for r in legacy.records]
    result = legacy.model_dump(exclude={'schema_version', 'mapper_version', 'records'})
    if not isinstance(document, HtmlDocument) or document.profile not in HTML_PROFILES:
        return ContentRecords(**result, records=records)

    index = HtmlIndex(document)
    if document.profile != 'lovdata':
        result.update(profile='asc_content' if document.profile == 'asc' else 'html_content',
                      status='review_required', issues=list(document.issues))
    if document.profile == 'asc':
        records.extend(_asc_records(index))
    used = {ref.pointer for r in records for values in r.fields.values()
            for field in values for ref in field.references}
    groups = defaultdict(list)
    owners = {}
    for i, atom in enumerate(document.atoms):
        if f'/atoms/{i}/text' in used or index.blocked(atom.node_id):
            continue
        chain = index.chains[atom.node_id]
        # A cell remains a cell even when it contains paragraphs/lists. Footnotes
        # form separate blocks, so their text cannot silently become cell values.
        owner = next((n for n in chain if n.kind == 'footnote'), None)
        owner = owner or next((n for n in chain if n.kind == 'table_cell'), None)
        owner = owner or next((n for n in chain if n.kind in CONTENT_KINDS), chain[0])
        groups[owner.id].append(i)
        owners[owner.id] = owner
    for nid, indices in groups.items():
        if not any(document.atoms[i].text.strip() for i in indices):
            continue
        node = owners[nid]
        # Direct text can occur on an existing clause/indicator root. A distinct
        # anchor keeps its supplemental block separate from the original record.
        anchor = nid
        kind = CONTENT_KINDS.get(node.kind, 'source_text')
        key = 'title' if kind == 'source_heading' else 'notes' if kind == 'source_note' else 'body'
        runs = []
        for i in indices:
            if not runs or i != runs[-1][-1] + 1:
                runs.append([])
            runs[-1].append(i)
        records.append(ContentRecord(id=record_id(document.source.content_hash, anchor + ':content'),
            kind=kind, source_anchor=anchor + ':content', locator=node.locator,
            fields={key: [index.field(run) for run in runs]}))

    # Images and empty links have no text inventory, but are still source evidence.
    represented_links = set()
    for ri, record in enumerate(records):
        root = record.source_anchor.removesuffix(':content')
        structure = index.structure(record.model_copy(update={'source_anchor': root}))
        records[ri] = record.model_copy(update={'structure': structure})
        represented_links.update(r.pointer for r in structure if r.pointer.startswith('/links/'))
    for node in document.nodes:
        if node.kind != 'image' or index.blocked(node.id):
            continue
        r = ContentRecord(id=record_id(document.source.content_hash, node.id + ':image'), kind='source_image',
            source_anchor=node.id + ':image', locator=node.locator, fields={}, issues=['image_content_not_transcribed'])
        r = r.model_copy(update={'structure': index.structure(r.model_copy(update={'source_anchor': node.id}))})
        records.append(r)
        represented_links.update(p.pointer for p in r.structure if p.pointer.startswith('/links/'))
    for i, link in enumerate(document.links):
        if f'/links/{i}' in represented_links or index.blocked(link.node_id):
            continue
        node = index.nodes[link.node_id]
        r = ContentRecord(id=record_id(document.source.content_hash, node.id + f':link:{i}'), kind='source_link',
            source_anchor=node.id + f':link:{i}', locator=node.locator, fields={})
        r = r.model_copy(update={'structure': index.structure(r.model_copy(update={'source_anchor': node.id}))})
        records.append(r)

    # Source order, not all clauses followed by all annexes. Stable v1 IDs persist.
    records.sort(key=lambda r: (min(int(p.pointer.split('/')[2]) for p in r.structure
                                    if p.pointer.startswith('/nodes/') and p.locator == r.locator), r.source_anchor))
    counts = Counter((r.fields.get('identifier', [])[0].text or '').strip()
                     for r in records if r.fields.get('identifier'))
    for r in records:
        identity = (r.fields['identifier'][0].text or '').strip() if r.fields.get('identifier') else ''
        if identity and counts[identity] > 1 and 'duplicate_source_identifier' not in r.issues:
            r.issues.append('duplicate_source_identifier')
    used = {p.pointer for r in records for values in r.fields.values() for f in values for p in f.references}
    result['residual'] = [r.model_dump() for r in legacy.residual if r.reference.pointer not in used]
    result['mapped_reference_count'] = sum(1 for i, a in enumerate(document.atoms)
                                            if a.text.strip() and f'/atoms/{i}/text' in used)
    if not records:
        result['issues'] = list(dict.fromkeys([*result['issues'], 'no_source_records']))
    return ContentRecords(**result, records=records)


def _asc_records(index):
    document = index.document
    records = []
    roots_by_row = defaultdict(lambda: defaultdict(list))
    for n in document.nodes:
        for css in ASC_FIELDS:
            if css in n.attributes.get('class', []):
                row = next((p.id for p in index.chains[n.id]
                            if 'indicator-row' in p.attributes.get('class', [])), None)
                roots_by_row[row][css].append(n)
    for row in document.nodes:
        if 'indicator-row' not in row.attributes.get('class', []) or index.blocked(row.id):
            continue
        owned = [i for i in index.descendant_atoms[row.id]
                 if next((n.id for n in index.chains[document.atoms[i].node_id]
                          if 'indicator-row' in n.attributes.get('class', [])), None) == row.id
                 and not index.blocked(document.atoms[i].node_id)]
        appendix = 'table-row' in row.attributes.get('class', [])
        appendix_roots = {}
        if appendix:
            cells = [n for n in document.nodes if n.parent_id == row.id and 'table-cell' in n.attributes.get('class', [])]
            appendix_roots['identifier'] = [n for n in cells if 'indicator' in n.attributes.get('class', [])]
            appendix_roots['body'] = [n for n in cells if 'indicator' not in n.attributes.get('class', [])]
            body_ids = {n.id for n in appendix_roots['body']}
            appendix_roots['applicability'] = [n for n in document.nodes if n.parent_id in body_ids and n.kind == 'paragraph'
                and index.field(index.descendant_atoms[n.id]).text.strip().startswith('Indicator applicability:')]
        fields = {}; issues = []
        for css, key in ASC_FIELDS.items():
            roots = appendix_roots.get(key, []) if appendix else roots_by_row[row.id][css]
            values = []
            for root in roots:
                indices = [i for i in owned if root in index.chains[document.atoms[i].node_id]]
                if key == 'body':
                    indices = [i for i in indices if not any(n.kind == 'footnote'
                               for n in index.chains[document.atoms[i].node_id][:index.chains[document.atoms[i].node_id].index(root)])]
                    if appendix:
                        exclude = {i for n in appendix_roots['applicability'] for i in index.descendant_atoms[n.id]}
                        indices = [i for i in indices if i not in exclude]
                values.append(index.field(indices))
            fields[key] = values or [_field(None, [])]
            if appendix and key == 'applicability' and not roots: issues.append('source_field_not_separately_stated:applicability')
            elif len(roots) != 1: issues.append('missing_or_ambiguous_field:' + key)
            elif not (values[0].text or '').strip(): issues.append('missing_or_empty_field:' + key)
        if 'indicator-row--not-in-use' in row.attributes.get('class', []):
            issues.append('source_marked_not_in_use')
        records.append(ContentRecord(id=record_id(document.source.content_hash, row.id), kind='standard_indicator',
            source_anchor=row.id, locator=row.locator, fields=fields, issues=issues))
    return records
