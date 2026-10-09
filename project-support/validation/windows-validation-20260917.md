# Native Windows validation, 2026-09-17

Revision: `31c4cf9`, branch `main`. Python: 3.12.10, Windows.

## Result

The current checkout is not ready to launch. Initial restoration fails while writing a 272-character staging path. `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled` is `0`. The parent directory exists; the failing file is the NYTEK23 HTML original under `workbench/runtime/backups/initial-import/prepared/sources/system1/A_Public_Authority/`.

The ordinary start command subsequently refuses startup because `workbench/runtime/state/layout.json` is absent. No application browser or business workflow acceptance is claimed.

## Passed

- Installation through `deployment.py install`: all three component virtual environments.
- `uv pip check`: application (1 package), System1 (4), System2 (40).
- Windows CMD launcher with `check`: correctly invokes the deployment entry and Python 3.12.
- Product index boundary and Windows filename/collision checks.
- Syntax parsing of 310 tracked Python files and 18 JSON files.
- Full bundled business-package validator: 172 inventoried files, four databases, 73 original references, zero saved cross-store bindings. Validates hashes, SQLite integrity, history and logical-package agreement. Empty material/Requirement/SCD seed means zero bindings is expected, not a test of populated workflows.
- Native PDFium rendering of a generated one-page PDF, OpenCV/NumPy operation, lxml parsing and in-memory Excel write/read roundtrip.

## Not verified

- Browser rendering, four-pane editing, save/reopen, Requirement/SCD operations, collaboration conflict/replay/import/export, recovery and live SQLite locking.
- Full regression suite: `workbench/tests/run_checks.py` is excluded from the published repository.
- OCR: Tesseract and Poppler executables are absent from the diagnostic process PATH; no OCR readiness is established.
- Frontend rebuild: Node/npm absent from PATH. Bundled assets are included for normal operation.
- External retrieval and AI calls were not run. No automation was enabled.

## Local changes and next checkpoint

Installed uv inside `workbench/runtime/cache/tools/python/bin` and component dependencies only inside their declared virtual environments. Installation used a process-local PATH addition for uv. No global packages, registry changes, source-code edits or Git commits.

An interrupted seed-import receipt and partial prepared files remain under `workbench/runtime/backups/initial-import`; preserve them. Restoration explicitly supports same-package retries. No completed layout marker exists.

Recommended next checkpoint: use a short checkout path outside OneDrive (for example `C:\work\aquaculture`), recreate component environments there and repeat initial restore/start, followed by browser and business-workflow checks. Do not copy virtual environments. A system-wide long-path setting change is an alternative that needs a separate decision; it was not performed.

Detailed diagnostic results: `windows-smoke-results.json`. Reproduction script: `windows_smoke.py`, run with the System2 interpreter. Sandbox network/temp-directory access errors were separately retried with ordinary Windows permissions and are not classified as application defects.
