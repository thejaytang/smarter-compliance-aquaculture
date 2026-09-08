"""Read-only real-source acceptance of a completed HTML batch and diagnostic XLSX.

Run from System2 with PYTHONPATH=src. No downloads, source decisions or source writes.
The output file must not already exist. This is evidence, not human acceptance.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from lxml import html
from openpyxl import load_workbook

from pdf_extraction.contracts.html import HtmlDocument
from pdf_extraction.intake.system1 import read_system1
from pdf_extraction.intake.registry import read_snapshot
from pdf_extraction.orchestration.source_batch import write_json
from validate_html_goal import check_windows


def raw_locator_index(tree):
    """lxml XPath, independent of the BeautifulSoup parser and record mapper."""
    lookup = {}
    for node in tree.iter():
        if not isinstance(node.tag, str): continue
        parts = []
        current = node
        while current is not None and isinstance(current.tag, str):
            index = 1 + sum(s.tag == current.tag for s in current.itersiblings(preceding=True))
            parts.append(f'{current.tag}:nth-of-type({index})')
            current = current.getparent()
        lookup[' > '.join(reversed(parts))] = node
    return lookup


def has_class(node, value): return value in node.get('class', '').split()


def raw_text(root, excluded=()):
    parts = []
    for text in root.xpath('.//text()'):
        owner = text.getparent().getparent() if text.is_tail else text.getparent()
        ancestry = [owner, *owner.iterancestors()] if owner is not None else []
        if any(n in excluded for n in ancestry): continue
        parts.append(str(text))
    return ''.join(parts)


def check_asc(tree, lookup, mapping):
    rows = [n for n in tree.iter() if isinstance(n.tag, str) and has_class(n, 'indicator-row')]
    records = [r for r in mapping['records'] if r['kind'] == 'standard_indicator']
    failures = []; field_count = 0
    if len(rows) != len(records): failures.append('indicator_inventory')
    for record in records:
        row = lookup[record['locator']]
        appendix = has_class(row, 'table-row')
        if appendix:
            cells = [n for n in row if has_class(n, 'table-cell')]
            selected = {'identifier': [n for n in cells if has_class(n, 'indicator')],
                        'body': [n for n in cells if not has_class(n, 'indicator')]}
            selected['applicability'] = [n for body in selected['body'] for n in body
                if n.tag == 'p' and raw_text(n).strip().startswith('Indicator applicability:')]
        else:
            selected = {key: [n for n in row.iterdescendants() if has_class(n, css)] for key, css in
                [('identifier','indicator-id'),('body','indicator-content'),('applicability','indicator-applicability')]}
        for key, roots in selected.items():
            expected = []
            for root in roots:
                excluded = [n for n in root.iterdescendants() if has_class(n, 'popup-inner') or has_class(n, 'fotnote')] if key == 'body' else []
                if appendix and key == 'body': excluded += selected['applicability']
                expected.append(raw_text(root, excluded))
            actual = [f['text'] for f in record['fields'][key]]
            if actual != (expected or [None]): failures.append(record['source_anchor'] + ':' + key)
            field_count += 1
        if ('source_marked_not_in_use' in record['issues']) != has_class(row, 'indicator-row--not-in-use'):
            failures.append(record['source_anchor'] + ':inactive_state')
    return {'records': len(records), 'fields_checked': field_count, 'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--system1', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--excel-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    handoff = read_system1(args.system1)
    batch = json.loads((args.run/'live-html/batch.json').read_bytes())
    windows = json.loads(Path('tests/fixtures/html/source-windows-20260907.json').read_bytes())['windows']
    report = {'registry_sha256': handoff.registry_sha256, 'html': [], 'failures': []}
    for result in batch['results']:
        sid = result['source']['source_id']; snap = result['source']['snapshot_id']
        if result['status'] != 'review_required':
            report['html'].append({'source_id': sid, 'status': result['status'], 'reasons': result['reason_codes']})
            continue
        directory = args.run/'live-html'/snap
        document = HtmlDocument.model_validate_json((directory/'canonical.json').read_bytes())
        raw = read_snapshot(document.source, handoff.source_root)
        tree = html.document_fromstring(raw.decode(document.encoding)); lookup = raw_locator_index(tree)
        mapping = json.loads((directory/'source-records.json').read_bytes())
        failures = []; checked = set()
        for record in mapping['records']:
            for values in record['fields'].values():
                for field in values:
                    for ref in field['references']:
                        if ref['pointer'] in checked: continue
                        index = int(ref['pointer'].split('/')[2]); atom = document.atoms[index]
                        locator, text_index = re.fullmatch(r'(.*)::text\((\d+)\)', ref['locator']).groups()
                        texts = lookup[locator].xpath('text()')
                        if int(text_index) > len(texts) or str(texts[int(text_index)-1]) != atom.text:
                            failures.append('raw_text:' + ref['pointer'])
                        checked.add(ref['pointer'])
        node_map = {n.id: n for n in document.nodes}; residual_roles = Counter()
        for residual in mapping['residual']:
            atom = document.atoms[int(residual['reference']['pointer'].split('/')[2])]; node = node_map[atom.node_id]
            roles = set()
            while node:
                roles.add(node.role)
                if 'share-paragraf' in node.attributes.get('class', []): roles.add('control')
                node = node_map.get(node.parent_id)
            role = 'control_or_navigation' if roles & {'control','navigation'} else 'metadata' if 'metadata' in roles else 'content'
            residual_roles[role] += 1
        if residual_roles['content']: failures.append('unmapped_literal_content')
        old = json.loads((args.baseline/'historical-html'/snap/'source-records.json').read_bytes())
        current_old = [{k:v for k,v in r.items() if k!='structure'} for r in mapping['records'] if r['kind']=='source_clause']
        if current_old != old['records'] and old['profile']=='lovdata_clauses': failures.append('legacy_clause_change')
        checks = check_windows(document, [w for w in windows if w['source_id']==sid])
        if any(w['status']!='passed' for w in checks): failures.append('frozen_source_window')
        record = {'source_id': sid, 'status': result['status'], 'source_sha256': sha256(raw).hexdigest(),
            'record_kinds': dict(Counter(r['kind'] for r in mapping['records'])), 'raw_text_references_checked': len(checked),
            'residual_roles': dict(residual_roles), 'windows_checked': len(checks), 'failures': failures}
        if document.profile=='asc':
            record['asc_fields'] = check_asc(tree, lookup, mapping)
            failures.extend(record['asc_fields']['failures'])
        report['html'].append(record)
        report['failures'].extend(sid + ':' + f for f in failures)
        print(sid, len(checked), 'raw references; failures', len(failures), flush=True)

    raw = args.excel_source.read_bytes()
    workbook = load_workbook(args.excel_source, read_only=True, data_only=False)
    sheet = workbook['CL - IFA v6 Smart - AQ']
    mapping = json.loads((args.run/'excel/source-records.json').read_bytes())
    old = json.loads((args.baseline/'globalgap/source-records.json').read_bytes())
    excel_failures = []
    if [{k:v for k,v in r.items() if k!='structure'} for r in mapping['records']] != old['records']: excel_failures.append('legacy_excel_change')
    columns = {'standard':1,'version':2,'category':3,'identifier':4,'context':5,'body':6,'criteria':7,'national_interpretation':8,'level':9}
    rows = {int(r['locator'].rsplit('=',1)[1]): r for r in mapping['records']}
    source_rows = 0
    for cells in sheet.iter_rows(min_row=10, max_col=9):
        if cells[1].value != 'IFA v6 Smart' or cells[2].value != 'AQ' or not cells[3].value: continue
        source_rows += 1; row = cells[3].row
        if row not in rows: excel_failures.append(f'missing_row:{row}');continue
        for key, col in columns.items():
            value = cells[col-1].value
            if rows[row]['fields'][key][0]['text'] != (str(value) if value is not None else None): excel_failures.append(f'field:{row}:{key}')
    workbook.close()
    if source_rows != len(rows): excel_failures.append('excel_inventory')
    report['excel'] = {'source_kind':'local_diagnostic','production_eligible':False,
        'source_sha256':sha256(raw).hexdigest(), 'records':source_rows,'fields_checked':source_rows*9,'failures':excel_failures}
    report['failures'].extend(excel_failures)
    handoff.assert_current()
    report['status'] = 'failed' if report['failures'] else 'passed'
    write_json(args.output, report)
    return int(bool(report['failures']))


if __name__=='__main__': raise SystemExit(main())
