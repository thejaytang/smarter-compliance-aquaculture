# Project Integration State

Updated: 2026-09-08

## GitHub workstream publication | 2026-09-08

The user authorized replacing the contents of the existing private repository [thejaytang/smarter-compliance-aquaculture](https://github.com/thejaytang/smarter-compliance-aquaculture) on `main`. The verified [publication snapshot](https://github.com/thejaytang/smarter-compliance-aquaculture/commit/1947336efc61c0ba51390db5426ae958f7c92762) is `1947336efc61c0ba51390db5426ae958f7c92762`, containing 964 files. Its root directly contains the entry documents, `system1/`, `system2/`, `system3/` and `workbench/`. The former `01` through `05` wrapper/reference tree is absent from the published current tree. Existing Git commit history remains; this was a normal forward commit replacing file contents.

The publication includes current source, documentation, configuration, the System1 workbook and snapshots, System2 inputs/Gold, and retained project assets. `.gitignore` excludes local environments, caches, runtime sessions/records and generated parsing outputs, including approximately 5 GB of historical System2 results. Those local artifacts and the original parent reference folders were not deleted by this publication. The repository remains private.

Validation: the 964-file publication copy matched local SHA-256 values. GitHub's recursive tree and `main` reference matched the published commit, including every file object ID and executable mode. The isolated copy passed System1 Environment Doctor, System2/Workbench source-import checks and launcher syntax checks. Repository-owned entry/guide links resolved; seven links explicitly refer to local historical evidence. No dependency installation, production service launch or business-data write was part of the publication. This state entry records that verified snapshot; its subsequent documentation-only commit adds the publication receipt.

## Shared environment guide | 2026-09-08

[ENVIRONMENT.md](ENVIRONMENT.md) is the shared setup and verification guide. README and AGENTS link to it, and component guides refer to it instead of maintaining separate installation recipes. Dependency declarations and the System2 lockfile remain in their owning components. System1, System2 and Workbench retain independent environments; System3 remains design-only.

Local checks on 2026-09-08 found Python 3.12.12 in all three existing environments. System1 Environment Doctor passed; System2 and Workbench imports resolved to their own current `src/` directories. System2's offline locked dry run resolved the declared development/docling/table-fallback profile without changing the lockfile or installing packages. The optional Paddle packages are absent from the checked environment; cached models alone are not evidence of a runnable Paddle backend. Available development/native tools were uv 0.10.7, Node.js 22.16.0, Poppler 26.04.0 and Tesseract 5.5.2. This was documentation and environment inspection, not a fresh-machine installation or parser-quality acceptance. No dependencies, production services or business data were changed.

## Current workspace boundary and entry points | 2026-09-08

Requirement code, outputs, documentation, state and launchers belong to `05_Working area of requirements side/`. Its [README.md](README.md), [AGENTS.md](AGENTS.md), `PROJECT_STATE.md` and [workbench launcher](Open Workbench.command) sit alongside the three systems and shared workbench. Maintained project documentation is in English.

At the user's explicit request on 2026-09-08, the temporary workspace-root archive was deleted, including the obsolete independent System1 repository, old Excel exports and relocation records. Current operations use `system1/`; current progress belongs to the owning `PROJECT_STATE.md` files. Reference directories `01` through `04`, and parent Git/tool metadata, retain their separate ownership.

The launcher resolves `workbench/` from its own directory. The production service, System1 workbook and system code directories have not moved. Parent-root references and absolute paths in retained historical records describe their original locations; this section defines the current entry points.

## Documentation cleanup completed | 2026-09-08

The system overview is consolidated into `README.md`; the redundant `SYSTEMS.md` is removed. Workbench design and implementation-plan documents now belong to `workbench/docs/`, so this workspace root has no separate `docs/` directory. The obsolete root archive was deleted at the user's request, as recorded above. The launcher filename and messages are English, and 11 maintained System2 document filenames were changed to English with references updated.

Validation: 45 maintained Markdown documents contain no Chinese prose, all 211 relative links resolve, and recorded SHA-256 evidence was retained during translation. Exact original filenames and paths in historical-source references retain their spelling. The launcher passed executable, shell-syntax and isolated path/module checks. The System1 presentation change passed its two targeted tests; its next controlled workbook save refreshes the launcher instruction. This documentation cleanup did not start a production service or write the production workbook.

## Workbench scope: the complete Requirement workflow | 2026-09-07

The shared workbench covers System1, System2 and System3. Overview presents three system statuses, separate metrics and a shared weekly random-check trend. System1 source charts are confined to its details area. System1 source totals do not represent the entire Requirement workflow, and unavailable or demo data does not count as production progress. Interface state and validation belong to [Workbench state](workbench/PROJECT_STATE.md). System2 retains ownership of its parsing and integration work.

## Browser and Excel entry points aligned | 2026-09-07

The production System1 workbook opens Instructions and keeps Instructions, Categories and Source Register visible. Dashboard and Human Operation Desktop are veryHidden compatibility sheets retaining calculations and review history. The browser owns the daily dashboard, human operations and review-history display. Controlled saves preserve this layout. Operating rules, guides and cross-system navigation are aligned. Reconciliation, backups and acceptance boundaries belong to [System1 state](system1/PROJECT_STATE.md).

That update did not change system ownership, System2 intake contracts or parsing implementation. The following migration and initial handoff records remain evidence from their respective dates.

## System1 to System2 intake and review-cache synchronisation | 2026-09-07

Explicit System2 batches use the existing read-only System1 `read` bridge through System1's own environment. They consume effective selections and source revisions bound to registry, configuration and original-file versions. System1 owns source review; downstream processing does not repeat it. The offline workbook entry remains compatible. This is explicit local intake, without automatic scheduling or a completed workbench review loop.

At the user's request, System1 controlled saves now calculate cell and chart caches when reviews are applied. A cache-only synchronisation preserved formulas and business history in the current registry. Exact hashes, backups and native Excel acceptance belong to [System1 state](system1/PROJECT_STATE.md). Content projections, parser regression and the next experiment belong to [System2 state](system2/PROJECT_STATE.md). The existing workbench remains the human interface. Production System2 queue/decision integration is incomplete; PDF accuracy is pending.

## Current architecture and ownership

- `system1/`: the complete former `05` workspace, owning source governance.
- `system2/`: the relocated desktop PDF Extraction Product, owning governed document parsing. It retains PDF/HTML intake and adds XLSX structural parsing; format capability and acceptance belong to its state file.
- `system3/`: Requirement semantic-enrichment and Site Model interface design based on the user-provided discussion; no running implementation.
- Each system's `PROJECT_STATE.md` owns its internal facts. This root state records integration facts only.

## Workbench integration checkpoint | 2026-09-07

Decision: `CONTINUE`. The platform belongs to `workbench/`. Its normal entry is the workspace-root launcher, which starts a local service and opens the default browser. System1 has live source data, named human decisions, automatic application and history. The browser Dashboard and System to Pending review / Review history navigation are implemented.

System1 workbook/Data remain the source business-state store. Workbench SQLite owns only operators, drafts, requests and receipts. Retired Excel surfaces remain veryHidden compatibility and audit stores; Instructions points to the browser. Current validation, integration boundaries and next work belong to [Workbench state](workbench/PROJECT_STATE.md).

The existing workbench owns human-review entry, interface and operator sessions. System2 owns parsing, review items, evidence, versioned decisions and receipts. System2 and System3 production queues and decisions remain unconnected. A complete PDF reader is available as an evidence component. An independent System2 demo covers highlighted page regions and correction workflows for PDF, HTML and Excel. Demo drafts/history remain in the browser and do not enter production queues, Canonical or random checks. This evidence does not establish a production review loop.

Conversation `compliance-workbench.html` and temporary previews are read-only snapshots of the Dashboard. Early PDF interactions remain historical demos. Neither is a production decision entry point. Design evidence and historical validation are in the [workbench design](workbench/docs/local-workbench-design.md).

## Historical directory integration checkpoint | 2026-09-07

Decision: `CONTINUE`. At that stage, shared README/AGENTS entry points were placed at the outer project root. Their location was corrected to the `05` root on 2026-09-08. Per-level Agent rules were consolidated, and 11 nested README files became guides, engineering documents or specialist indexes. System state ownership remained separate. Directory consolidation did not establish automatic data handoff.

Relative links, read order and the System2 `pyproject.toml` readme reference were updated. Business code, production workbook, inputs, Gold annotations and historical outputs were unchanged. The independent repository, third-party packages and historical evidence were preserved. The pre-consolidation document backup was `/tmp/smarter-compliance-docs-before-20260907`, for local recovery only.

At that checkpoint, all active local Markdown links resolved; nested active entry points were removed, with dependencies, caches, independent repositories and historical evidence excluded. The System2 packaging readme existed, and the production workbook SHA-256 was unchanged. No business cycle or parsing job was run for that documentation change.

The earlier atomic system migration preserved inode, size, permissions and link targets for 1,864 System1 entries and 145,822 System2 entries. Hidden files, environments, inputs, Gold, historical outputs and caches moved with their systems. Old absolute paths in environment launch scripts were corrected.

System1 Environment Doctor returned `PASS`. System2 local regression passed with one skip. System1 passed 60 of 61 tests; the existing Dashboard hidden-column contract caused the remaining failure. The workbook hash was unchanged. See System1 state for details and subsequent resolution.

No production Routine Cycle, Full Source Check, large-PDF run, external API, automation, commit or push was performed. Reference and confidential material retained its original location.

## Next steps and boundaries

- Use the current system paths for development and operations. The former desktop PDF Extraction Product path is absent; tools still bound to it need the `05_Working area of requirements side/system2` path.
- The earlier System1 Dashboard contract mismatch has been resolved. Retired sheets remain hidden; use current browser and controlled-save rules. Validation belongs to System1 state.
- System3 next validates its consumer interface on real requirements. See its state and design basis. System1/System2 have the explicit read-only intake described above; automatic scheduling and production review closure still require contracts and integration acceptance.

## System3 design checkpoint | 2026-09-07

Decision: `ADJUST`. The user-selected shared discussion was read and responsibilities were aligned. Keep System3 as the workspace for validating a Site Model consumer contract. Independent deployment is undecided, and existing System2 semantic modules remain in place. This was a documentation change; no external team contact or running implementation was performed.

## System2 HTML code merge | 2026-09-07

The user authorised merging HTML v2, governed intake and verification code from an independent worktree into the saved project. Newer Workbench and System1 changes were preserved; workbook and snapshots were unchanged. System2 guide/state were updated. Merge evidence belongs to `system2/docs/reports/html-merge-20260907.json`. Code integration does not establish a connected parsing and human-review loop.

## Weekly checks and English workbench interface | 2026-09-07

The workbench uses English and three named operators. The review service itself owns weekly checks: five items per connected system each Monday, with persistent weekly identity preventing duplicates. This does not depend on Codex tasks or personal-device reminders. System1 supports batch creation, human verification and five-week accuracy projection; System2/3 display their actual disconnected state. Data, identity audit and validation belong to Workbench and System1 state.

## Source-content consumption and INCLUDE scope | 2026-09-07

New System2 batches default to `source-records/2`, extending source-content fields and Canonical references while retaining the explicit v1 entry and historical artifacts. The projection is read-only and is not connected to workbench decision writes. Only INCLUDE sources are in scope; other sources do not generate parsing or replacement tasks and do not block current completion. Seven INCLUDE Lovdata directory snapshots require complete originals from System1, without repeating source eligibility review. That diagnostic round did not download or change upstream state. Implementation and acceptance belong to [System2 state](system2/PROJECT_STATE.md).

## Human format-conversion design boundary | 2026-09-08

The user confirmed three System2 parsing pipelines: HTML, XLSX and PDF. Other INCLUDE formats require a dedicated human-conversion workflow in the existing workbench to create a parsing copy, followed by verification and intake. Preserve original sources and versions; do not repeat eligibility review or build another human interface. Conversion, registration and intake remain design work, without changes to System1, Workbench or production parsing. The detailed contract, state and validation belong to [System2 state](system2/PROJECT_STATE.md).
