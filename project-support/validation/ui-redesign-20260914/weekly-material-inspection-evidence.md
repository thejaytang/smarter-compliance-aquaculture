# Weekly material archive inspection mechanics

Verified 2026-09-14 in isolated temporary stores. Candidate implementation: `candidate/workbench/src/local_workbench/material_inspection_schedule.py`.

## Ownership and activation

`MaterialInspectionSchedule(collaboration).run_due(settings, clock=None)` is an owning-workbench service operation, never a page-read operation. The service integration reads `workbench/runtime/material-inspection-settings.json` at most once per 60 seconds from the material worker; a missing file supplies `{}` and dispatch remains disabled. This change does not create that settings file or enable a normal business schedule. Reviewer installations cannot dispatch enabled schedules.

An explicitly authorized configuration must specify `enabled`, `timezone`, `sample_size` (1–100 materials) and a roster `assignee`. Sampling is deterministic weekly hash ordering over latest confirmed content archives, with full retained original scope per selected material. This is an explicit mechanical selection policy, not a statistical quality or coverage claim. Production activation and actual sampling size/assignee remain separate operational decisions.

## Durable behavior

The existing collaboration SQLite journal owns `material_inspection_batch`; the existing `MaterialQueue.create` owns task creation and its atomic task/receipt records. A batch is identified by local ISO year and week and freezes material IDs, archive revisions and stable request UUIDs before dispatch. A process file lock plus collaboration lock serialize dispatch. A restart after task creation but before batch progress persistence finds the durable task receipt and cannot duplicate that task.

The current week is the only catch-up target. Short and empty populations are recorded, completed batches cannot silently select later additions, and open checks of the same archived revision are reused. If an interrupted batch's frozen revision stops being the latest archive before task creation, that item is recorded as skipped; it is never silently rebound to a newer version. Other dispatch failures leave a resumable incomplete batch.

Archive bodies, source binding, confirmation and prior versions remain in System2. Dispatch creates Pending review tasks without editing those artifacts. Normal unchanged completion uses the existing explicit full-scope pass operation. Later revisions require the existing human finalization flow and can be selected independently in a subsequent week.

## Evidence

Command: owning Workbench interpreter with candidate `workbench/src` in `PYTHONPATH`, `unittest discover` against `test_material_inspection_schedule.py`.

Final targeted result: **8 tests passed**, comprising 7 schedule tests and 1 worker wiring test. The 15 existing MaterialQueue tests run separately in the complete 180-test workbench suite, which passed. Fixture reuse no longer imports the old TestCase into discovery. All stores and source projections are temporary synthetic fixtures. No normal source sweep, archive confirmation, scheduler configuration or real business task was performed.

New checks cover disabled no-read/no-task behavior; coordinator versus reviewer boundaries; explicit settings and aware clock validation; Oslo Monday/UTC Sunday ISO-week boundary; frozen source hash/revision/full-scope binding; archive retention; restart deduplication; interruption after durable creation; unresolved prior checks; current-week-only catch-up; stale frozen revision skip; empty/short populations; unchanged explicit pass and later finalized revision selection with old archive retention.

Service-worker invocation is merged and its disabled default, rate limit and reviewer exclusion are tested. These tests establish dispatch and queue behavior, not normal schedule activation, Windows execution, full production acceptance or actual statistical inspection quality.
