# Windows workspace evidence archive, 2026-10-09

The user explicitly requested publication of the current local contents to the public `thejaytang/smarter-compliance-aquaculture` repository on a new `windows` branch. This archive retains the current four business databases and source directory, including originals, saved work and history. It complements the code and development materials in the same branch. It does not incorporate newer remote changes.

The service was stopped, the service lock and coordinated database writer locks were held during capture, and each database was copied through SQLite backup. All four SQLite integrity checks passed. Every archived file was read back and matched its recorded SHA-256. Source bytes were preserved. Runtime credentials, authentication/session configuration, environments and runtime caches are excluded; source-associated reader evidence remains with the source directory.

The canonical [manifest](manifest.json) lists the capture timestamp, database table counts, every archived path, sizes and hashes. Archive size: 165,341,029 bytes. Full archive SHA-256: `fe1b67c085b8a09f5c75828cc9a0c9d33aebfb230f453bf0e0c19d17d1911851`. The two numbered parts are raw consecutive slices of one ZIP, each below GitHub's single-file limit.

## Known limitation

Normal Collaboration export rejected the current historical PE001 binding with:

```text
Requirement has no matching saved material revision: 8f2d46c7-29f6-57e4-b600-e98781e875dd/1
```

This is an evidence archive, not a validated Collaboration import or initial seed. The history was not rewritten to bypass the error. Do not pass these parts to the seed importer or replace an existing workspace with the databases. SQLite integrity and matching hashes do not establish cross-store semantic validity.

## Reassemble for inspection

Run this Python snippet from this directory. It verifies all parts before creating a new ZIP and refuses to overwrite an existing file. Inspection or extraction should use a separate directory, outside any active workspace.

```python
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path('manifest.json').read_text(encoding='utf-8'))
chunks = []
for part in manifest['parts']:
    content = Path(part['name']).read_bytes()
    assert len(content) == part['bytes']
    assert hashlib.sha256(content).hexdigest() == part['sha256']
    chunks.append(content)
content = b''.join(chunks)
assert len(content) == manifest['bytes']
assert hashlib.sha256(content).hexdigest() == manifest['sha256']
with Path(manifest['archive']).open('xb') as output:
    output.write(content)
```

Capture implementation: [capture script](../../../project-support/validation/capture_windows_archive_20261009.py). Existing validated initial-data and Example packages remain unchanged.
