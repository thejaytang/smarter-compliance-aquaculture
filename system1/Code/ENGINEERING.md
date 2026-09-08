# System1 Code | Engineering Guide

## Architecture

System1 uses one deterministic Leader and three bounded modules:

1. `Discovery & Intake`
2. `Retrieval & Monitoring`
3. `Governance & QA`

The Leader owns orchestration, the complete-run lock, persisted state, task consolidation, retry handoff, notification, and run reporting. Human-facing work is consolidated to one current task per source.

No search provider or AI API is configured. Discovery therefore processes `Data/00_Human_Intake`, the structured candidate inbox, duplicate checks, and coverage checks only. It must not claim autonomous regulatory discovery.

An optional provider boundary exists in `src/system1/provider_extensions.py`. A future search provider may propose candidates and an assessment provider may propose human-governed field updates. Provider output has no direct write authority: candidates and suggestions are validated and routed to the human gate, with `Human Operation Desktop` retaining adapter staging. Connected review actions use the browser; the dedicated candidate form still requires maintainer-assisted handling. The shipped configuration still runs in `NO_API` mode and includes no provider adapter, credentials, or external API call.

## Engineering structure

```text
Code/
├── config/
│   ├── config.example.json
│   ├── config.json
│   ├── schedule.example.json
│   └── schedule.json
├── deployment/
│   ├── requirements.txt
│   ├── register_schedule_macos.command
│   ├── register_schedule_windows.cmd
│   ├── setup_macos.command
│   ├── setup_windows.cmd
│   ├── unregister_schedule_macos.command
│   └── unregister_schedule_windows.cmd
├── scripts/
│   ├── (advanced maintenance scripts)
│   └── run_windows.cmd
├── src/
│   ├── system1/
│   │   ├── provider_extensions.py
│   │   └── ...
│   ├── leader_orchestrator.py
│   ├── human_operations.py
│   ├── manual_intake.py
│   ├── source_updater.py
│   ├── staged_pipeline.py
│   └── sync_run_state.py
├── tests/
├── runtime/
└── ENGINEERING.md
```

The retained numbered scripts are advanced compatibility and diagnostic entry points. Normal users use Open Workbench.command at the Requirement Workstream root (`05_Working area of requirements side/`). Old macOS menu launchers are archived under runtime/workbench_activation_20260907/retired_launchers.

## Environment contract

Use the shared [environment guide](../../ENVIRONMENT.md) for setup, interpreter selection and checks. System1 owns `Code/.venv`; its pinned dependencies are defined in [deployment/requirements.txt](deployment/requirements.txt). Setup scripts create this isolated environment with the prompt `SmarterComplianceSystem1`. They do not install Python itself, register a schedule or add credentials.

## CLI

These are maintainer interfaces. Daily browser decisions apply automatically; operators do not run `routine` after each review. `full` performs a network-enabled operational sweep and requires explicit user authorization.

Run from `Code` with `PYTHONPATH=src`:

```text
python -m system1 menu
python -m system1 routine
python -m system1 full
python -m system1 status
python -m system1 doctor
python -m system1 scheduled
python -m system1 register-schedule
python -m system1 unregister-schedule
```

`routine` uses `execute_collection = false`. `full` forces all modules and performs collection. `scheduled` checks persisted due keys and runs at most one due job, with Full Source Check taking precedence.

## Configuration

`config.json` contains only shared relative paths and portable operational settings: workbook and `Data` paths, runtime paths, timeout and byte limits, timezone, HTML-first format preference, authoritative-first language policy, eligible source states, folder prefixes, Random QA, and module intervals.

`schedule.json` contains schedule intent: `enabled`, routine and full-check times, timezone, polling interval, catch-up behavior, and notification preference.

Device-specific absolute paths exist only in the local `launchd` or Windows Task Scheduler record. They are not written to the workbook or shared source code.

## Scheduling adapters

These optional adapters schedule maintenance and retrieval, not the workbench review loop. The workbench itself checks for current-week Monday QA every minute while running, samples 5 eligible sources, records the weekly key and catches up only the current week. No Codex task or OS scheduler registration is required for that service behavior. Registration or Full Source Check still requires explicit authorization.

macOS registration creates a current-user LaunchAgent. Windows registration creates a current-user Task Scheduler task. Both launch a lightweight periodic runner that exits when no job is due, records successful due keys, catches up missed runs, avoids repeating a completed period, gives Full Source Check precedence, and defers on an open workbook or active System1 run.

Registration requires an existing `.venv` and `schedule.json` with `enabled = true`. Moving the folder requires unregistering and registering again.

## Module responsibilities

### Leader

Runs the human cycle, wakes due modules, re-reads findings, consolidates one current task per source, persists state, writes one JSON report, and produces a user-facing status. `REVIEW` is a completed business outcome, not a process crash.

### Discovery & Intake

Scans manual intake and the structured candidate inbox, checks duplicate identities and coverage gaps, and sends every candidate to the human gate. It does not assign a formal source ID before `ACCEPT`.

### Retrieval & Monitoring

Evaluates collectable `CURRENT` records, prefers complete official HTML over equivalent official PDF, downloads original formats, validates content, compares hashes, archives changed snapshots, and preserves the current valid file after failure. Paywalls become `PAYWALL_BLOCKED` and are never bypassed.

### Governance & QA

Evaluates selection fields, audits workbook-file consistency, creates at most one weekly Monday QA batch of 5 eligible sources, catches up the current week after downtime, and creates correction tasks for incorrect QA results.

## Workbook contract

Browser-mode workbooks carry the `system1-browser-workbench` keyword. `Instructions`, `Categories` and `Source Register` are visible; `Dashboard` and `Human Operation Desktop` are veryHidden compatibility/audit sheets. Excel opens on `Instructions`, which describes browser review, automatic application and weekly QA. `system1/workbook_presentation.py` owns that guide and presentation migration. `save_workbook_atomic` applies it before cache calculation on every controlled save; the guide version marker avoids unnecessary rebuilding. Business records, audit rows, formulas and charts are preserved. Unmarked legacy test workbooks keep their existing presentation. Normal decisions arrive through system1.workbench_bridge with a named actor, task/source revisions and a stable request ID. Source business state stays in the workbook.

`human_operations.py` applies task-type-specific validation, fills timestamps, checks source fingerprints, processes decisions, refreshes the hidden legacy Dashboard's five priority items for compatibility, preserves completed history, and maintains one current task per source. Dashboard priority follows `NEEDS_REPLAN`, `WAITING_FOR_HUMAN`, and `PENDING`, with the oldest task first inside each status.

## File and workbook safety

- `exclusive_process_lock` protects the complete Leader cycle.
- `system_lock` protects each workbook write and checks the Excel temporary lock.
- Controlled writes create a backup and use temporary-file replacement.
- Windows file occupation stops the run safely.
- Failure paths preserve current valid source files.
- Filename validation covers Windows reserved names, invalid characters, case-insensitive collisions, path length, and paths containing spaces.

## Environment doctor

`python -m system1 doctor` checks Python and dependency versions, configuration and relative paths, workbook and `Data`, Excel lock, timezone, runtime writability, Windows-compatible paths, schedule configuration, and scheduler registration state.

## Testing

The regression suite is local and does not perform a full network download:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Coverage includes selection, failure preservation, human decisions, stale fingerprints, consolidation, weekly QA (with legacy monthly history), schedule catch-up and idempotence, Windows path rules, workbook contracts, and atomic safety behavior.

`tests/test_operator_journeys.py` adds end-to-end simulations for every supported operator journey, manual intake and replacement, paywall recovery, Random QA, Excel-open deferral, deterministic `NO_API` operation, and fake-provider `API_CONNECTED` success and failure boundaries. See `tests/OPERATOR_SCENARIO_MATRIX.md` for the acceptance mapping. Fake-provider tests do not claim that a real API adapter, credential, or external service has been validated.

Platform acceptance additionally requires fresh `.venv` tests on macOS and Windows, a path containing spaces, Excel-open and concurrent-run deferral, schedule registration/unregistration, and folder-move re-registration. A full network sweep is an explicit operational run, not a routine regression test.

## Runtime state

- `runtime/backups`: recovery workbooks
- `runtime/inbox`: structured candidate handoff
- `runtime/logs`: updater events, Leader reports, scheduler state, and scheduler output

Runtime files are operational evidence. Do not edit them to force a business result.


## Browser adapter and validation

system1/workbench_bridge.py accepts JSON on stdin for read, artifact and apply commands. Workbook request markers/receipts support replay and staged recovery; task/source revisions reject stale pages. Partial assessments retain human findings. Workbench calls this module through System1's own interpreter.

tests/test_workbench_bridge.py validates score application, replay, partial findings, stale revisions, Excel locks, staged recovery and manual-file promotion using isolated workbooks. Dashboard tests compare live data and available formula caches, not historical fixed counts. The browser Dashboard reads adapter state, not the hidden Excel chart caches. Presentation tests verify migration and a later save after a legacy writer exposes retired sheets, preserving business cells, formulas, tables, charts and caches.

### Formula and chart cache synchronization

Every `save_workbook_atomic` now calculates the workbook's supported formula vocabulary before saving, writes cell and chart result caches into the temporary file, validates the ZIP, rechecks workbook modification time and Excel-open state, and only then promotes the file. Formula expressions, audit rows, locks and backups remain intact. An applied review therefore includes immediately readable workbook results; users do not have to open Excel to populate caches.

`system1/formula_cache.py` is a bounded local evaluator for the current System1 template: direct/cross-sheet and table references, IF/IFERROR, AND/OR, COUNTIF(S), COUNTA, SUM, MAX/MAXIFS, TEXT with `0%`, INT and TODAY. It does not execute arbitrary code, external links or macros. Unknown formulas, circular references and unhandled calculation errors stop publication. Changes to the workbook's formula vocabulary require corresponding supported behavior and native Excel verification; do not silently skip them or substitute prior caches.

Tests include review apply/replay, complete real-template cache coverage, preserved business values/formulas/history, chart changes after selection changes, and interrupted publication. The 2026-09-07 native Excel comparison and one-time production cache synchronization are recorded in [cache verification](runtime/formula-cache-20260907/report.md).

System2 consumes the existing bridge `read` command using its own adapter and System1's interpreter. It uses `effective_selection` and source revisions, and verifies registry/configuration stability. No source scoring or human decisions are duplicated downstream. See [System2 intake contract](../../system2/docs/contracts/source-intake.md).
