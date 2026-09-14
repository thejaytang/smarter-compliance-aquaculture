# System1 | Source Management

Current browser collaboration: save source ratings, field corrections and issue findings as personal proposals in the material workbench. Export or inspect the personal submission; Weijie Tang explicitly adopts it into the governed source store. A saved proposal is not an effective source decision. See [offline workflow](../project-support/design/offline-human-review.md). Earlier direct-operation descriptions below remain relevant to the owning compatibility/audit mechanism, not a bypass of this personal-adoption workflow.

## Current two-stage workflow | 2026-09-09

Open the shared launcher and select a named reviewer. System2 → Pending review shows real jobs; choose an INCLUDE source and click Start processing. Confirm full-text coverage and content/structure before classifying Requirements, context and exclusions. Use source evidence, corrections, split/merge or missing-content supplementation where needed. Save draft is not acceptance. Include reviewed content to reopen an earlier result. Pause is checkpoint-based; Request reprocessing preserves the old generation and invalidates its deliveries.

Confidence settings owns all thresholds, initially 95%. Uncalibrated results require manual review regardless of threshold. Raising thresholds reopens affected machine results; human decisions/drafts remain protected. Optional assistance is disabled without explicit configuration. System1 Machine assessments shows evidence-supported five-dimension proposals and preserves named human decisions.

System2 Weekly checks samples machine-accepted outputs. System3 Incoming requirements displays incremental deliveries and source completeness; semantic processing is not connected. Original HTML is a script-free text view, PDF opens its registered full original, and XLSX supports paged cells, formulas/caches, hidden state and merged-region metadata.

See the [current workflow contract](../system2/docs/contracts/two-stage-review.md) for authority, operations and compatibility. Older dated integration/demo descriptions below are historical; they do not replace this workflow.


System1 maintains governed source identities, authorised original files, retrieval and selection state, human decisions and weekly source checks. Its business-state store is the configured `Code/runtime/governance.sqlite`; `Data` retains managed originals and `Requirement_Source_Registry.xlsx` is a protected generated snapshot. The browser workbench is the daily review and Dashboard interface.

Start with the [Requirement Workstream README](../README.md). Current evidence belongs to [PROJECT_STATE.md](PROJECT_STATE.md), engineering details to [ENGINEERING.md](Code/ENGINEERING.md), and Agent rules to the [workstream contract](../AGENTS.md).

## Daily source workflow

1. Open the root workbench launcher and select Ana Jokic, Daniel Restad or Weijie Tang.
2. Enter **Source Management System → Pending review**. The source/task list opens an independent source detail workspace. **Source records** includes included, pending and excluded records; **Review history** retains previous decisions and actors. Source review does not require a material or three-pane editor.
3. Inspect source identity, links, original availability, ratings, provenance, applicability and the specific listed reasons. Open evidence only as needed. Enter field corrections, a selection proposal and an evidence note. A low rating proposes EXCLUDE; five high ratings propose INCLUDE, subject to all owning source gates. Missing or invalid originals remain pending.
4. **Save progress** retains personal work. On the coordinator workstation, **Review and apply** shows the proposed review and estimated effective state; **Confirm and apply** records the contribution and applies it explicitly. Other reviewers return saved proposals for coordinator adoption.
5. Verify reported problems individually. **Report a source problem** adds a named personal report; main adoption creates a specific follow-up. Check only source tasks whose entire listed conditions were examined. Ratings cannot close unrelated tasks or later issues.
6. Use each task's dedicated controls: explicit retrieval retry, authorised original upload, candidate accept/reject/defer, replacement accept/reject/defer, or source inspection Correct/Incorrect. Only the selected task executes. A failed replacement preserves the retained original; Incorrect inspection results generate follow-up work.
7. From a current or historical source, **Request another source review** creates a new pending record with a reason. Earlier decisions are preserved. Version conflicts require fresh comparison; uncertain retries retain the same request and proposal.
8. **My submissions** selects multiple saved source, task, material and inspection results for one local ZIP. Import creates pending entries only. Source-only comparisons use **Submission inbox** here; task/inspection results use **Task results**, where every applied choice has its own receipt. Candidate registration and original replacement are coordinator actions, never import effects.

The named reviewer list identifies people on trusted local machines; it is not password authentication. A returned task whose common version has changed cannot close the current task. Source inspections do not establish material content acceptance. The [collaboration contract](../project-support/design/offline-human-review.md) owns the full scenario and package rules; [current workstream state](../PROJECT_STATE.md) identifies what is loaded and verified.

The remaining workbook sections document the protected generated view and compatibility mechanisms. They are not an alternative daily decision-entry route.

## What the workbook contains

Excel opens on `Instructions`. Four sheets are visible:

- `Instructions`: this browser workflow, source rules and recovery guidance.
- `Categories`: program-maintained classification and dropdown reference values.
- `Source Register`: the generated source register. Submit changes through the browser.
- `Machine confidence`: source-bound confidence values, calibration state and evidence identifiers.

`Dashboard` and `Human Operation Desktop` are **veryHidden** compatibility sheets. The browser Overview replaces the old Dashboard. The operation sheet is a generated view of database operations and item-level audit history. Do not delete either sheet, unhide them for daily operation, or alter their formulas and records. Every controlled browser-mode save enforces this presentation.

The background writer refreshes workbook formula and chart caches from a consistent database snapshot. The browser reads current System1 state directly. Calculation, revision or file-lock failures prevent Excel from being reported synchronized; already saved decisions and history remain available.

## Source rules and outputs

- Prefer complete official HTML over an equivalent official PDF; preserve the published format and authoritative language. Among equally authoritative versions, prefer English, then Norwegian, then Other.
- `official_url` identifies the official source or landing page. `retrieval_url` identifies the retrievable original.
- Retrieval and selection are separate. `SUCCESS`, `FAIL` and `PAYWALL_BLOCKED` describe retrieval; `INCLUDE`, `PENDING` and `EXCLUDE` describe effective source selection. Inclusion requires a valid current snapshot and completed governance gates.
- Restricted material requires an authorised copy. Never bypass a paywall or replace an original with a convenience conversion.
- Failed retrieval and replacement retain the valid current file, failure evidence and unresolved task.
- One source can have several unresolved issues, consolidated into one current source task. Completed decisions and the latest updater remain traceable.

The output is a controlled source package: source identity, original-format files, versions, hashes, retrieval state and governed selection. It is not an extracted Requirement dataset or a legal-compliance verdict. System2's explicit local intake reads this effective source state through the existing read interface; completed source selection is not re-reviewed downstream. Opening the workbench does not start parsing.

## Automatic processing and weekly QA

The running workbench processes submissions and checks once per minute for the current week's QA batch. Every Monday in `Europe/Oslo`, it samples 5 eligible items per connected system. System1 selects effective INCLUDE sources without unresolved tasks. Fewer eligible items means a smaller recorded sample, including an empty batch when none are eligible.

After downtime, the service creates only the missing current-week batch. The Dashboard plots the most recent five weeks; only completed batches with named applied decisions contribute accuracy points. Incomplete or unconnected weeks stay blank. See the [workbench guide](../workbench/USER_GUIDE.md) for the calculation and connection status.

This scheduling belongs to the review service, not Codex or a personal account. Closing the browser page leaves the service running; `Exit workbench` stops it. Login autostart and a permanently running system service are not installed.

Separate operating-system schedules for maintenance and source retrieval are optional, require explicit setup and Environment Doctor validation, and are not needed to apply browser reviews or generate weekly QA while the service runs. Their advanced configuration is in [ENGINEERING.md](Code/ENGINEERING.md). Merely launching or viewing the workbench never starts a Full Source Check or downloads.

## Setup and maintenance

Use the combined project, including the workstream-root launcher and sibling `workbench` directory. Copying only this System1 folder does not provide the daily browser interface or the project operating contract.

- The declared project environment uses Python 3.12. Microsoft Excel is for workbook inspection and native visual acceptance, not daily review.
- System1 uses its own `Code/.venv`; the workbench uses a separate `.venv` and standard-library runtime. Follow the shared [environment guide](../ENVIRONMENT.md) for platform-specific setup and Environment Doctor.
- Recreate both environments on a new computer; copied environments are not portable installations.
- The normal root launcher is validated on macOS. The retained Windows maintenance menu does not establish acceptance of the browser launcher on Windows.
- Shared paths stay relative. Keep `Requirement_Source_Registry.xlsx`, `Data` and `Code` together. Do not add credentials or device-specific scheduler records to shared files.

Maintainers retain CLI operations for routine intake, status, environment checks and explicitly authorised full source checks. Candidate intake and exceptional recovery use the compatibility adapter with the same human-authority, lock, backup and audit rules. The retired macOS menus are historical artifacts, not alternative daily entry points.

## Safety, recovery and handoff

System1 backs up controlled database writes, including the immutable migration companion, and separately validates a temporary Excel snapshot before replacement. Excel-open detection, complete-run locks, source revisions and request IDs protect against concurrent or repeated application.

- If Excel reports a repair prompt, decline automatic repair and preserve the file. Ask the maintainer to identify a verified backup, restore it under the normal locks and run Environment Doctor.
- If Excel synchronization is waiting, close Excel; the service retries automatically. Do not edit or save business decisions into the generated workbook. Do not start a second writer.
- Use the workbench for retrieval failures, corrected links and authorised originals. A saved URL does not prove that an original has been retrieved or verified.
- Preserve `Code/runtime/backups`, logs, source snapshots, completed reviews and weekly QA history. Workbench's separate SQLite and pending uploads also contain persistent operational evidence.

`Code/runtime/governance.sqlite`, its `governance-migration-input.xlsx` companion, assessment history and Workbench receipts are persistent business data. Other runtime archives and files under `Others` are retained evidence. Never remove the database setting to restore an old Excel authority after new decisions; see the [verified recovery procedure](Code/reports/2026-09-10-governance-database-transition.md#recovery-and-diagnostics). `presentation` contains shareable visuals; verify their dates and labels before treating them as current facts. Never overwrite reference or customer-confidential material as part of cleanup.

Before sharing, close Excel and active writers, retain the necessary data and operational history, review confidentiality, and require fresh local environments and Environment Doctor on the recipient computer. A standalone distribution needs package-root documentation derived from the combined project contract. Scheduler registration remains an explicit deployment choice.

Source folder conventions: [STORAGE.md](Data/STORAGE.md).

Overall ownership and handoff boundaries: [README.md](../README.md).
