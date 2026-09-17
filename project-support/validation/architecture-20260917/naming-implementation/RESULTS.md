# Naming, structure and first-handoff verification

Date: 2026-09-17. Current publication status is recorded in the root local PROJECT_STATE.md.

## 1. Implemented

- Flattened System1 `Code/src` and `Code/deployment` to the owning component; rebuilt its locked Python 3.12 environment. The previous environment is retained in the consistent recovery folder.
- Retained the unreferenced `derived 2.py` implementation locally as `derived-legacy.py`; it is outside product imports and the Git index.
- Established explicit backend packages. Application orchestration lives under local_workbench; shared utilities and System3 have explicit imports without path injection. Application composition was extracted from the HTTP server without changing its class body.
- Corrected attributes, test/dependency/guide paths and workbook guide generation version. PDFs retain binary offsets. Added Windows filename/case/Unicode and Python naming checks.
- Added an explicitly authorized first-handoff package under workbench/initial-data, preserving four business stores, sources and human history. First restore validates it, rejects existing work and supports same-package interruption retry. Credentials/runtime/development files remain local.

## 2. Evidence

- Consistent pre-change backup: `workbench/runtime/backups/naming-structure-20260917-ready`, 704 original product files and 188 data/support files, six consistent SQLite snapshots. Moves are recorded in moves.json.
- 326 Workbench tests passed; 169 System1 tests passed.
- System2 full run: 1163 passed, two failed subprocess environment checks, two skipped. After explicit import-path correction, all 17 affected environment/handoff tests passed. All 1165 distinct tests therefore have passing coverage; the full run was not misreported as clean.
- 26 frontend tests passed.
- Populated migration/failure-retry and two real local peers passed. Real source/material/Requirement/interpretation exchange, restart readback and application-only Git update preserved local work.
- Current initial snapshot passed fresh restoration, interrupted restoration/retry, exact database-byte comparison, refusal to overwrite and actual Application readback of 88 sources and 73 originals.
- 310 Python 3.12 source files parsed. The staged boundary contains 708 product files and four initial-data files. Naming and targeted credential-pattern scans passed.
- Normal service restarted on port 62742; /health returned the expected workspace and /api/state returned 88 sources.

## 3. Environment failures and boundaries

The first recursive test command incorrectly mixed component environments; the new local runner selects each suite explicitly. Separate handoff attempts timed out on iCloud-backed local code/dependency/cache reads; an open cached Python module was observed at the blocked worker. Existing files were downloaded locally and validation used a local temporary Python cache. The subsequent real integration run passed. No business data was reset to bypass those failures.

Native Windows execution of this revised layout remains unverified. No paid/remote model or source-processing calls were made. The data package is publicly accessible once pushed; removing it later from a branch does not erase Git history. Package checks do not establish legal compliance or extraction fidelity.
