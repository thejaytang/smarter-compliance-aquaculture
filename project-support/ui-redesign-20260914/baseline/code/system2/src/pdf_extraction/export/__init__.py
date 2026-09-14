"""Deprecated compatibility facade for :mod:`pdf_extraction.delivery.exporters`."""

from importlib import import_module
import sys

from ..delivery.exporters import *
from ..delivery.exporters import __all__

for _name in ("html", "jsonl", "markdown", "overlay", "rag", "xml"):
    sys.modules[f"{__name__}.{_name}"] = import_module(
        f"pdf_extraction.delivery.exporters.{_name}"
    )

del _name, import_module, sys
