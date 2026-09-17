"""Read-only source records derived from, and version-bound to, Canonical."""
from typing import Literal
from pydantic import Field
from .source import Strict

FieldName = Literal['identifier','title','body','criteria','level','context','notes',
                    'standard','version','category','national_interpretation']
GLOBALGAP_HEADERS = {
    'Standard':'standard', 'Version':'version', 'Product Category':'category',
    'Principle':'identifier', 'Section':'context', 'Description':'body',
    'Criteria':'criteria', 'NIG':'national_interpretation', 'Level':'level',
}

class TextReference(Strict):
    pointer: str
    locator: str

class MappedText(Strict):
    text: str | None
    references: list[TextReference]
    status: Literal['present','empty','missing']
    confidence: None = None
    review_policy: Literal['review_required'] = 'review_required'

class SourceRecord(Strict):
    id: str
    kind: Literal['standard_principle','source_clause']
    source_anchor: str
    locator: str
    fields: dict[FieldName, list[MappedText]]
    issues: list[str] = Field(default_factory=list)
    confidence: None = None
    review_policy: Literal['review_required'] = 'review_required'

class ResidualReference(Strict):
    reference: TextReference
    reason: Literal['outside_record_mapping','source_control','unmapped_record_content','nonliteral_formula']

class SourceRecords(Strict):
    schema_version: Literal['source-records/1'] = 'source-records/1'
    mapper_version: str = 'source-records/1.0.0'
    canonical_schema_version: str
    canonical_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_verification_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    profile: Literal['lovdata_clauses','globalgap_ifa_aq','unsupported']
    status: Literal['review_required','not_supported']
    interpretation: Literal['source_structure_only'] = 'source_structure_only'
    records: list[SourceRecord]
    residual: list[ResidualReference]
    issues: list[str]
    source_reference_count: int
    mapped_reference_count: int
    confidence: None = None
    review_policy: Literal['review_required'] = 'review_required'
