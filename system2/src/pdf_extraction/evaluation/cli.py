from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import AppConfig
from .evaluator import evaluate_manifest, enforce_regression_thresholds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate canonical PDF extraction outputs")
    parser.add_argument("--manifest", type=Path, default=Path("gold/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/evaluation-report.json"))
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    report = evaluate_manifest(args.manifest, args.output)
    failures = enforce_regression_thresholds(
        report, AppConfig.from_yaml(args.config).evaluation.regression_thresholds
    ) if args.enforce else []
    print(json.dumps({"report": str(args.output), "aggregate": report["aggregate"], "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
