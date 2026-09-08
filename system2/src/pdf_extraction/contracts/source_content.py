"""Version 2 adds literal HTML content without changing the version 1 contract."""
from typing import Literal
from pydantic import Field
from .source_records import SourceRecords, SourceRecord, MappedText, TextReference

# Structural source labels, not inferred legal Requirement types.
CONTENT_KINDS = {
    'heading': 'source_heading', 'paragraph': 'source_paragraph',
    'table_cell': 'source_table_cell', 'list_item': 'source_list_item',
    'footnote': 'source_note', 'caption': 'source_caption',
    'definition_term': 'source_definition_term', 'definition': 'source_definition',
    'disclosure_heading': 'source_heading',
}
ASC_FIELDS = {'indicator-id': 'identifier', 'indicator-content': 'body',
              'indicator-applicability': 'applicability'}


class ContentRecord(SourceRecord):
    kind: Literal['standard_principle', 'source_clause', 'standard_indicator',
                  'source_heading', 'source_paragraph', 'source_table_cell',
                  'source_list_item', 'source_note', 'source_caption',
                  'source_definition_term', 'source_definition', 'source_text',
                  'source_image', 'source_link']
    fields: dict[Literal['identifier', 'title', 'body', 'criteria', 'level', 'context',
                         'notes', 'standard', 'version', 'category',
                         'national_interpretation', 'applicability'], list[MappedText]]
    # Pointers address Canonical nodes, table/cell geometry, lists and links.
    # Ancestor nodes preserve chapter/annex, display variants and source attributes.
    structure: list[TextReference] = Field(default_factory=list)


class ContentRecords(SourceRecords):
    schema_version: Literal['source-records/2'] = 'source-records/2'
    mapper_version: str = 'source-records/2.0.0'
    profile: Literal['lovdata_clauses', 'globalgap_ifa_aq', 'asc_content',
                     'html_content', 'unsupported']
    records: list[ContentRecord]
