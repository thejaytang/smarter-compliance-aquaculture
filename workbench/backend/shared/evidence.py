"""Read-only PDF delivery from an adapter-resolved, registered artifact."""
import hashlib
import re
from pathlib import Path


def registered_pdf(artifact, expected_hash=None):
    path = Path(artifact["path"])
    if path.suffix.lower() != ".pdf":
        raise ValueError("This original is not a PDF. Use its document viewer.")
    recorded = str(artifact.get("hash") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", recorded):
        raise ValueError("The original has no valid file fingerprint. Verify the source first.")
    if expected_hash is not None and expected_hash != recorded:
        raise ValueError("The original version has changed. Reload and review it again.")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or hashlib.sha256(data).hexdigest() != recorded:
        raise ValueError("The local original does not match its registered fingerprint. Keep the task pending and verify the source.")
    return data, recorded


def pdf_range(data, header):
    """Native PDF readers use byte ranges; reject malformed/multiple ranges."""
    if not header:
        return 200, data, {}
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()):
        return 416, b"", {"Content-Range": f"bytes */{len(data)}"}
    first, last = match.groups()
    if first:
        start, end = int(first), min(int(last) if last else len(data) - 1, len(data) - 1)
    else:
        start, end = max(0, len(data) - int(last)), len(data) - 1
    if start > end:
        return 416, b"", {"Content-Range": f"bytes */{len(data)}"}
    return 206, data[start:end + 1], {"Content-Range": f"bytes {start}-{end}/{len(data)}"}
