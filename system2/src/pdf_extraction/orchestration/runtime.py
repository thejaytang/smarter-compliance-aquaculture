"""Runtime artifact ownership, hashing, and collision-safe cleanup helpers."""

from __future__ import annotations

import hashlib
import re
import shutil
from functools import lru_cache
from pathlib import Path


OWNED_OUTPUT_DIRS = {
    "pages", "crops", "figures", "raw", "schemas", "overlays", "ontology",
}
OWNED_OUTPUT_FILES = {
    "canonical.json", "document.md", "document.html", "document.xml",
    "blocks.jsonl", "rag-chunks.json", "regulatory-ir.json",
    "quality-report.json", "performance-report.json", "security-report.json",
    "verification-report.json",
    "runtime-checkpoint.json", "audit-events.jsonl",
}


def owned_base_name(name: str) -> str:
    return re.sub(r" \d+(?=\.[^.]+$|$)", "", name)


def clean_owned_output(output: Path) -> None:
    """Remove only parser-owned artifacts before a non-resume overwrite run."""
    if not output.is_dir():
        return
    for path in output.iterdir():
        base = owned_base_name(path.name)
        if path.is_dir() and base in OWNED_OUTPUT_DIRS:
            shutil.rmtree(path)
        elif path.is_file() and base in OWNED_OUTPUT_FILES:
            path.unlink()


def clean_owned_collision_copies(output: Path) -> None:
    """Remove File Provider/Finder-style numbered copies without touching primaries."""
    if not output.is_dir():
        return
    for path in output.iterdir():
        base = owned_base_name(path.name)
        if path.is_dir() and base in OWNED_OUTPUT_DIRS:
            for nested in sorted(
                path.rglob("*"), key=lambda item: len(item.parts), reverse=True
            ):
                if not re.search(r" \d+(?=\.[^.]+$|$)", nested.name):
                    continue
                if nested.is_dir():
                    shutil.rmtree(nested)
                elif nested.is_file():
                    nested.unlink()
        if not re.search(r" \d+(?=\.[^.]+$|$)", path.name):
            continue
        if path.is_dir() and base in OWNED_OUTPUT_DIRS:
            shutil.rmtree(path)
        elif path.is_file() and base in OWNED_OUTPUT_FILES:
            path.unlink()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_hash() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@lru_cache(maxsize=32)
def model_cache_hash(model_name: str) -> str | None:
    root = Path.cwd() / ".cache" / "paddlex" / "official_models"
    aliases = {model_name, model_name.split("/")[-1]}
    candidates = [
        path for alias in aliases for path in root.glob(f"{alias}*") if path.exists()
    ]
    files = sorted(
        path
        for candidate in candidates
        for path in candidate.rglob("*")
        if path.is_file()
    )
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(str(path.stat().st_size).encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "clean_owned_collision_copies",
    "clean_owned_output",
    "model_cache_hash",
    "owned_base_name",
    "sha256_bytes",
    "sha256_file",
    "source_tree_hash",
]
