"""Canonical-document construction boundary.

The implementation is intentionally decomposed across routing, layout,
parsers, assembly, and reconciliation packages.  The orchestrator coordinates
those capabilities; it must not own their domain rules.
"""

