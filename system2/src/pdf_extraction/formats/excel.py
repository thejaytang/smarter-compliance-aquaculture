"""Read OOXML without calculating formulas, loading links or executing active content."""
from hashlib import sha256
from io import BytesIO
import json
import posixpath
import re
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
from lxml import etree
from ..contracts.excel import ExcelCell, ExcelSheet, ExcelPart, ExcelDocument, LocalExcelSource
from ..contracts.source import Snapshot
from .excel_structure import source_relationship_issues

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
POLICY = {'max_parts': 10000, 'max_expanded_bytes': 134217728, 'format': 'xlsx', 'execute': False}
CONFIG_HASH = sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest()

def parse_excel(raw: bytes, source: Snapshot | LocalExcelSource) -> ExcelDocument:
    if source.file_format.lower().lstrip('.') != 'xlsx':
        raise ValueError('excel_legacy_xls_not_supported')
    if sha256(raw).hexdigest() != source.content_hash:
        raise ValueError('snapshot_hash_mismatch')
    with ZipFile(BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if (len(entries) > POLICY['max_parts'] or sum(e.file_size for e in entries) > POLICY['max_expanded_bytes']
            or len(set(names)) != len(names)):
            raise ValueError('xlsx_container_limits_or_duplicate_parts')
        if any(n.startswith('/') or '..' in n.split('/') or '\\' in n for n in names):
            raise ValueError('xlsx_unsafe_part_path')
        blobs = {n: archive.read(n) for n in names if not n.endswith('/')}
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    trees = {}
    for name, data in blobs.items():
        if name.endswith(('.xml', '.rels', '.vml')):
            tree = etree.fromstring(data, parser)
            if tree.getroottree().docinfo.doctype:
                raise ValueError('xlsx_doctype_not_supported')
            trees[name] = tree
    def xml(el):
        return etree.tostring(el, encoding='unicode', with_tail=False)
    def tag(local):
        return '{' + NS + '}' + local
    book = trees['xl/workbook.xml']
    if book.tag != tag('workbook'):
        raise ValueError('xlsx_namespace_not_supported')
    relationships = {}
    for el in trees['xl/_rels/workbook.xml.rels']:
        if not isinstance(el.tag,str):continue
        rid = el.get('Id')
        if not rid or rid in relationships:
            raise ValueError('xlsx_duplicate_or_missing_relationship')
        relationships[rid] = el
    def resolve(relationship):
        target=relationship.get('Target','')
        uri=urlsplit(target)
        if (relationship.get('TargetMode')=='External' or uri.scheme or uri.netloc
            or uri.query or uri.fragment or not target):
            raise ValueError('xlsx_relationship_not_local')
        target=unquote(uri.path)
        if '\\' in target or '\x00' in target:
            raise ValueError('xlsx_relationship_invalid_path')
        part=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('xl',target))
        if part.startswith('../') or part not in trees:
            raise ValueError('xlsx_relationship_part_missing_or_outside')
        return part
    string_relationships=[el for el in relationships.values() if el.get('Type')==REL+'/sharedStrings']
    if len(string_relationships)>1:
        raise ValueError('xlsx_shared_string_relationship_ambiguous')
    strings=trees[resolve(string_relationships[0])] if string_relationships else None
    if strings is not None and strings.tag!=tag('sst'):
        raise ValueError('xlsx_shared_string_part_type_invalid')
    shared=strings.findall(tag('si')) if strings is not None else []
    sheets, issues, used_parts = [], [], set()
    source_sheets = book.find(tag('sheets'))
    if source_sheets is None or len(source_sheets) == 0:
        raise ValueError('xlsx_no_sheets')
    for entry in source_sheets:
        relationship = relationships[entry.get('{' + REL + '}id')]
        if relationship.get('TargetMode') == 'External' or relationship.get('Type') != REL+'/worksheet':
            raise ValueError('xlsx_nonworksheet_sheet_not_supported')
        part = resolve(relationship)
        if part in used_parts:
            raise ValueError('xlsx_sheet_part_invalid')
        used_parts.add(part)
        sheet = trees[part]
        if sheet.tag != tag('worksheet'):
            raise ValueError('xlsx_sheet_type_invalid')
        cells, rows, seen = [], [], set()
        data = sheet.find(tag('sheetData'))
        if data is None:
            raise ValueError('xlsx_missing_sheet_data')
        for row in data:
            rows.append(dict(row.attrib))
            for cell in row:
                if cell.tag != tag('c'):
                    raise ValueError('xlsx_unknown_cell_structure')
                coord = cell.get('r', '')
                if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}', coord) or coord in seen:
                    raise ValueError('xlsx_cell_coordinate_invalid_or_duplicate')
                col, rownum = re.fullmatch(r'([A-Z]+)([0-9]+)', coord).groups()
                column = 0
                for ch in col:
                    column = column * 26 + ord(ch) - 64
                if column > 16384 or int(rownum) > 1048576 or str(int(rownum)) != row.get('r'):
                    raise ValueError('xlsx_cell_coordinate_out_of_bounds')
                seen.add(coord)
                val, formula = cell.find(tag('v')), cell.find(tag('f'))
                value = val.text if val is not None else None
                text = None
                if cell.get('t') == 's':
                    try:
                        index = int(value)
                        if index < 0: raise ValueError()
                        string = shared[index]
                    except (ValueError, TypeError, IndexError) as exc:
                        raise ValueError('xlsx_shared_string_invalid') from exc
                    text = ''.join(string.xpath('./s:t/text() | ./s:r/s:t/text()', namespaces={'s': NS}))
                elif cell.get('t') == 'inlineStr':
                    text = ''.join(cell.xpath('./s:is/s:t/text() | ./s:is/s:r/s:t/text()', namespaces={'s': NS}))
                elif cell.get('t') == 'str':
                    text = value
                cached = 'not_formula' if formula is None else ('present' if value is not None or (val is not None and cell.get('t') == 'str') else 'missing')
                if cached == 'missing':
                    issues.append('formula_cache_missing:' + part + '#' + coord)
                cells.append(ExcelCell(coordinate=coord, locator=part + '#' + coord,
                    attributes=dict(cell.attrib), value=value, text=text,
                    formula=formula.text or '' if formula is not None else None,
                    formula_attributes=dict(formula.attrib) if formula is not None else None,
                    cache_status=cached, source_xml=xml(cell)))
        merges=sheet.xpath('./s:mergeCells/s:mergeCell/@ref', namespaces={'s': NS})
        issues.extend(source_relationship_issues(part,cells,merges))
        sheets.append(ExcelSheet(name=entry.get('name'), sheet_id=entry.get('sheetId'),
            state=entry.get('state', 'visible'), part=part, attributes=dict(entry.attrib), worksheet_attributes=dict(sheet.attrib), cells=cells, rows=rows,
            merged_ranges=merges,
            structure_xml=[xml(el) for el in sheet if el.tag != tag('sheetData')]))
    if not any(c.value is not None or c.text or c.formula is not None for s in sheets for c in s.cells):
        raise ValueError('xlsx_empty_workbook')
    parts = []
    for name in sorted(blobs):
        data = blobs[name]
        auxiliary = name not in used_parts and name != 'xl/workbook.xml'
        parts.append(ExcelPart(path=name, sha256=sha256(data).hexdigest(), size=len(data),
            xml=xml(trees[name]) if auxiliary and name in trees else None))
        if name not in trees:
            issues.append('binary_part_not_transcribed:' + name)
        if name.endswith('.rels'):
            for relationship in trees[name]:
                if relationship.get('TargetMode') == 'External':
                    issues.append('external_relationship_not_fetched:' + name + '#' + relationship.get('Id', ''))
    return ExcelDocument(source=source, config_hash=CONFIG_HASH, workbook_attributes=dict(book.attrib), sheets=sheets, parts=parts,
        workbook_structure_xml=[xml(el) for el in book if el.tag != tag('sheets')], issues=issues)
