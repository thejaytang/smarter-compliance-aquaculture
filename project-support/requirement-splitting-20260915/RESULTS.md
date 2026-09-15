# Manual requirement splitting: implementation and activation

Date: 2026-09-15. Scope: the user's whole-passage, outside-in manual splitting workflow in the existing Requirements pane.

## Delivered behavior

Whole saved text blocks enter separate source-bound sessions. Users split outer units and establish relationships before assigning exact original spans to the fixed fields. Recursive groups support exact `k` or inclusive `[min,max]` over direct children. Existing requirement links resolve real unit IDs under extracted headings. Every applied step is saved with revision checks, replay protection and restorable history. Completion of splitting does not confirm or archive a material.

The maintained [user guide](../../workbench/docs/manual-requirement-splitting.md) owns the format, workflow and storage contract. [Code manifest](code-manifest.json) identifies the delivered source files.

## Validation

| Check | Observed result | Evidence |
| --- | --- | --- |
| Full frontend regression after final UI changes | 245 passed, zero failures | [Log](frontend-final.log) |
| Full Workbench backend regression | 217 passed, zero failures | [Log](all-backend.log) |
| Focused backend rerun after final label changes | 8 passed | [Log](backend-final.log) |
| Served module import graph | Passed | [Log](routes-tests.log) |
| Design detector | One pre-existing runtime-populated PDF region image warning; no new-module finding | [Report](design-check.json) |

An actual browser run against isolated synthetic material at `127.0.0.1:58731` exercised whole-passage intake, two outer units, exception linkage, exact Subject/Modal Verb/Main Verb/Object spans, two conditions in a nested range group, exception fields and completion. The material remained revision 1 and unreviewed. Restart and reopen retained the work. A second Chapter 3 requirement was created, found by chapter text and linked by its actual ID into Chapter 2 conditions. Linked source details were displayed. [Browser evidence](browser-evidence.json) records the sessions at the completed cross-reference checkpoint; subsequent fixture reopening changed only its splitting phase. A 1280-pixel browser screenshot was inspected after the right-pane width correction. A session-loading race discovered during browser testing was fixed and covered by a frontend regression test.

All decomposition writes used the isolated fixture. Native Windows interaction, multi-day reliability and user acceptance were not measured by this run.

## Daily Workbench activation

The normal service at `http://127.0.0.1:62742/` was stopped through its protected API after confirming no active requests, then relaunched with its own environment. Five existing SQLite stores were backed up first. The first relaunch encountered the old service lock during shutdown; a retry after the old metadata disappeared succeeded. `activate.py` is a one-off preparation record, not an unattended recovery launcher.

[Activation evidence](activation.json) records PID 62303, startup source fingerprints, no parent source changes and automation disabled. The served JavaScript/CSS matched the files in the code manifest. Logical table/row hashes of all five stores matched their backups immediately after restart; SQLite backup byte hashes differ, so byte identity is not claimed. Later browser reads can create normal session metadata and empty requirement tables.

A read-only browser smoke check opened PA001 in the normal Workbench and visibly confirmed the new Whole source passage, Saved passages and step-by-step instructions in the Requirements pane. PA001 had no saved extracted text blocks, so Bring whole passage was correctly disabled. No real material was decomposed, confirmed or archived during this check.

## Remaining boundaries

- Splitting sessions are local to the selected reviewer. Existing collaboration/full-review ZIPs do not include the new requirement tables; the interface and guide disclose this limitation.
- Searches cover the reviewer's saved manual units. They do not synthesize IDs for unsplit chapters or convert legacy requirement data.
- Automatic extraction, ontology enrichment, machine learning and compliance evaluation remain disconnected.
- No Git commit, push, pull request or external model request was made for this change.
