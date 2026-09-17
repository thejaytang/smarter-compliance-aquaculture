# Initial business snapshot

This is the complete first-handoff business snapshot explicitly authorized for public GitHub publication on 2026-09-17. It includes original materials, the four business databases and human history, including confidential business content. API keys, login sessions, local environments and development evidence are excluded.

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
