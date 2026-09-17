# Windows fixes promoted to the shared product

Date: 2026-09-18. Windows source: `d1e8aab6059f4c51031fb0616958502b0a31501f`. Product integration: `2458352`. Development base: `6808e30`. The user explicitly authorized promotion to `main`, local Mac synchronization and publication of the updated `developing-only-jay` branch.

## 1. Integration

All 27 Windows-changed product files are retained: native SQLite URI conversion, short seed staging and atomic-copy names, Windows System2 time-zone dependency, current-store health probes, prioritized reentrant operation serialization, idle queue hints, persistent owning component processes, separate immutable material computation, non-overlapping polling and reduced interpretation readbacks. The extra product commit corrects runtime diagnostics for persistent workers and identifies `main` as the common Windows/macOS branch.

The older uncommitted Mac idle helper overlapped `Collaboration.tick`. Its exact source and tests were archived under the earlier performance report; the Windows implementation is now the sole active scheduler. Development documents, tests and history remain on Jay's branch. No database schema change, seed reimport, source overwrite or runtime reset was performed. `developing-win` is retained as the incoming reference rather than deleted.

## 2. Verification

- Workbench suite: **331 passed** in the declared application environment.
- Frontend suite: **374 passed**, including selection synchronization and preservation of newer edits when a save returns a committed document.
- Focused System2 suite: **51 passed**, including real HTML parsing, worker process reuse/restart, Unicode storage routing and concurrent manual edits during separate computation.
- Two isolated peers using real owning component adapters: initial restoration, source/material/Requirement/interpretation Collaboration round trip, Git update preservation and restart readback passed on **macOS**.
- Full owning-store integrity and source-binding verification passed. Live Source register retains **88** sources; **73** source-version records, **137** governance operations and **240** governance history entries remain.
- Live browser read checks passed for Source register, Material review (38 available sources) and Archive (0). These checks did not create development material records in the real workspace.
- Updated Mac service started at `http://127.0.0.1:62742/`; its runtime snapshot reports no source changes since startup and correctly identifies persistent workers.
- Product/development file boundaries and naming are checked separately before publication. The authorized initial-data ZIP is unchanged.

The first isolated reuse of older test fixtures exposed missing `snapshot`/`component_pool` collaborators, the old one-second export interval expectation and a selection stub that never opened its interpretation. Tests were updated to model the new interfaces and five-second interval, without changing business assertions. Additional checks cover the new response and worker paths.

## 3. Preservation and limits

Before updating the local checkout, the service was stopped through its normal API and a verified recovery package was created at `workbench/runtime/backups/windows-sync-20260918-before`: 190 data/support files, 709 code files and six retained stores. The four business databases plus private configuration, 11 protected files in total, are byte-identical before integration and after restart/read checks. Private configuration bytes and the recovery package remain local.

Evidence: [verification.json](verification.json), [Workbench tests](workbench-tests.txt), [frontend tests](frontend-tests.txt), [material tests](material-tests.txt), [Collaboration integration](collaboration-tests.txt), [workspace integrity](workspace-integrity.json).

Windows responsiveness is reported fixed by the user. This task ran native macOS checks; it did not rerun Windows, real AI, OCR, large-document performance or every four-pane pointer interaction. No Windows timing claim is inferred from these Mac results.
