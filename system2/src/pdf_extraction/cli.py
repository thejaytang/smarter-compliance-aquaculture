from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import ExtractionPipeline


def parse_page_selection(value: str) -> set[int]:
    """Parse a one-based page expression such as 6-28,31 into zero-based indices."""
    selected: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start, end = int(left), int(right)
            if start < 1 or end < start:
                raise argparse.ArgumentTypeError(f"invalid page range: {part}")
            selected.update(range(start - 1, end))
        else:
            page = int(part)
            if page < 1:
                raise argparse.ArgumentTypeError(f"invalid page number: {part}")
            selected.add(page - 1)
    if not selected:
        raise argparse.ArgumentTypeError("page selection is empty")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-preserving PDF extraction")
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse compatible page renders and OCR evidence from the output directory",
    )
    parser.add_argument(
        "--pages",
        type=parse_page_selection,
        help="One-based page selection, for example 6-28 or 6-28,31",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_pdf.is_file():
        print(f"Input PDF not found: {args.input_pdf}", file=sys.stderr)
        return 2
    try:
        pipeline = ExtractionPipeline.from_config_file(args.config)
        document = pipeline.run(
            args.input_pdf, args.output, resume=args.resume, page_indices=args.pages
        )
    except Exception as exc:
        print(f"Extraction failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "document_id": document.document_id,
        "status": document.quality.status.value,
        "pages": document.quality.processed_page_count,
        "blocks": document.quality.block_counts,
        "review_queue": len(document.review_queue),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if document.quality.status.value != "failed" else 1
