# macOS integration of the Windows compatibility changes

Date: 2026-09-14. Status: source integration COMPLETE; affected macOS checks PASS. Full System2 regression INCOMPLETE because of existing environment file-read delays. Normal Workbench parent was not restarted.

## Source and application

Integrated Windows commit `f0909e71dba5e66d9e9fccbd9ce958dbed2102b9` (parent `5f01f1a0611c207567a22e395ccbf33be9b3315f`) from `thejaytang/smarter-compliance-aquaculture`. The pinned source archive was main `95ca3903ea172357208ddc2f247b700c4a50d432`, which retains that executable code. Commit content and the Windows report establish repository provenance; physical-device identity was inferred from the user's context, not independently authenticated.

All 62 selected paths were checked against the local base before application: 50 unchanged-base replacements, 10 additions and two local documentation merges. No conflicts. All 52 existing targets were backed up in `source-before/`; new helpers were installed before their callers. All 62 resulting SHA-256 hashes matched the prepared merge. Subsequent local acceptance notes only update the four state documents. [Application manifest](sync-manifest.json) records exact targets and hashes; [final verification](final-verification.json) records the final state.

The local cross-platform design section in AGENTS.md and the design/full-backup completion paragraphs in PROJECT_STATE.md remain preserved. No runtime database, saved draft, source original, workbook, environment version or UI asset was selected for source replacement. No push, business review action or service restart was performed. Existing workers may load updated code on their next invocation; the already-running parent has not been verified as loading this revision. A future clean normal-service start is the activation boundary.

## macOS verification

Candidate checks used each owning component's existing Python 3.12.12 environment, isolated data and temporary ports on Darwin arm64. Published Windows results remain separately attributed to [the Windows report](../windows-compatibility-20260914/RESULTS.md).

| Check | Locally observed result |
| --- | --- |
| System1 full regression | 168 passed |
| Workbench full regression | 209 passed |
| Frontend state regression | 238 passed |
| System2 affected contracts, material/review state, SQLite and memory | 88 passed, 1 Windows-only skip |
| System2 six historical Requirement test modules | 95 passed after restoring fixtures |
| System2 final expanded attempt | 670 passed, 1 skip before interruption; no reported test failures; incomplete |
| Applied-source SQLite lifecycle checks | 1 System1 and 1 Workbench passed |
| Applied-source System2 memory and SQLite checks | 5 passed, 1 Windows-only skip |
| Applied-source native macOS port handling | occupied-port fallback and close/rebind passed using temporary state |
| Applied-source native macOS memory query | passed; positive resident-memory value |

Rows overlap and must not be summed as unique test counts. Logs and native JSON results are in [validation/](validation/). Passing checks establish no observed regression within these affected paths, not universal Mac acceptance or a new Windows/Mac reviewer round trip.

## Test-environment diagnosis and limits

The initial expanded source-only run reported 53 failures caused by missing ignored historical fixtures. Only 186 native-page/regulatory-ir JSON fixtures (233,257,404 bytes) were copied from local historical outputs into the isolated candidate. No production data was modified. The six affected modules then passed all 95 tests, eliminating all 53 observed failures.

Existing dependency reads also delayed imports. Two files were atomically rewritten using identical bytes, with original bytes backed up and unchanged SHA-256, mode and mtime: `referencing/__pycache__/_attrs.cpython-312.pyc` and `pydantic/_internal/_generate_schema.py`. [Repair record](dependency-storage-repair.json) records the hashes. No package installation or dependency-version change occurred.

The final full System2 attempt was stopped after 670 passes and one skip while importing unchanged dependency files; a native process sample showed Python FileIO readall/read, and an open-file snapshot identified a Polars bytecode file. The full suite therefore remains INCOMPLETE on this Mac. This observation does not establish a specific iCloud root cause or prove all local storage delays repaired. Starlette/httpx emitted its existing deprecation warning. The directly affected suites, native Mac memory/port behavior and applied-source persistence checks passed independently.

## Recovery

`source-before/` retains the 52 original target files. `merge-plan.json` lists the 10 added paths and every pre/post hash. Recovery must check for later local changes before restoring any target or removing an added file. This backup is a source checkpoint, not a business-database rollback. Existing human data and the previously completed full-workspace release retain their own recovery authority.
