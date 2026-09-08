# Smarter Compliance Aquaculture

This project builds a traceable source-governance and document-extraction workflow for aquaculture compliance. This is the single human entry point for the Requirement Workstream, alongside `system1/`, `system2/`, `system3/` and `workbench/`. Agents start with [AGENTS.md](AGENTS.md).

The GitHub repository contains this workstream directly at its root, without a `05` wrapper or the former parent reference folders. In the original authoring workspace, this same root is named `05_Working area of requirements side/`. The repository includes current code, documentation, configuration, the System1 register and source snapshots, System2 inputs and Gold. Local environments, caches, runtime sessions/history and generated parsing outputs are excluded by [.gitignore](.gitignore). Historical links into those local-only directories require the original local workspace; this repository is not a backup of live browser sessions or all historical runs.

## Open the workbench

For a new computer or a missing environment, start with [ENVIRONMENT.md](ENVIRONMENT.md). It covers component environments, dependency files, setup, native tools and verification.

Double-click the [workbench launcher](Open Workbench.command) in this directory. It starts a local service and opens the default browser; repeated launches reuse the same service. The shared Requirement workbench covers System1 source governance, System2 extraction review and System3 semantic enrichment. System1 source ratings, URL corrections, original-file intake and review history are available in the browser. Select a named operator once; submitted decisions are applied automatically.

The interface is in English. Requirement overview presents the three systems, their actual connection status, separate units, pending work and key outputs, followed by five weeks of random-check accuracy. Expand System1 details for source statistics. Unconnected metrics display Not connected, and demo records do not count as production progress. Each system has Pending review and Review history. Excel remains the System1 business-state store and opens Instructions by default. Dashboard and Human Operation Desktop are veryHidden compatibility sheets that retain formulas and review history. Close Excel while applying changes. System2 and System3 production queues are not connected; System2 provides a clearly labelled review demo whose completed items move to demo history. See the [workbench guide](workbench/USER_GUIDE.md).

## Systems and boundaries

| System | Responsibility | Guide |
| --- | --- | --- |
| System1 | Source identity, original snapshots, selection, named human decisions and source quality | [System1 guide](system1/USER_GUIDE.md) |
| System2 | PDF/HTML/XLSX parsing, Canonical JSON, verification and source-content projection | [System2 guide](system2/USER_GUIDE.md) |
| System3 | Requirement semantic enrichment and Site Model interface design; currently a design workspace | [System3 design](system3/DESIGN.md) |

System1 governed sources feed System2 document parsing. Directory integration alone does not establish automatic handoff. System1 preserves original formats. System2 retains its PDF pipeline and supports five controlled local HTML template families plus XLSX structural parsing with independent verification. Legacy XLS is not implemented. Current priorities are Excel/HTML, integration with the existing workbench, then PDF accuracy. See [System2 state](system2/PROJECT_STATE.md). System3 designs semantic outputs for Site Model consumers; it has no running implementation. Grounding in actual site instances and evidence assessment remain collaboration boundaries. System3 expresses object types, conditions and actions; Site Model collaborators map them to actual entities, events and states. Evidence needs remain a shared interface, with no separate evidence-collection or compliance-decision system implemented. Components retain separate Python environments, and the workbench uses system adapters.

System2 explicit local batches consume effective selections and source revisions through System1's read-only interface. They do not repeat completed source-eligibility reviews. System1 refreshes workbook formula and chart caches when reviews are saved; System2 verifies parsed text, structure and field mapping. This connection does not start parsing automatically, and production review queues and decisions still require workbench integration. Only INCLUDE sources enter the current processing scope. See the [version 2 content contract](system2/docs/contracts/source-records-v2.md); an explicit version 1 entry remains available.

## Directory and document ownership

- This repository root: shared entry documents, three systems and the workbench.
- The original authoring workspace also has parent-level `01_Project_Documents/`, `02_ASC_Standards/`, `03_GLOBALGAP_Standards/` and `04_Customer_Examples_CONFIDENTIAL/` reference directories. They are outside this repository and are not required to locate its component code or environments. Confidential customer material remains local.
- `PROJECT_STATE.md`: cross-system integration state.
- `ENVIRONMENT.md`: shared runtime setup and verification guide; dependency declarations remain in each component.
- The workbench launcher in this directory: the single normal launch entry.

Requirement code, outputs, documentation, state and launchers belong inside this workspace. Keep `README.md` and `AGENTS.md` only at this workspace root, alongside the systems. Use ordinary specialist documents below this level. Each system's `PROJECT_STATE.md` owns its current facts; historical reports and execution plans retain their separate roles.

## Read by task

- System1 daily operations: open the workbench, select an operator and complete the relevant task. See the [user guide](system1/USER_GUIDE.md), [engineering guide](system1/Code/ENGINEERING.md) and [current state](system1/PROJECT_STATE.md).
- System2 parsing and verification: check [current state](system2/PROJECT_STATE.md), then choose a bounded validation command from the [user guide](system2/USER_GUIDE.md). Consult the [document index](system2/docs/INDEX.md) for architecture and contracts.
- System3 interfaces: read the [design](system3/DESIGN.md), [design basis](system3/docs/design-basis.md) and [current state](system3/PROJECT_STATE.md).
- Cross-system collaboration: use the system boundaries above and [integration state](PROJECT_STATE.md).
- Shared workbench: read the [user guide](workbench/USER_GUIDE.md), [current state](workbench/PROJECT_STATE.md), [design evidence](workbench/docs/local-workbench-design.md) and [review demo contract](workbench/docs/system2-review-demo.md). System1 has live source access and governed decision writes. Conversation previews are read-only snapshots; early interaction demos remain historical design evidence.

Third-party dependencies and retained system-specific historical artifacts keep their original contents and entry documents. Historical entry points are not current operating instructions. A future standalone system distribution needs suitable entry documents at its package root.

Before development, read [AGENTS.md](AGENTS.md). Current integration facts belong to [PROJECT_STATE.md](PROJECT_STATE.md).
