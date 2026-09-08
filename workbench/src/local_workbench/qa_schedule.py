"""Idempotent local weekly sampling; no retrieval, parsing or machine review."""
import json
from pathlib import Path
from .adapter import System1


def run_due(root=None):
    root = Path(root or Path(__file__).resolve().parents[2])
    return System1(root.parent / "system1").call("random_qa")


if __name__ == "__main__":
    print(json.dumps({"system1": run_due(), "system2": {"status": "NOT_CONNECTED"},
                      "system3": {"status": "NOT_CONNECTED"}}, ensure_ascii=False))
