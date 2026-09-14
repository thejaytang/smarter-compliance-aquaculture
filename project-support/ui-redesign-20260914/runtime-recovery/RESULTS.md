# Reviewer-switch loading and English file input

2026-09-14 follow-up to the user's loading failure and Chinese file-button report.

Observed: normal PID 45944 remained listening. Initial health read timed out; a later direct loopback health read succeeded. /api/state returned 200 in 8.45 s. Chrome progressed from Loading workbench to Opening materials. A sampled material-service child was blocked inside Python import readall; its open file was openpyxl/workbook/__pycache__/_writer.cpython-312.pyc. The byte-length read succeeded, but the import readall remained stuck. The exact generated cache was retained here and regenerated from its existing Python source. An openpyxl import then completed. No database, original, library source or source registry was restored/rewritten.

Authority check: system2/intake/system1.py uses governance_db to select the SQLite bridge branch; workbook read/version calls are bypassed in that branch. However intake/registry.py imported openpyxl eagerly even for database callers. That import now occurs only within legacy read_registry. MaterialService import/listing succeeds with all openpyxl imports prohibited by a fresh-process import hook. Existing database handoff tests prove a malformed derived Excel file has no effect and logical DB version changes are guarded.

Validation: 14 targeted System2 environment/handoff tests passed using the owning environment. 5 source UI checks passed. A broader source/parser run was stopped after 36 completed cases because an unrelated cache read stalled; it is not reported as passed. The initial broad run was also stopped; disabling plugin autoload alone did not resolve the broader test stall. No full dependency-repair claim is made.

The Original file field now uses an English page button and live filename status, retaining the hidden native input and selected File object. Actual normal Chrome displayed Choose file / No file selected. No file was uploaded. Current user source form was empty before reload; no human decision or actor was changed by these checks.

The exact cause of all local filesystem stalls is not established. This repair removes Excel import from the database material navigation dependency path. It does not claim that the user's actor mutation itself was faulty or that a database record was lost. Normal code remains loaded; component workers import the modified module on their next invocation. changes.json records this follow-up delta separately from the prior delivery, whose promotion hashes are historical.

Final normal-browser verification: switching from Sources to Materials completed and rendered Material review / 38, with active workspace controls and the material table. This confirms the normal material entry recovered; it does not claim a new normal actor mutation test.
