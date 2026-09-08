# System1 Project State

Updated: 2026-09-08

## Documentation and launcher update | 2026-09-08

Maintained System1 documentation is English. The shared entry is `../Open Workbench.command`. The presentation layer refreshes Instructions C5 with this English filename during the next existing controlled save, preserving the workbook layout and business history. Both targeted presentation tests passed. This update did not save the production workbook or apply a business decision.

## Current checkpoint: browser entry and Excel instructions aligned | 2026-09-07

Decision: `CONTINUE`. The production workbook opens the updated English Instructions and exposes only Instructions, Categories and Source Register. Dashboard and Human Operation Desktop are `veryHidden`, retaining compatibility calculations, staging and history. Daily dashboards and human actions use the browser. The save layer maintains this layout so legacy maintenance paths do not reveal retired sheets.

Root README/AGENTS, System1 user/engineering guides, workbench guidance, cross-system navigation and program prompts are aligned. The overlooked Data/README was archived and replaced by [storage guidance](Data/STORAGE.md). The original plan is marked historical. Boundaries remain explicit: candidate registration is not connected to the browser, and saving a URL does not download it again.

The production file was updated under existing lock, backup and atomic-save rules. The 87 sources, 31 pending items, 70 originals and 44 named completed-history records were preserved. The complete read-only business projection, source/task revisions, original-file hashes and business cells outside Instructions were unchanged. All 1,264 formula caches were populated, with zero formula errors. Workbook SHA-256 at this checkpoint: `eff72dedd6cad269ea8b5adf09585f97dc4996404f24b804c95b3b8957ac4110`. The cache-checkpoint hash below identifies the preceding version.

System1 **79/79**, Workbench Python **17/17** and frontend **14/14** regression tests passed; Environment Doctor PASS. All 97 local links across 13 documents resolved. An isolated copy opened in native Excel and passed three-part layout inspection without a repair prompt. OfficeCLI font-order and legacy Dashboard DPI schema findings remain unresolved; that check was not claimed as passed. Exact backups, versions and validation boundaries belong to [this report](Code/runtime/browser-presentation-20260907/report.md). System2 was not modified and no human business decisions were submitted.

## Verified checkpoint: review saves and cache synchronization | 2026-09-07

Decision: `CONTINUE`. The user requested Excel cache synchronization whenever a human review is applied. Before atomic
publication, the save flow calculates all supported formulas and updates cell and chart result caches, preserving formulas,
backups, locks and review history. Unknown calculations or concurrent changes block the save. Each new System1 process invoked by the workbench uses this behavior.

All 1,264 formula results matched native Microsoft Excel recalculation in an isolated copy, with zero differences
and zero formula errors. Isolated review and chart tests verified immediate synchronization after changes. System1 regression **77/77**,
Workbench Python **16/16** and frontend **14/14** passed.

The current register received one cache-only synchronization under existing lock and backup protection. Business values,
original formulas and review history matched item by item. No human decisions were added and no sources were downloaded.
Before/after versions, backups and native Excel comparison belong solely to the [cache report](Code/runtime/formula-cache-20260907/report.md). The register hash at that checkpoint
was `defd3e5f702cd96209641b48f969aaf40ca57e658ce5b577c61f02f1f43fed39`;
cached effective selections for all 87 sources matched the production `read` interface.

System2 now consumes System1’s final effective selections and source revisions through the existing read-only bridge,
without duplicating source governance or requiring another eligibility review. See the parsing-side [source-intake contract](../system2/docs/contracts/source-intake.md).
Existing weekly QA, named decisions and unresolved issues remain. The human-review and platform-handoff records below describe their respective historical checkpoints.

Documentation entry points (2026-09-08): use [README.md](../README.md) and [AGENTS.md](../AGENTS.md) at the root of `05_Working area of requirements side/`, alongside all three systems. This system no longer has a separate entry contract. That README links directly to usage and design guidance. Old entry locations in historical records describe their original state. Integration state is `../PROJECT_STATE.md`; the shared launcher is also at the `05` root.

## Historical checkpoint: browser workbench handoff and validation | 2026-09-07

Decision: `CONTINUE`. Daily named review and the management dashboard moved to the workspace-root `Open Workbench.command`. The System1 workbook/Data remain the production source-state store. Human Operation Desktop is a `veryHidden` compatibility and history store. Interface, drafts and service validation belong to [Workbench state](../workbench/PROJECT_STATE.md).

Handoff verification: 87 sources, 70 registered originals, 26 pending sources; effective selections INCLUDE 38, PENDING 25, EXCLUDE 24. Named history contained Ana 20, DR 22, plus one each for Jay and Jokic; Ana. All 68 local regression tests passed; Environment Doctor PASS. The former Dashboard helper-column contract failure was resolved. The import checkpoint’s 61/62 result and Excel operation entry below describe that earlier state only.

All workbench write tests in this round used isolated workbooks. No production review decisions, original downloads or Full Source Check occurred. The verified production workbook fingerprint was `318ca627355911124c090f47830e75a01ea0f850ccb66e6893b9afc5e27321e5`.

Subsequent reconciliation confirmed all 42 rows in colleagues’ original Excel matched production history field by field, with no additions or omissions. The workbench now displays original conclusions, notes and remaining pending reasons. The production workbook was unchanged. See the [review synchronization report](../workbench/runtime/review_reconciliation_20260907/report.md).

## Historical checkpoint: importing colleagues’ reviews | 2026-09-07

Decision: CONTINUE. All 42 named reviews, Ana 20 and DR 22, were written to the production workbook. The 15 ACCEPT records preserve human INCLUDE intent, 23 REJECT records map to EXCLUDE, and four INCORRECT records remain persistent tasks. Corrected `retrieval_url` values for PA057 and CS004 were recorded without retrieving originals again; CS013 and CS014 still need links. Scores were unchanged, actual review dates are unknown, and the import date is 2026-09-07.

At that checkpoint: 87 sources, 70 stored snapshots and 26 unique pending sources, consistent between Leader and workbook. Reviewer names occupy the `operator` field in Human Operation Desktop column G. Completed rows remain hidden and retained; Source Register `manual_updated_by` records the named operator. Original review files, complete notes, mappings, backups and hashes belong solely to the [import report](Code/runtime/review_import_20260907/review-report.md) and linked evidence.

Fixed automatic queue refresh discarding human issues. HUMAN_REPORTED_ISSUE now persists until explicit human resolution and merges with other issues for the same source. Repeated isolated cycles and new regression checks passed, including 13 operator-journey tests. Of 62 final regression tests, 61 passed; only the existing Dashboard hidden-column contract failed. That old test hard-codes historical business counts. This round used actual reconciliation rather than replacing them with another fixed count.

Native Excel opened normally. Ana, DR and the operator header were checked, followed by calculation, save and close. Originals and prior review history were retained. No downloads or external models were used. Next work covers four link issues, unfinished scoring and licensed standard originals. Completed import does not mean all sources pass quality gates.

The following sections are snapshots of earlier checkpoints and do not replace the current state above.

## Historical validation: human edits synchronized across sheets | 2026-09-07

Decision: `CONTINUE`. Synchronization was checked through the actual `Routine Cycle` entry using isolated copies of the production workbook and Data. No production cycle, network download or business-code modification occurred.

- Copy PA006: entering `APPLY`, operator, explanation and `EXCLUDE` changed Source Register’s manual selection from `PENDING` to `EXCLUDE` and recorded the operator. The original task became `APPLIED`; history remained hidden and retained.
- Copy PA008: deliberately omitting the operator left Source Register at `PENDING` and the task at `WAITING_FOR_HUMAN`, with an explicit missing-operator message. It moved to the first Dashboard priority position.
- Unfinished tasks fell from 49 to 48, matching the Leader report; Dashboard priorities refreshed. Original formulas matched cell by cell, with automatic recalculation and full calculation on open enabled.
- After program save, Dashboard A5’s formula cache was empty. Before Excel reopened and calculated, cache-dependent previews could not prove refreshed metrics. This test did not include native Excel recalculation or visual chart acceptance.
- OfficeCLI confirmed retention of five sheets, Source Register’s 900 formulas and table, Dashboard’s 364 formulas and two charts, and the human-operation sheet. All 12 operator-journey tests passed.
- Production workbook SHA-256 remained `96aebadfbb42265c8a0e050cc0014006372b33711a5ed371a3ce0e61a7bf1fab`. The isolated run created one backup and did not invoke the downloader.

Evidence and reproduction: [result.json](Code/runtime/sync_smoke_20260907/result.json), [check.py](Code/runtime/sync_smoke_20260907/check.py). This directory’s workbook is test-only and contains simulated human decisions; it must not replace production. The existing Dashboard helper-column visibility issue remained tracked by the migration checkpoint below.

## Historical checkpoint: directory migration

Decision: `CONTINUE`. System1 moved into this directory with its internal relative paths and independent `Code/.venv` intact. Old paths in five environment launch files were corrected. Current integration state is in `../PROJECT_STATE.md`.

- Environment Doctor: `PASS`. Workbook and Data resolved correctly, no Excel lock was found, and automation was disabled and unregistered.
- Local regression: 61 tests, 60 passed and one failed. `test_dashboard_management_reporting_contract` failed the Dashboard R:V helper-column hiding assertion (`Code/tests/test_workbook_contract.py`).
- Workbook SHA-256 before and after migration was `96aebadfbb42265c8a0e050cc0014006372b33711a5ed371a3ce0e61a7bf1fab`. Migration and tests did not rewrite workbook contents; the contract mismatch already existed before migration. This round did not rewrite the workbook or weaken the test.
- Former root-level System1 state moved into this file. The 2026-09-04 tests, counts and workbook hash below are historical and cannot replace this validation.

Next experiment at that checkpoint: inspect Dashboard R:V visibility against the contract and decide whether hiding must be restored. Production source state and review history remain unchanged. Full Source Check and automation require explicit authorization.

---

# System1 Historical State

Last updated: 2026-09-04

## Current direction

Stabilise and validate System1 as the governed source-management foundation before expanding System2 requirement extraction or enabling unattended automation.

## Verified facts

- Current System1 architecture is `1 Leader + 3 bounded modules + Human Gate`.
- The project-local environment is `Code/.venv`, displayed as `SmarterComplianceSystem1`, using uv-managed CPython 3.12.12.
- Pinned dependencies are `openpyxl==3.1.5`, `portalocker==4.3.0`, and `tzdata==2026.3`.
- Environment Doctor passed on 2026-09-01 with relative paths, workbook availability, portable filenames, writable runtime paths, timezone, and intentionally disabled automation all passing.
- The complete local regression suite passed 61 of 61 tests on 2026-09-04. This includes 12 isolated end-to-end operator journeys and the Dashboard management-reporting contracts.
- The current workbook contains 87 source records, 44 operator decisions of `INCLUDE`, 42 `PENDING`, 1 `EXCLUDE`, 70 stored snapshots, and 49 open human-operation tasks. These counts are a time-specific operational snapshot.
- A non-collection Routine Cycle completed on 2026-09-01 at 09:56 Europe/Oslo with business status `REVIEW`. `Discovery & Intake`, `Retrieval & Monitoring`, and `Governance & QA` all returned `PASS`.
- The current Leader report identifies `1 Leader + 3 bounded modules`, and the open operation count agrees at 49 in both the report and workbook.
- The Routine Cycle created `Requirement_Source_Registry_20260901_095607.xlsx` before controlled workbook updates. The current workbook reopened successfully, retained formulas, returned no formula-error matches, and preserved 101 operation-history rows: 52 `APPLIED` and 49 `PENDING`.
- Operator-journey tests now cover existing-source `APPLY` and `RETURN`, selection `INCLUDE`/`PENDING`/`EXCLUDE`, candidate `ACCEPT` and `REJECT`, human file intake, manual replacement and paywall recovery, Random QA `CORRECT` and `INCORRECT`, missing operator data, stale fingerprints, duplicate intake, Excel-open deferral, deterministic `NO_API` operation, and simulated `API_CONNECTED` success and failure.
- The operator tests found and repaired a real format-normalisation defect: `.html` intake files were previously converted to the invalid label `htmll`, so an accepted manual file could fail to become the current snapshot even though the task was marked applied.
- An optional provider contract now permits future search and assessment adapters to propose candidates and governed field updates. The current shared configuration remains `NO_API`; fake-provider tests verify that provider proposals cannot bypass `Human Operation Desktop`, and provider failure cannot overwrite current source state or stop the deterministic core.
- The production Dashboard was rebuilt on 2026-09-04 as a read-only, single-screen management overview. It shows formula-backed KPIs for 87 total sources, 44 included sources, 70 stored snapshots, 49 open human tasks, 8 retrieval exceptions, and QA 7/7 at 100%; it also contains a seven-category horizontal portfolio chart, a populated selection doughnut, retrieval and governance panels, and five priority tasks.
- Dashboard priority refresh now writes only `A36:F40`, orders `NEEDS_REPLAN`, `WAITING_FOR_HUMAN`, then `PENDING`, and places the oldest task first within each status. `days_open` is calculated from the program-owned `created_at` field.
- The pre-change recovery copy is `Code/runtime/backups/Requirement_Source_Registry_20260904_dashboard_before.xlsx` with SHA-256 `054341510fc104d49b34b6916e018aa16b00e49622c937cea4c1f5024ebc2fe0`. The rebuilt production workbook SHA-256 is `3c9c818d2638ab781d42cd85881556f576bd8b711d2f3e382162cab79781a04d`.

## Open issues

- Older Leader JSON reports identify `1 Leader + 5 specialist agents`; they are retained as historical audit evidence, while the latest report is current.
- Git still shows the old `Book1.xlsx` as deleted while the new System1 workspace is not yet tracked. The replacement boundary must be reviewed before any commit.
- The 49 open human-operation tasks are business review work, not a program failure.
- Full Source Check and unattended scheduling remain intentionally disabled.
- No real API adapter, credential, external discovery call, or model-quality evaluation has been completed. `API_CONNECTED` evidence currently covers only the local provider contract with fake providers.

## Current checkpoint

Checkpoint completed: Dashboard management-reporting redesign and regression acceptance.

Success evidence:

- Excel-open and process-lock checks pass.
- A backup is created before controlled workbook writes.
- Routine Cycle completes without a process failure.
- The new Leader report identifies `1 Leader + 3 bounded modules`.
- The workbook reopens cleanly and Dashboard, Source Register, and Human Operation Desktop remain internally consistent.
- Completed human-operation history remains retained and hidden.
- All supported human journeys complete in isolated Excel workbooks, with human notes, timestamps, visibility, source updates, file promotion, file preservation, and follow-up tasks matching the operating contract.
- Routine Cycle in `NO_API` mode does not call the downloader.
- Simulated API candidates and assessment suggestions remain pending until explicit human approval; unsafe program-field proposals are rejected.
- Dashboard helper columns `R:V` are hidden, gridlines are off, the saved zoom is 85%, and both native Excel chart objects are populated from formula-backed helper ranges.
- The Dashboard formula scan returned no formula-error matches, and the priority preview agrees with the open task queue.
- All 61 local regression tests pass without a Full Source Check, external API, or live network retrieval.

Decision after the run: `CONTINUE`. The deterministic System1 core, human workflow, and management Dashboard are locally operational. The optional provider boundary is safe enough for a future adapter experiment, but no real API capability should be claimed yet.

## Next useful experiment

Keep the 49 production tasks as the next business review queue. If API expansion becomes a priority, implement one sandboxed discovery adapter against the tested provider contract and verify authentication, rate limits, duplicate handling, source quality, and failure reporting before enabling it in Routine Cycle. Do not run Full Source Check or enable the scheduler without explicit authorization.

## Unified operators and weekly sampling | 2026-09-07

The user confirmed operator mappings. Production Source Register `manual_updated_by` and Human Operation Desktop `operator` now use full names: Weijie Tang 1, Ana Jokic 21, Daniel Restad 22 named-history records. Only identity fields changed; scores, decisions, notes, original import payloads and formulas did not. Backups and the [field-level identity audit](../workbench/runtime/english_ui_20260907/identity-migration.json) were retained.

Random QA is configured as MONDAY_WITH_CATCH_UP with five weekly items, triggered by the local review service itself and portable with deployment. No Codex or operating-system scheduled task was registered. Sampling uses currently included sources with no unresolved tasks. The workbook stores weekly batches and actual sample sizes; old monthly history remains. Five items were created for the current week, and a repeat created zero. Sources 87 / pending 31 / originals 70 / included 38. Human checks were unfinished; no 100% accuracy was claimed.

System1 regression 71/71 and Environment Doctor PASS. Business locks, Excel-open waiting, backups and `veryHidden` operation history remain enforced. No Full Source Check ran. Final fingerprints and task IDs are in the [data verification](../workbench/runtime/english_ui_20260907/final-data-verification.json). Workbench owns charts and the English interface; System2/3 integration still awaits their contracts.

Additional checks found and fixed Random QA corrective tasks being cleared by later task consolidation. QA failures now carry persistent `human_reported_issue`, preserving original notes, operator and QA evidence ID. They remain unresolved after another Routine Cycle and require explicit verification. Isolated bridge tests cover CORRECT replay, INCORRECT history retention, repeated cycles and explicit verification closure.
