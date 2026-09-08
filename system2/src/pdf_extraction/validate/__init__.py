"""Compatibility facade for canonical and extraction validation helpers.

Submodules are loaded on demand so callers that only need schema validation do
not initialize image-processing dependencies.
"""

from __future__ import annotations

from typing import Any


_EXPORTS = {
    "build_quality_report": ("quality_gate", "build_quality_report"),
    "validate_document": ("schema_validator", "validate_document"),
    "write_schema": ("schema_validator", "write_schema"),
    "structural_fingerprint": ("fingerprint", "structural_fingerprint"),
    "build_page_completeness_report": (
        "completeness_gate",
        "build_page_completeness_report",
    ),
    "apply_secondary_native_gate": (
        "secondary_native_gate",
        "apply_secondary_native_gate",
    ),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attribute_name = target
    module = __import__(f"{__name__}.{module_name}", fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


__all__ = list(_EXPORTS)
