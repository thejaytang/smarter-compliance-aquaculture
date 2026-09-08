"""Canonical Regulatory IR implementation derived from Canonical evidence."""

from .extractor import export_regulatory_ir, extract_regulatory_ir
from .models import RegulatoryIRDocument, RegulatoryStatement

__all__ = [
    "RegulatoryIRDocument",
    "RegulatoryStatement",
    "export_regulatory_ir",
    "extract_regulatory_ir",
]
