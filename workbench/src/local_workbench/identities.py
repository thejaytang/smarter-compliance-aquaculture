"""Approved reviewer roster. Original external review evidence keeps its original spelling."""
REVIEWERS = ("Ana Jokic", "Daniel Restad", "Weijie Tang")
ALIASES = {"jay": "Weijie Tang", "ana": "Ana Jokic", "jokic; ana": "Ana Jokic", "dr": "Daniel Restad"}

def canonical_name(name):
    name = str(name or "").strip()
    return ALIASES.get(name.casefold(), next((n for n in REVIEWERS if n.casefold() == name.casefold()), name))
