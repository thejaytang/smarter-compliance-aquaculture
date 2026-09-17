from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parser_state_fingerprint(root: Path, config: Path) -> dict[str, object]:
    """Hash the local parser implementation and its effective static inputs."""

    root = root.resolve()
    candidates = [
        *sorted((root / "src" / "pdf_extraction").rglob("*.py")),
        config.resolve(),
        (root / "pyproject.toml").resolve(),
        (root / "uv.lock").resolve(),
    ]
    files = [path for path in candidates if path.is_file()]
    digest = hashlib.sha256()
    entries: list[dict[str, str]] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        file_digest = hashlib.sha256(content).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        entries.append({"path": relative, "sha256": file_digest})
    return {
        "algorithm": "sha256(path\\0sha256(content)\\n)",
        "sha256": digest.hexdigest(),
        "file_count": len(entries),
        "files": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a deterministic fingerprint for a frozen parser state."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/asc-sample-no-vl.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON artifact path; stdout is still emitted.",
    )
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else args.root / args.config
    payload = json.dumps(
        parser_state_fingerprint(args.root, config),
        ensure_ascii=False,
        indent=2,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{payload}\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
