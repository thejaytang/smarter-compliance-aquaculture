# Complete development snapshots

This directory belongs only to `developing`. On 2026-09-22 the user explicitly chose this same public repository for complete development content. `main` now contains only the permanent PE002 Example. These complete snapshots include original materials, the four business databases and human history, including confidential business content. API keys, login sessions, local environments and development evidence are excluded.

The current complete snapshot is **workspace-20260922.zip**, captured at **2026-09-21 23:02:45 UTC**, package ID `8ca47f11-7bd3-4539-b7ea-4dbee796cd6c`. It contains 76 registered originals, 157 source bindings and the saved material/Requirement/interpretation work, including PE002. Its exact internal inventory is copied to `manifest-20260922.json`. SHA-256: `cd5d033e4cfa10ae91838589b773720d9388918122cb43058d1fa61f9bb05bc0`.

For a fresh development installation, after dependency setup:

```sh
python3.12 deployment.py restore-initial --archive workbench/initial-data/workspace-20260922.zip --sha256 cd5d033e4cfa10ae91838589b773720d9388918122cb43058d1fa61f9bb05bc0
python3.12 deployment.py verify
```

On Windows use `py -3.12` instead. For an existing workspace, import the package through **Collaboration**, inspect the preview and apply explicitly; resolve conflicts without overwriting the workspace files. Application updates never import it. Native Windows restoration remains unverified.

## Historical first handoff, 2026-09-17

The following package and manifest remain unchanged for recovery and provenance. They predate the current saved Material and Requirement work.

The package is immutable. Application updates never apply it. Future work is exchanged through Collaboration, not by committing active databases. Keep this snapshot as recovery evidence if it is later removed from the application checkout; removal from a branch does not erase Git history.

## 1. First installation only

Install the environment using the root environment guide, then run from the repository root.

Windows Command Prompt:

```bat
py -3.12 deployment.py restore-initial --archive "workbench\initial-data\workspace-20260917.zip" --sha256 a6978fb67ff00bdf55d9a99e1a1488f86ebdca1e3e55c4d0a618e1ec91774a75
py -3.12 deployment.py verify
```

macOS:

```sh
python3.12 deployment.py restore-initial --archive workbench/initial-data/workspace-20260917.zip --sha256 a6978fb67ff00bdf55d9a99e1a1488f86ebdca1e3e55c4d0a618e1ec91774a75
python3.12 deployment.py verify
```

Then open the launcher for your operating system. Initial restoration refuses an installation with existing work. A retry of an interrupted import is allowed only for the same verified package. No external tasks or schedules are enabled by the import.

## 2. Contents and verification

- `workspace-20260917.zip`: coordinated SQLite snapshots, originals, derived human-history logs and logical exchange representation.
- `workspace-20260917.zip.sha256`: checksum of the complete ZIP.
- `manifest.json`: human-readable copy of the internal inventory with per-file hashes, database table counts and source bindings.

The snapshot preserves 88 source records, 137 operations, 240 source-history entries, 73 source versions and 76 artifacts. Materials, Requirement and S/C/D saved work were empty at handoff; development examples are not restored as real work. The package contains no executed compliance judgment. Native Windows verification of this revised layout remains pending.
