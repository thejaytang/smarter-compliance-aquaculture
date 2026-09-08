"""Deprecated compatibility facade for :mod:`pdf_extraction.domains.requirements`."""

from importlib import import_module
import sys

from ..domains.requirements import *
from ..domains.requirements import __all__

for _name in (
    "canonical",
    "clauses",
    "footnotes",
    "hierarchy",
    "native_assembler",
    "profile",
    "semantics",
):
    sys.modules[f"{__name__}.{_name}"] = import_module(
        f"pdf_extraction.domains.requirements.{_name}"
    )

del _name, import_module, sys
