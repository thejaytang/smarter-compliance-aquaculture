"""Independent stdlib XML verification; never invokes the extraction implementation."""
from hashlib import sha256
from io import BytesIO
import json
import posixpath
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from ..contracts.excel import ExcelDocument
from .excel_structure import source_relationship_issues

N = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def verify_excel(raw: bytes, document: ExcelDocument) -> dict:
    errors = []
    def parse_xml(data):
        return ET.fromstring(data, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
    def check(ok, reason):
        if not ok: errors.append(reason)
    def shape(el):
        return (el.tag, dict(el.attrib), el.text or '', [(shape(c), c.tail or '') for c in el])
    def same_xml(actual, expected):
        try: return shape(parse_xml(actual)) == shape(expected)
        except (ET.ParseError, TypeError): return False
    def texts(el):
        return ''.join((x.text or '') for x in el if x.tag == N+'t') if not any(x.tag == N+'r' for x in el) else ''.join(
            (t.text or '') for x in el for t in ([x] if x.tag == N+'t' else list(x) if x.tag == N+'r' else []) if t.tag == N+'t')
    try:
        check(sha256(raw).hexdigest() == document.source.content_hash, 'source_hash_mismatch')
        check(document.confidence is None and document.review_policy == 'review_required', 'document_review_policy')
        with ZipFile(BytesIO(raw)) as archive:
            names = [n for n in archive.namelist() if not n.endswith('/')]
            check(len(names) == len(set(names)), 'duplicate_parts')
            blobs = {n: archive.read(n) for n in names}
        check([p.path for p in document.parts] == sorted(blobs), 'part_inventory_mismatch')
        trees = {n: parse_xml(b) for n,b in blobs.items() if n.endswith(('.xml', '.rels', '.vml'))}
        book = trees['xl/workbook.xml']
        check(document.workbook_attributes == dict(book.attrib), 'workbook_attributes')
        entries = list(book.find(N+'sheets'))
        check(len(entries) == len(document.sheets), 'sheet_inventory_mismatch')
        rel_nodes=[r for r in trees['xl/_rels/workbook.xml.rels'] if isinstance(r.tag,str)]
        rels = {r.attrib['Id']: r.attrib for r in rel_nodes}
        check(len(rels)==len(rel_nodes),'duplicate_relationship_identity')
        def part_for(rel):
            uri=urlsplit(rel['Target'])
            if rel.get('TargetMode')=='External' or uri.scheme or uri.netloc or uri.query or uri.fragment or not uri.path:
                raise ValueError('nonlocal_relationship')
            path=unquote(uri.path)
            if '\\' in path or '\x00' in path:raise ValueError('invalid_relationship_path')
            path=posixpath.normpath(path[1:] if path.startswith('/') else 'xl/'+path)
            if path.startswith('../') or path not in trees:raise ValueError('missing_relationship_part')
            return path
        string_relations=[r for r in rels.values() if r.get('Type')==R[1:-1]+'/sharedStrings']
        if len(string_relations)>1:raise ValueError('ambiguous_shared_strings')
        shared=[]
        if string_relations:
            string_root=trees[part_for(string_relations[0])]
            if string_root.tag!=N+'sst':raise ValueError('invalid_shared_string_part')
            shared=[el for el in string_root if el.tag==N+'si']
        used_parts, expected_issues = set(), []
        for entry, sheet in zip(entries, document.sheets):
            rel = rels[entry.attrib[R+'id']]
            check(rel.get('Type')==R[1:-1]+'/worksheet','worksheet_relationship_type')
            part = part_for(rel)
            used_parts.add(part)
            check((sheet.name, sheet.sheet_id, sheet.state, sheet.part, sheet.attributes) ==
                  (entry.get('name'), entry.get('sheetId'), entry.get('state','visible'), part, dict(entry.attrib)), 'sheet_identity:' + part)
            check(sheet.confidence is None and sheet.review_policy == 'review_required', 'sheet_review_policy:' + part)
            root = trees[part]
            check(sheet.worksheet_attributes == dict(root.attrib), 'worksheet_attributes:' + part)
            rows = list(root.find(N+'sheetData'))
            check(sheet.rows == [dict(r.attrib) for r in rows], 'row_properties:' + part)
            source_cells = [c for r in rows for c in r]
            check(len(source_cells) == len(sheet.cells), 'cell_inventory:' + part)
            for src, cell in zip(source_cells, sheet.cells):
                coord = src.get('r')
                label = part + '#' + str(coord)
                check(cell.coordinate == coord and cell.locator == label, 'cell_locator:' + label)
                check(cell.attributes == dict(src.attrib) and same_xml(cell.source_xml, src), 'cell_evidence:' + label)
                value_node, formula_node = src.find(N+'v'), src.find(N+'f')
                value = value_node.text if value_node is not None else None
                formula = (formula_node.text or '') if formula_node is not None else None
                attrs = dict(formula_node.attrib) if formula_node is not None else None
                cache = 'not_formula' if formula_node is None else ('present' if value is not None or (value_node is not None and src.get('t') == 'str') else 'missing')
                text = None
                if src.get('t') == 's':
                    index = int(value)
                    if index < 0: raise ValueError('negative shared string')
                    text = texts(shared[index])
                elif src.get('t') == 'inlineStr':
                    text = texts(src.find(N+'is'))
                elif src.get('t') == 'str':
                    text = value
                check((cell.value, cell.text, cell.formula, cell.formula_attributes, cell.cache_status) ==
                      (value, text, formula, attrs, cache), 'cell_content:' + label)
                check(cell.confidence is None and cell.review_policy == 'review_required', 'cell_review_policy:' + label)
                if cache == 'missing': expected_issues.append('formula_cache_missing:' + label)
            expected_issues.extend(source_relationship_issues(part,root))
            merge_parent = root.find(N+'mergeCells')
            merges = [] if merge_parent is None else [e.get('ref') for e in merge_parent]
            check(sheet.merged_ranges == merges, 'merged_ranges:' + part)
            expected_structure = [el for el in root if el.tag != N+'sheetData']
            check(len(sheet.structure_xml) == len(expected_structure) and all(same_xml(a,b) for a,b in zip(sheet.structure_xml,expected_structure)), 'sheet_structure:' + part)
        expected_book = [el for el in book if el.tag != N+'sheets']
        check(len(document.workbook_structure_xml) == len(expected_book) and all(same_xml(a,b) for a,b in zip(document.workbook_structure_xml,expected_book)), 'workbook_structure')
        for part in document.parts:
            data = blobs[part.path]
            check(part.size == len(data) and part.sha256 == sha256(data).hexdigest(), 'part_hash:' + part.path)
            auxiliary = part.path not in used_parts and part.path != 'xl/workbook.xml'
            if auxiliary and part.path in trees:
                check(same_xml(part.xml, trees[part.path]), 'auxiliary_xml:' + part.path)
            else:
                check(part.xml is None, 'unexpected_auxiliary_xml:' + part.path)
            if part.path not in trees:
                expected_issues.append('binary_part_not_transcribed:' + part.path)
            if part.path.endswith('.rels'):
                for rel in trees[part.path]:
                    if rel.get('TargetMode') == 'External':
                        expected_issues.append('external_relationship_not_fetched:' + part.path + '#' + rel.get('Id',''))
        check(document.issues == expected_issues, 'issue_inventory_mismatch')
    except Exception as exc:
        errors.append('verification_exception:' + type(exc).__name__ + ':' + str(exc))
    return {'schema_version':'excel-verification/1', 'verifier_version':'stdlib-ooxml/1.1.0',
            'status':'failed' if errors else 'passed', 'errors':errors,
            'source_sha256':sha256(raw).hexdigest(),
            'canonical_model_sha256':sha256(json.dumps(document.model_dump(), sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'sheet_count':len(document.sheets), 'cell_count':sum(len(s.cells) for s in document.sheets)}
