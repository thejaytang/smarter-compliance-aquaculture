from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from pdf_extraction.ingest.native_extractor import NativeExtractor


def _page_indices(value: str) -> set[int]:
    indices: set[int] = set()
    for part in value.split(","):
        bounds = part.strip().split("-", maxsplit=1)
        start = int(bounds[0])
        end = int(bounds[-1])
        if start < 1 or end < start:
            raise argparse.ArgumentTypeError(f"invalid one-based page range: {part}")
        indices.update(range(start - 1, end))
    return indices


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract source-only native evidence for Gold annotation."
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", required=True, type=_page_indices)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = args.pdf.resolve()
    result = NativeExtractor().extract(source)
    selected = [
        page for page in result.pages if page.page_index in args.pages
    ]
    if {page.page_index for page in selected} != args.pages:
        raise ValueError("selected pages are outside the source document")
    payload = {
        "source": {
            "file_name": source.name,
            "sha256": _sha256(source),
            "page_count": len(result.pages),
        },
        "backend": result.backend,
        "version": result.version,
        "fallback_reason": result.fallback_reason,
        "pages": [asdict(page) for page in selected],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "backend": result.backend,
        "page_numbers": [page.page_index + 1 for page in selected],
        "word_counts": [len(page.words) for page in selected],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
