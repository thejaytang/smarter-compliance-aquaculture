"""Lossless spreadsheet cell values, source coordinates and workbook structure."""
from typing import Literal
from pydantic import Field
from .source import Strict, Snapshot

class LocalExcelSource(Strict):
    source_kind: Literal['local_diagnostic'] = 'local_diagnostic'
    relative_path: str
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    file_format: Literal['xlsx'] = 'xlsx'
    production_eligible: Literal[False] = False

class ExcelCell(Strict):
    coordinate: str
    locator: str
    attributes: dict[str, str]
    value: str | None
    text: str | None
    formula: str | None
    formula_attributes: dict[str, str] | None
    cache_status: Literal['not_formula', 'present', 'missing']
    # Source XML retains rich text, phonetics and extension attributes without guessing.
    source_xml: str
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'

class ExcelSheet(Strict):
    name: str
    sheet_id: str
    state: str
    part: str
    attributes: dict[str, str]
    worksheet_attributes: dict[str, str]
    cells: list[ExcelCell]
    rows: list[dict[str, str]]
    merged_ranges: list[str]
    # Non-cell XML includes columns, views, filtering, tables, print and validation rules.
    structure_xml: list[str]
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'

class ExcelPart(Strict):
    path: str
    sha256: str
    size: int
    # Auxiliary XML is preserved, including styles, table headers, names and relationships.
    xml: str | None = None

class ExcelDocument(Strict):
    schema_version: Literal['excel-document/1'] = 'excel-document/1'
    source: Snapshot | LocalExcelSource
    parser_version: str = 'xlsx-ooxml/1.1.0'
    config_hash: str
    workbook_attributes: dict[str, str]
    sheets: list[ExcelSheet]
    workbook_structure_xml: list[str]
    parts: list[ExcelPart]
    issues: list[str] = Field(default_factory=list)
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'
    requirement_status: Literal['not_extracted'] = 'not_extracted'
