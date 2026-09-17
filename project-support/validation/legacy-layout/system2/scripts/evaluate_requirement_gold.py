from __future__ import annotations

import argparse
import json
from pathlib import Path

from pdf_extraction.evaluation.requirement_evaluator import (
    evaluate_requirement_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Requirement Gold v2")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("gold/requirements/manifest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/runs/goal04-round1/requirement-baseline.json"),
    )
    args = parser.parse_args()
    report = evaluate_requirement_manifest(args.manifest, args.output)
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
