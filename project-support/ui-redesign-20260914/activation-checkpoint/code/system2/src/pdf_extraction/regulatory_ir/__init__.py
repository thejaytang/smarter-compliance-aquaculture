"""Deprecated compatibility facade for :mod:`pdf_extraction.domains.regulatory`."""

from importlib import import_module
import sys

from ..domains.regulatory import *
from ..domains.regulatory import __all__

for _name in ("extractor", "models"):
    sys.modules[f"{__name__}.{_name}"] = import_module(
        f"pdf_extraction.domains.regulatory.{_name}"
    )

del _name, import_module, sys
