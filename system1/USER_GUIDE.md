# System1 | Source Management

System1 maintains governed source identities, authorised original files, retrieval and selection state, human decisions and weekly source checks. Its business-state store is `Requirement_Source_Registry.xlsx` together with `Data`. The browser workbench is the daily review and Dashboard interface.

Start with the [Requirement Workstream README](../README.md). Current evidence belongs to [PROJECT_STATE.md](PROJECT_STATE.md), engineering details to [ENGINEERING.md](Code/ENGINEERING.md), and Agent rules to the [workstream contract](../AGENTS.md).

## Daily workflow

1. Save and close Excel, then double-click [Open Workbench.command](../Open Workbench.command) in the Requirement Workstream root (`05_Working area of requirements side/`). It starts the local service and opens the default browser. Reopening the launcher reuses the service.
2. Choose your name once: Ana Jokic, Daniel Restad or Weijie Tang. Switch reviewer when another person takes over.
3. Open `System1 → Pending review`. Select a source from the left queue and use its official link, retrieval link or original-file viewer to check the evidence.
4. Complete the action requested for that issue. The service applies submitted decisions automatically; there is no separate program run after each review.
5. Use `Review history` for completed decisions and `Overview` for the live Dashboard. Unresolved follow-up issues remain in `Pending review`.

The workbench uses English labels. Reviewer selection identifies the person on a trusted local computer; it is not password authentication. Full screen-by-screen instructions are in the [workbench guide](../workbench/USER_GUIDE.md).

| Review case | Operator action |
| --- | --- |
| Source assessment | Explicitly click H / M / L for each of the five dimensions. Light fill shows the previous score; dark fill shows the current choice. The last rating submits automatically. Existing human issues still need explicit verification. |
| Wrong or incomplete URL | Open the associated links, enter the correct URL and save. This records metadata; it does not download or verify a replacement original. Complete the issue verification separately when supported by evidence. |
| Missing original | Choose an authorised PDF, HTML or XLSX in the workbench. After format checks, confirm source identity, completeness and permission, then submit. The existing valid snapshot survives a failed replacement. |
| Unresolved question | Save a note or keep the source pending with a reason. A draft is not a completed decision. |
| Source outside scope | Use the removal action and record the reason. History and retained source evidence are preserved. |
| Weekly random check | Compare the record with its original, then choose `Correct` or add a note and `Report an error`. An error creates follow-up work. |
| New source candidate | A dedicated browser candidate form is not connected yet. A maintainer must process the candidate through the compatibility adapter with a named human ACCEPT decision. Ordinary ratings cannot accept a new source. |

`Submitted`, `Applying` and `Waiting` do not mean the decision has been applied. If Excel is open or another writer holds the lock, the request waits and resumes automatically. An outdated task must be reloaded and reviewed against its current version. Use `Retry submission` for an unknown submission result so the request keeps its original ID.

## What the workbook contains

Excel opens on `Instructions`. Three sheets are visible:

- `Instructions`: this browser workflow, source rules and recovery guidance.
- `Categories`: program-maintained classification and dropdown reference values.
- `Source Register`: the canonical source register, managed by System1. Submit changes through the browser rather than editing these cells.

`Dashboard` and `Human Operation Desktop` are **veryHidden** compatibility sheets. The browser Overview replaces the old Dashboard. The operation sheet retains program-owned staging and item-level audit history. Do not delete either sheet, unhide them for daily operation, or alter their formulas and records. Every controlled browser-mode save enforces this presentation.

An applied review also refreshes workbook formula and chart caches. These retained calculations support compatible readers; the browser Dashboard reads the current System1 snapshot directly. Calculation, revision or file-lock failures prevent a save from being reported as successful.

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

- Python 3.11+ is required. Microsoft Excel is for workbook inspection and native visual acceptance, not daily review.
- System1 uses its own `Code/.venv`; the workbench uses a separate `.venv` and standard-library runtime. Follow the shared [environment guide](../ENVIRONMENT.md) for platform-specific setup and Environment Doctor.
- Recreate both environments on a new computer; copied environments are not portable installations.
- The normal root launcher is validated on macOS. The retained Windows maintenance menu does not establish acceptance of the browser launcher on Windows.
- Shared paths stay relative. Keep `Requirement_Source_Registry.xlsx`, `Data` and `Code` together. Do not add credentials or device-specific scheduler records to shared files.

Maintainers retain CLI operations for routine intake, status, environment checks and explicitly authorised full source checks. Candidate intake and exceptional recovery use the compatibility adapter with the same human-authority, lock, backup and audit rules. The retired macOS menus are historical artifacts, not alternative daily entry points.

## Safety, recovery and handoff

System1 backs up controlled writes and validates a temporary workbook before replacement. Excel-open detection, complete-run locks, source revisions and request IDs protect against concurrent or repeated application.

- If Excel reports a repair prompt, decline automatic repair and preserve the file. Ask the maintainer to identify a verified backup, restore it under the normal locks and run Environment Doctor.
- If a browser request is waiting for Excel, save and close Excel; the service retries automatically. Do not start a second writer.
- Use the workbench for retrieval failures, corrected links and authorised originals. A saved URL does not prove that an original has been retrieved or verified.
- Preserve `Code/runtime/backups`, logs, source snapshots, completed reviews and weekly QA history. Workbench's separate SQLite and pending uploads also contain persistent operational evidence.

`Code/runtime` archives and files under `Others` are retained evidence, not alternate operational workbooks. `presentation` contains shareable visuals; verify their dates and labels before treating them as current facts. Never overwrite reference or customer-confidential material as part of cleanup.

Before sharing, close Excel and active writers, retain the necessary data and operational history, review confidentiality, and require fresh local environments and Environment Doctor on the recipient computer. A standalone distribution needs package-root documentation derived from the combined project contract. Scheduler registration remains an explicit deployment choice.

Source folder conventions: [STORAGE.md](Data/STORAGE.md).

Overall ownership and handoff boundaries: [README.md](../README.md).
