from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import AppConfig
from ..models import Document
from .full_system import evaluate_full_system


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the complete scheme-three product")
    parser.add_argument("canonical", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--gold-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    document = Document.model_validate_json(args.canonical.read_text(encoding="utf-8"))
    gold = json.loads(args.gold_report.read_text()) if args.gold_report and args.gold_report.is_file() else None
    report = evaluate_full_system(document, AppConfig.from_yaml(args.config), args.canonical.parent, gold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.enforce and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
