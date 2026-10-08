# Complete development snapshots

This directory belongs only to `developing`. On 2026-09-22 the user explicitly chose this same public repository for complete development content. `main` now contains only the permanent PE002 Example. These complete snapshots include original materials, the four business databases and human history, including confidential business content. API keys, login sessions, local environments and development evidence are excluded.

## Current saved workspace: 6 October 2026

The current complete snapshot is **workspace-20261006.zip**, based on the coordinated stopped-service capture at **2026-10-06 17:42:50 UTC**. On 8 October it was converted from the already published Appendix F handoff into the existing `workbench-business-package/1` format. This is not a new capture of live work on 8 October.

The package includes the four authoritative business databases, 76 registered originals, 157 source bindings, saved Material/Requirement/interpretation work and its history. It retains 89 source records; PE002 is the only active Example and PE001 remains excluded. PE002 has 85 blocks, 21 active Requirements and 21 matching interpretations. Its exact inventory is in `manifest-20261006.json`. Runtime coordination databases are recreated locally; they are not business authorities. The original six-database Appendix F handoff remains unchanged in the final-report repository.

SHA-256: `4146707902341cd30290a70baffd9b58249db6ed610c286499adf4b4d76b0160`.

### New Windows installation

Prerequisites: Git, Python 3.12, `uv`, and access to dependency downloads. Use company-approved tools. Open Command Prompt and run each command only after the previous one succeeds. `C:\sc` must be a new writable location; otherwise choose another short local path outside OneDrive.

```bat
git clone -c core.longpaths=true --branch developing --single-branch https://github.com/thejaytang/smarter-compliance-aquaculture.git C:\sc
cd /d C:\sc
py -3.12 deployment.py install
py -3.12 deployment.py restore-initial --archive workbench/initial-data/workspace-20261006.zip --sha256 4146707902341cd30290a70baffd9b58249db6ed610c286499adf4b4d76b0160
py -3.12 deployment.py verify
py -3.12 deployment.py start
```

Keep the seed ZIP compressed: restoration checks its hash and uses the application's long-path-aware file operations. After setup, double-click `Open Workbench (Windows).cmd`. On macOS replace `py -3.12` with `python3.12` and use a suitable local directory.

For an existing workspace, update code with `git pull --ff-only` after preserving local changes and stopping the service. Import the package through **Collaboration**, inspect the preview and apply explicitly. Initial restoration refuses an existing workspace; never unpack the seed over saved files. API keys, environments, login sessions and schedules are not imported.

The fresh dependency installation, complete restoration, saved PE002 readback and local HTTP startup passed on macOS on 8 October. Windows dependency resolution passed; native Windows installation and interaction remain unverified.

## Previous complete snapshot: 22 September 2026

`workspace-20260922.zip` remains unchanged for recovery and provenance. It was captured at 2026-09-21 23:02:45 UTC, package ID `8ca47f11-7bd3-4539-b7ea-4dbee796cd6c`. Its SHA-256 is `cd5d033e4cfa10ae91838589b773720d9388918122cb43058d1fa61f9bb05bc0`; see `manifest-20260922.json`.

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
