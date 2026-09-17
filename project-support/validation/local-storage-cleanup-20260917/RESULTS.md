# Authorized local backup cleanup

Date: 2026-09-17. Scope: the user approved deleting obsolete local database copies, historical runtime backups and isolated test output while retaining current work, private configuration, development evidence and a verified complete recovery set.

## 1. Result

- Deleted all 131 audited paths without errors: 107,066 regular files, 54,377,642,506 logical bytes (54.38 GB).
- Their inventoried allocated blocks totalled 26,829,975,552 bytes. Available disk space increased by 26,924,347,392 bytes (26.92 GB) during deletion. Logical size differs from disk occupancy because some files were cloud placeholders; the free-space measurement also includes concurrent filesystem activity.
- Preserved all Git-tracked files. No commit, push, branch change or remote operation was performed for this cleanup.
- Exact paths and deletion receipts are in [plan.json](plan.json) and [result.json](result.json). These are local development records.

## 2. Preserved

- Active `workbench/workspace/` data and original sources, current runtime settings/state, installed environments, application code and tests.
- `workbench/initial-data/workspace-20260917.zip`, including its matching checksum, manifest and guide.
- Complete recovery at `workbench/runtime/backups/naming-structure-20260917-ready`: 188 inventoried data/support files, 6 SQLite stores and 704 application files. File hashes, database integrity, cross-store/source references and code inventory passed verification before and after cleanup.
- Original migration checkpoint at `workbench/runtime/backups/architecture-v1`.
- Legacy System2 outputs still referenced by regression tests, including baselines and diagrams; original PDF fixtures and development reports. Top-level historical runtime scripts/reports also remain. An ignored path or old name alone was not treated as grounds for deletion.
- Outer workspace directories 01–04.

## 3. Verification

- All 182 protected business/source/configuration files remain byte-identical to their pre-deletion hash baseline.
- All four business databases pass SQLite integrity and foreign-key checks. Source governance retains 88 sources, 73 source versions, 76 artifacts, 137 operations and 240 history rows.
- The published initial-data ZIP remains SHA-256 `a6978fb67ff00bdf55d9a99e1a1488f86ebdca1e3e55c4d0a618e1ec91774a75`.
- Current configuration and saved database values contain no references to the proposed deleted roots; inspected running Workbench/parser processes had no open files in those roots.
- `/health` and the application page both returned HTTP 200 after deletion. This confirms availability, not a new complete UI acceptance run.
- No target remains. No Git-tracked file was deleted, and HEAD remains `6808e30e91d048eb076bddf8925b7be65c97caa3`.

Native Windows and model tests were not rerun: this task removed inactive local files without changing product code. Historical reports remain historical evidence; their deleted temporary runtime paths are no longer available.
