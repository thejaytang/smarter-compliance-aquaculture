"""Deprecated compatibility facade for :mod:`pdf_extraction.delivery.ontology`."""

from importlib import import_module
import sys

from ..delivery.ontology import *
from ..delivery.ontology import __all__

sys.modules[f"{__name__}.mapper"] = import_module(
    "pdf_extraction.delivery.ontology.mapper"
)

del import_module, sys
