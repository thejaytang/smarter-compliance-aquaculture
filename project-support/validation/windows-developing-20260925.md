# Native Windows developing checkout validation

## Current repair result

The user authorized bug fixes after the initial inspection below. Changes remain local on `developing`; no commit or push was made. The initial failure results below are retained as history, not current status.

Implemented:

- Added a shared native filesystem boundary for long Windows paths, without changing logical path spelling, evidence filenames or hashes. Applied it to workspace storage, migration, recovery, package preparation/validation and initial restore. Native read-only SQLite URIs retain query flags and alias routing; temporary/in-memory connections remain nonpersistent.
- Shortened generated atomic-copy names and moved disposable package preparation to unique short OS temporary directories. Cleanup handles long descendants and read-only copies and checks directory ownership before removal. The system registry remains unchanged (`LongPathsEnabled=0`); only this repository's `core.longpaths` was enabled.
- Confirmed that the original collaboration HTTP 503 was caused by a long atomic-copy path. After fixing that, corrected Windows CRLF conversion of exported JSONL history, which had made the package fail its own database/history validation. Exports now write canonical UTF-8/LF bytes.
- Made rejected POST connections deliver their rejection before a bounded drain/close, retaining Host/Origin/CSRF checks and avoiding Windows unread-body connection resets.
- Fixed the migration test's slash-dependent failure injection. The test runner now uses deployment tool discovery for all suites.
- Installed development dependencies into System2 only, using existing lock constraints. Node 22.20.0 and Poppler 26.09.0 were verified by SHA-256 and installed under local runtime tools. Existing local Tesseract is discovered through deployment. No model weights or remote inference were used.

Final native results:

| Check | Result |
| --- | --- |
| Workbench | 348 passed |
| System1 | 169 passed |
| Frontend | 529 passed |
| System2 | 1122 passed, 53 failed due to absent historical inputs, 1 conditional skip |
| Populated migration and interrupted promotion retry | Passed; saved JSON, authors/time, old SCD bindings and validated delivery retained |
| Two real Windows CMD peers | Passed source/material/Requirement/interpretation round trip, Git update byte preservation and restart readback |
| Native Edge browser | Passed isolated Example restore/open, original HTML HTTP 200, four panes, R1 selection and matching Scope display, with no JavaScript exceptions |
| Source/JSON syntax | 502 Python and 21 JSON files passed, including tests and the new shared module |
| Live workspace | Stopped integrity passed; all six database-directory files remained byte-identical to the pre-update snapshot |

The missing System2 inputs are not a failed checkout: the GitHub recursive tree for `developing` at `cabd108672b908f0b8149d0e473f0bc2c2ef579e` had 11,176 entries, was not truncated, and contained zero `native-page-*.json`, `regulatory-ir.json` or `outputs/runs/goal04-*` entries. Both the root and historical System2 ignore rules exclude the output directory. No local Git history of these outputs was found. Gold, thresholds and test assertions were not weakened; the full System2 suite remains red until the exact retained inputs are supplied. macOS was not executed on this Windows machine.

Final logs are under `workbench/runtime/backups/developing-sync-20260925/`: `workbench-final.log`, `system1-final.log`, `frontend-fixed.log`, `system2-final.log`, `system2-tools-final.log`, `integration-final.log`, `integrity-final.json`, `final-static-checks.json`, and `remote-fixture-audit.json`. The native Edge browser probe is reproducible with `project-support/validation/windows_browser_20260925.py`; its report and screenshot are stored alongside these logs.

## Initial inspection (superseded by repairs above)

Date: 2026-09-25. Checkout: `cabd108672b908f0b8149d0e473f0bc2c2ef579e`, tracking `origin/developing`. Remote branch fetched and switched in the existing user-requested directory. Four pre-existing source edits and three untracked diagnostic files were preserved. No commit, push, business restore, migration of live data, registry change or dependency installation was performed.

## Results

- Three declared environments run Python 3.12.10. Root deployment check and Windows CMD launcher `check` passed.
- Development index boundary passed. Parsed 316 product Python files and 19 JSON files.
- Stopped live-workspace integrity verification passed: four business stores, one original and 170 saved bindings. All six files in the database directory retained their pre-update SHA-256 values.
- Native NumPy, OpenCV, PDFium, lxml and openpyxl imports passed. This does not establish OCR or parsing acceptance.
- Workbench suite: 341 tests, 340 passed and one `WinError 10053` connection-aborted error in `test_capability_identity_and_write_transport_protections`. That exact test passed when rerun alone. The full suite did not have a clean pass.
- System1 suite: all 169 tests passed.
- Migration integration failed creating a same-directory `.migration-<64-character hash>.tmp` file under the temporary migrated workspace. Native long paths are disabled (`LongPathsEnabled=0`). The generated path exceeds the legacy Windows limit; moving only the source checkout would not address this temporary-directory case.
- Colleague handoff integration launched native CMD peers and reached collaboration export, then failed with HTTP 503: `The application receipt is unavailable. Keep the request and retry the same action.` Underlying cause not established; do not equate it with the migration path failure.
- System2 suite not run: its environment lacks pytest. Frontend suite not run: Node is absent from the diagnostic PATH and no executable was found under workbench. Browser pointer/layout acceptance and remote models were not run.

## Evidence and next work

Local evidence and copies of pre-existing edited files are under `workbench/runtime/backups/developing-sync-20260925/`: `workbench-native.log`, `http-recheck.log`, `system1-native.log`, `integration-native.log`, `handoff-native.log`, `integrity.json`, `static-checks.json` and `databases-before.json`. Initial sandbox execution hit temporary-directory permission errors; the native results above were obtained with ordinary Windows permissions.

Windows acceptance remains incomplete. Address paths consistently across restore, migration, export, validation and subprocess handoffs rather than shortening individual prefixes. Current restore code also conservatively rejects paths at 260 UTF-16 units irrespective of OS long-path opt-in. A complete policy needs capability checks, compact generated paths, safe filesystem-boundary handling, preflight coverage, and native long-path/Unicode tests. Preserve original filenames, hashes, IDs and saved provenance. Investigate the independent collaboration 503 and complete missing frontend/System2 checks before claiming full compatibility.
