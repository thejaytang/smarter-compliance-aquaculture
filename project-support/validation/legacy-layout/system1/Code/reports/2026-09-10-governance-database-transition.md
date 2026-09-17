# System1 normal database authority transition

Date: 2026-09-10. Decision: **CONTINUE** for the verified persistence transition. Overall Requirement Workstream acceptance remains incomplete. This follows the [isolated rehearsal](2026-09-10-governance-database-rehearsal.md), including its browser-discovered Keep pending failure and recovery.

## Verified normal transition

The normal configuration now selects `Code/runtime/governance.sqlite` through the relative `governance_db` value `../runtime/governance.sqlite`. The database owns source and operation state and append-only history. `Requirement_Source_Registry.xlsx` is a protected, one-way generated view. The exact pre-migration workbook remains the immutable `governance-migration-input.xlsx` companion; its SHA-256 is `8adfb864c0e8c9502fb773c4880feb9603bf395dd281215e276fbeb64670c806`.

The normal service was verified by root, instance and process identity, checked for unfinished requests, stopped gracefully and checked for surviving normal writers. Service and System1 locks protected the transition. Before changing configuration, a stopped-write recovery package preserved the original workbook/configuration, all 73 managed source files, source logs, assessment/Leader databases, Workbench database and System2 workflow database. Each copied database's complete table contents were compared with its original. Import and backup validation preceded activation.

| Preserved item | Verified result |
| --- | --- |
| Sources and operations | 87 sources, 126 operations; all business values and positions match |
| Human state | 30 pending tasks and 96 historical operations; all existing source/task guards match |
| Selection | 38 INCLUDE and 24 EXCLUDE, unchanged; access/paywall matters remain pending |
| Originals and version links | All 73 managed files retain bytes/paths; 70 verified STORED version links |
| Database history | 213 import entries preserve all source and operation records; normal revision remains 1 |
| Downstream continuity | All System2 workflow tables unchanged after explicit schema-2 reconciliation and resumed polling |
| Related history | Assessment and Leader tables unchanged; Workbench business tables unchanged, with only ordinary browser sessions added |
| Normal engineering decisions | Zero; no isolated PA006 removal or SB001–SB003 test decisions were copied into normal state |

The normal service resumed on retained port 62742, process 36269, instance `6FHOShMpZ-FtCFkpzh2RYLh54vOzRhnK` at this checkpoint. Health root/instance matched. The actual browser showed Queue 30, SB001's authorised-original task, unchanged PA006 Pending, and `Decisions saved · Excel synchronized · saved revision 1 · Excel revision 1`. The source download link produced an actual browser download. Review-history navigation was invoked; the normal history count and identities were independently verified through the owning adapter/database. No new source decision was submitted on the normal UI.

The normal source Excel SHA-256 is `2ca52ed1dff462772039b151bb3f10ba879034ed25a67e04ba7bb404a8f20376`. Complete readback matched database business values and confirmed sheet/structure protection. A byte-identical local copy opened in native Microsoft Excel without a repair prompt; Instructions visibly showed revision 1 and the database/Excel rules. Source Register showed PA006 still Pending. The copy was closed without saving.

An additional controlled System2 workbook synchronization returned the current artifact (`d5c40144bb37c9553cb8ca1076bccdf4272975e77806ec095897a0b5f09b683c`) in 0.655 seconds and preserved every workflow table. Inspection initially suggested that source-only changes lacked an export trigger. Reading the complete scheduler corrected that hypothesis: its existing 60-second full check captures such changes even without review events. The remaining issue is the status window before that periodic check: hot status compares review-event/policy versions without separately comparing source authority. Record this limit; this checkpoint did not add another scheduler or claim immediate source-change status detection. Native visual acceptance of the complete optimized System2 workbook remains separate.

## Decision latency and isolation

Daily operations now build a lean business view from a fresh database snapshot. Only immutable template metadata is cached; mutable source and operation values are never reused between transactions. Full presentation reconstruction belongs to the background Excel writer. Source-record and manual-intake hash reads use the owning database directly.

Six fresh complete isolated copies were compared on Apple M4, 16 GiB RAM, macOS 26.6.2 arm64, project CPython 3.12.12, with the normal/pilot background services also present. Both comparators used direct source reads, the same frozen inputs, actor, request ID and domain clock; immutable metadata caches started cold. These unprofiled measurements isolate the business-view change, not every earlier optimization.

| View | Three observed apply durations, seconds | Median |
| --- | --- | --- |
| Full presentation | 2.2104, 2.2930, 2.3529 | 2.2930 |
| Business view | 1.0823, 1.0644, 1.0521 | 1.0644 |

Business values, revisions and history matched across modes, excluding actual execution timestamps. A subsequent isolated workbench SB003 Keep pending request took 1.5772 seconds from persisted creation to applied receipt and retained Queue 29. Its client timing report initially used a wrong timestamp field after successful application; only persisted receipt timing was recovered, without repeating the decision. Three samples per mode and one HTTP receipt do not establish p95, a general service budget or measured human effort. The proposed two-second application target remains an engineering proposal for broader measurement.

## Recovery and diagnostics

`Application.close` now waits for all local writer threads, including both output workers, before completing shutdown. A blocked-writer test verifies this behavior. Existing subprocess timeouts still bound adapter work; long jobs can delay a safe exit.

Environment Doctor now checks the configured database read-only, integrity, schema and the immutable companion hash. A missing database is not created or replaced from Excel. Missing/changed companions fail. A missing derived workbook or open Excel is a synchronization warning in database mode, while the legacy authority keeps its former protections. The new recovery test exposed an existing macOS `/var` versus `/private/var` path mismatch; resolving the configuration path fixed the diagnostic. The failed run remains retained.

Recovery must preserve post-migration decisions. The isolated database was backed up again after its engineering decisions at revision 10; all restored table contents and effective snapshots matched, including new history. For an actual recovery, stop and drain writers, preserve the current failed state, verify a database backup and its matching immutable companion, retain source files and the related assessment/Workbench/System2 state, restore under owning locks, then regenerate Excel and recheck guards. Do not remove `governance_db` or restore the old Excel as authority after new decisions. An older backup is insufficient when newer valid decisions are absent; retain and reconcile that newer history before resuming. Runtime is excluded from Git, so a repository clone alone cannot restore this live authority.

## Validation and remaining failures

- System1: 107 regression checks passed in 18.724 seconds after the diagnostic path correction. Workbench: 25 passed, including shutdown drainage. System2 controlled source/intake checks and a fresh full 691-case suite passed with one skip (690 passed); explicit normal reconciliation preserved every workflow table. The fresh log is [`system2/runtime/governance-transition-regression.txt`](../../../system2/runtime/governance-transition-regression.txt). Twelve updated documents passed 235 local-link checks before this evidence link was added.
- Normal Environment Doctor passed. OS maintenance/retrieval scheduling remains disabled. Existing service QA history was preserved; the new 5 System1 / 20 A / 5 B rules were not activated.
- OfficeCLI still reports exactly the same 22 errors on baseline and normal output: two zero-DPI attributes, one sheet-view selection structure error and 19 font metadata errors. Native opening does not erase these findings. Source Register's long filenames still clip in fixed row heights. Export formatting acceptance therefore remains open.
- No source retrieval, source-discovery expansion, external model, new scheduler, publication, commit or push occurred.

Next: fix the bounded generated-Excel defects and source-version status window without altering immutable input/business state; continue the separate A scan/cross-page repair and independent reference gates, then configurable provisional B subdivision and stage-specific monitoring. Independent reviewer labels, separate calibration/held-out samples, user release thresholds, human workload and collaborator B decisions remain necessary. This transition is not evidence of source-fidelity or Requirement accuracy.

## Evidence ownership

The local recovery/evidence directory is [`Code/runtime/governance-transition-20260910`](../runtime/governance-transition-20260910). Its `before.json`, `prepared.json`, `activation-checks.json`, `activated.json`, `system2-reconciliation.json`, `live-start.json`, `normal-output-readback.json`, `post-decision-recovery.json`, `environment-doctor.json` and regression/Office logs retain the exact checks. `Code/runtime/governance-migration/transition.py` and `activate.py` record the performed one-time procedure; they are not repeatable import commands for an already active database. The latency comparison remains in [`workbench/runtime/governance-db-pilot/lean-adapter-comparison`](../../../workbench/runtime/governance-db-pilot/lean-adapter-comparison) and `lean-live-latency.json`. These local artifacts are not automatically included in shared repository distributions.
