# Smarter Compliance Aquaculture Project Contract

## Scope and read order

This is the only Agent entry point for the active Requirement Workstream. Its root is the directory containing this file and `README.md`, alongside `system1/`, `system2/`, `system3/` and `workbench/`. In the original authoring workspace this directory is named `05_Working area of requirements side/`; on GitHub its contents are the repository root, without that wrapper or the parent reference directories. Resolve component paths from this file's directory. Do not create duplicate `README.md`, `AGENTS.md`, `agent.md` or `AGENT.md` entry points for this workstream in parent or component directories.

1. Read this workstream root's `README.md` and `PROJECT_STATE.md`.
2. Read the applicable System1, System2, System3 or Workbench rules below, then that system's `PROJECT_STATE.md`.
3. Read only the task-relevant guide, architecture, contract and source evidence linked from this workstream root's `README.md`. Already-read documents need not be loaded again.

Before running code or changing dependencies, read [ENVIRONMENT.md](ENVIRONMENT.md), identify the owning component's existing environment and inspect its dependency declaration/lockfile. Update that guide when setup procedures or environment ownership change; do not copy installation instructions into parallel guides.

## Documentation ownership

- Write all maintained project documentation in English. Preserve exact identifiers, commands, file paths and authoritative source quotations. Historical archives and original source material retain their original language.
- This workstream root's `README.md` is the single human entry point; this file is the single operating contract. System guides describe usage and implementation, not parallel Agent instructions.
- System1 usage: `system1/USER_GUIDE.md`; engineering: `system1/Code/ENGINEERING.md` under the same workstream.
- System2 usage: `system2/USER_GUIDE.md`; module boundaries: its `docs/architecture/05-module-boundaries-and-directory-layout.md`.
- System3 design: `system3/DESIGN.md`; design evidence: its `docs/design-basis.md`.
- Keep current facts in the owning `PROJECT_STATE.md`, history in reports or ledgers, and execution plans in designated documents. Each fact has one canonical source.
- After documentation or directory changes, verify relative links, read order, packaging references and ownership consistency. Preserve existing safety constraints.
- Independent repositories, third-party packages and retained historical artifacts are outside this consolidation. Do not rewrite their entry points or historical evidence.
- A future standalone distribution of one system needs its own package-root entry points derived from this contract; copying a system folder alone does not carry the combined project's Agent instructions.

## Ownership

- `system1` owns governed source management.
- `system2` owns the relocated PDF Extraction Product.
- `system3` owns requirement semantic-enrichment and Site Model interface design. Do not treat its design workspace as an implemented service, Site Model or compliance engine.
- Keep Requirement code, outputs, documentation, integration state and launchers inside this workstream root. Parent-level `01` to `04` source/reference directories and repository/tool metadata retain their own ownership.
- System-specific architecture, environment directories, dependency declarations, operational commands and state belong inside the owning system. Shared setup instructions are indexed in `ENVIRONMENT.md`; this workstream root's `PROJECT_STATE.md` records integration facts only.

## Shared boundaries

- Treat `../01_Project_Documents`, `../02_ASC_Standards`, `../03_GLOBALGAP_Standards`, and `../04_Customer_Examples_CONFIDENTIAL` as source and reference material. Do not rewrite, relocate, submit or publish them without explicit authorization.
- Keep customer-confidential material local; never expose it in logs, presentations or responses.
- Do not commit, push, submit, email, publish, enable automation or change external accounts unless explicitly requested.
- Use one project-local environment per system. Never install project dependencies into the system or another system's environment.
- Use OfficeCLI for Office structure work and native Microsoft Office for final visual acceptance. Do not use LibreOffice by default.
- Tests, generated workbooks, previews, diagrams and directory integration are evidence for their specific checks, not automatic business, legal or release acceptance.
- Inspect current repository, workbook or runtime evidence before current-state claims. Label older reports and presentation assets as historical.

## Working method

Use adaptive, rolling-horizon planning. Diagnose observed failures with the smallest discriminating check before modifying. At a checkpoint choose `CONTINUE`, `ADJUST`, `BACKTRACK`, `PIVOT` or `STOP`.

Update the owning system's `PROJECT_STATE.md` after events that change future judgments. Update this workstream root's `PROJECT_STATE.md` when ownership or integration changes. Keep states decision-oriented, not chronological command logs. Preserve backups, snapshots, logs and human-review history.

## System1 operating rules

Scope: `system1/`. Paths in this section are relative to that system unless explicitly identified as project-root paths.

### Scope and authority

- Treat this folder as the canonical System1 source-management workspace within the Requirement Workstream.
- Treat `Requirement_Source_Registry.xlsx` as the human-governed System1 business-state store.
- Treat `Source Register` as program-managed. Normal human changes are submitted through the local browser workbench; Human Operation Desktop remains a veryHidden program-owned staging and audit sheet for the compatibility adapter. Dashboard is also veryHidden and retired from daily use; keep its formulas/charts for compatibility. Instructions opens by default and describes the browser workflow. Enforce these presentation rules on controlled saves.
- System1 governs source identity, retrieval, snapshots, selection, provenance, human review, and QA.
- System1 does not perform legal interpretation and does not represent a completed System2 Requirement-extraction pipeline.
- Treat `presentation` as the current shareable visual area. Treat variants under `Others` as supporting or historical until their dates and labels are verified.

### Current System1 model

System1 uses one deterministic Leader, three bounded modules, and one human gate:

1. `Discovery & Intake`
2. `Retrieval & Monitoring`
3. `Governance & QA`
4. Local browser workbench as the normal named-human decision surface; the hidden operation sheet retains System1 application history.

Without a configured provider, do not claim autonomous regulatory discovery, semantic reasoning, or complete source coverage. API-connected capabilities are optional extensions and never replace Python validation or human authority.

### Data and output contract

Inputs may include registered official sources, `retrieval_url` targets, authorised files placed in `Data/00_Human_Intake`, structured candidates, configuration, schedule intent, and operator decisions.

System1 produces and maintains:

- governed workbook state;
- original-format source snapshots under `Data`;
- one current human-operation task per source where action remains unresolved;
- backups, locks, persisted state, logs, and Leader reports under `Code/runtime`;
- a maintained eligible source package for downstream Requirement extraction.

Do not describe this maintained source package as an already extracted Requirement dataset.

### Non-negotiable operating rules

- Resolve all shared paths relative to this workspace. Never write device-specific absolute paths into the workbook or shared configuration.
- Use only the project-local environment at `Code/.venv`. Never install project dependencies into the system or default Python environment.
- Keep `official_url` as source identity or landing page and `retrieval_url` as the actual retrievable resource.
- Keep retrieval independent of selection.
- Preserve authoritative language and original published format.
- Never bypass a paywall or silently substitute a convenience conversion for an authoritative original.
- Preserve the current valid snapshot after a failed retrieval or replacement.
- Require a named human decision before accepting a new candidate or applying a governed judgment.
- Do not write while Excel is open or another System1 process holds the lock.
- Preserve backups, logs, source snapshots, failure evidence, human-review history, and Random QA history.
- Do not add API keys, credentials, customer-confidential content, or device-specific scheduler records to shared files.
- Do not commit, push, publish, email, enable automation, or run a Full Source Check without explicit user authorization.

- Resolve configured paths from `Code/config/config.json`; shared paths remain relative.
- Prefer complete official HTML over an equivalent official PDF. Preserve the authoritative language and original format.
- Among equally authoritative official versions, prefer English, then Norwegian, then Other.
- Accept a new candidate only with a human `ACCEPT` decision and operator identity.
- Consolidate all unresolved choices, corrections, exceptions, pending selections, candidates, manual-file actions and Random QA into one current task per source.
- Check source fingerprints before applying tasks; fill operator and program timestamps in code.
- Retain and hide completed tasks. Keep correction/candidate fields hidden unless required, and program support outside the normal view.
- Create at most one Random QA batch per ISO week, scheduled for Monday in the configured business timezone. Sample 5 eligible items per connected system; preserve older batches, record short or empty samples, and catch up only the current week after downtime.
- Back up and use temporary-file replacement for controlled workbook writes.
- Refresh formula and chart result caches in the same controlled save as an applied review. Preserve formulas; unsupported calculations must stop publication rather than leave empty or stale caches.
- Recipients must recreate `Code/.venv`; a copied environment is not assumed portable.
- Before completion, distinguish verified evidence, time-specific or unresolved state and external acceptance still required.

### Working method and checkpoints

Use adaptive, evidence-based work:

1. Inspect the relevant source, workbook structure, configuration, code, or runtime evidence.
2. Record the observed symptom and distinguish it from plausible root causes.
3. Run the smallest check that can discriminate between those explanations.
4. Modify only after diagnosis.
5. Validate in proportion to the change.
6. At the checkpoint, choose `CONTINUE`, `ADJUST`, `BACKTRACK`, `PIVOT`, or `STOP`.

Validation expectations:

- Documentation-only change: verify file paths, commands, terminology, and cross-file consistency.
- Local code change: run targeted tests.
- Cross-module change: run the complete local regression suite.
- Environment or schedule change: run Environment Doctor before enabling or registering automation.
- Workbook or source-state change: verify workbook integrity, Leader/workbook task agreement, retained completed history, IDs, filenames, hashes, and current files.
- Full Source Check: treat as a network-enabled operational run requiring explicit intent, not as a normal test.

### Failure handling

Record the observed failure, preserve current state, distinguish symptom from likely cause, run the smallest discriminating check, and then repair. Do not clear retrieval state, failure evidence, or human tasks to make a report appear successful.

## System2 operating rules

Scope: `system2/`. Paths in this section are relative to that system unless explicitly identified as project-root paths.

### Purpose and scope

System2 provides reliable parsing of English and Norwegian legislation, general regulations, standards and audit manuals. Retain the PDF pipeline, controlled local System1 snapshot intake, template-specific HTML structural parsing and original XLSX structural parsing. Legacy XLS is not implemented. The current format scope belongs to `docs/contracts/source-intake.md`. Prioritise silent omissions, structural errors and field errors; generic public benchmark rankings are not completion criteria.

Canonical JSON is the sole structured source of truth. Markdown, HTML, XML, RAG, Regulatory IR and RDF are downstream products and must never overwrite Canonical facts.

The existing local workbench owns the normal human-review entry point, interface, operator sessions and interaction. System2 owns parsing, verification, review items, evidence, versioned decision application, audit receipts and result-state readback. Do not build a separate normal review interface. Retain the existing standalone review page only for compatibility and diagnostics.

### Source of truth

- Stable operating rules: the System2 section of `../AGENTS.md` at the `05` workspace root.
- Current state: `PROJECT_STATE.md`. Also update `../PROJECT_STATE.md` when cross-system ownership or interfaces change; do not duplicate integration state here.
- Stable architecture: `docs/architecture/`.
- Current complex-task plans: `docs/plans/`.
- Domain contracts: `docs/contracts/`.
- Historical events and acceptance evidence: `docs/reports/`.
- Executable policy: `config/`, schemas and tests.
- Irreversible Gold sample state: `gold/requirements/sample-history.json`.

Each fact has one canonical source. Other documents reference it rather than maintaining parallel copies.

### Module boundaries

- `contracts`: stable cross-module models; no business-implementation imports.
- `preflight`: safety checks and document/page/region profiling.
- `evidence`: acquisition of native, rendered, OCR and vector source evidence.
- `extraction`: routing, layout, parsing, assembly and reconciliation.
- `canonical`: Canonical schemas, invariants and structural self-consistency checks.
- `verification`: source-fidelity verification and per-atom human-review routing.
- `domains`: Requirement, Regulatory IR and other domain interpretation.
- `delivery`: read-only exports and deliverable generation.
- `evaluation`: Gold, metrics and regression; no production inference.
- `orchestration`: orchestration, run state, caching and failure propagation only.

Verification depth describes machine evidence depth only. Every machine-generated or machine-judged atom requires confidence, provenance and a review policy. At every depth, below-threshold or missing confidence, conflicting evidence or incomplete provenance must trigger human review.

### Engineering directories

- `data/inputs/`: user-provided production and test PDFs; never overwrite or delete.
- `docs/`: architecture, contracts, plans, goals and acceptance records.
- `src/pdf_extraction/`: product code.
- `tests/`: unit, contract, integration and domain regression tests.
- `gold/`: internal Gold Set source PDFs, annotations and manifests.
- `outputs/baselines/`: historical baselines that must be preserved.
- `outputs/runs/`: current experiments and production run results.
- `tmp/`: reproducible temporary files.
- `runtime/`: job database and run state.

Use `system2/.venv` and `PYTHONPATH=src` for local source execution. Never install dependencies into the system environment or another project's environment.

### Always

1. Preserve page, bbox, segment, native/OCR evidence, parser version and configuration hash for every key result.
2. Document-level learning may propose structure, anomalies and targeted reparse evidence; it must not generate text absent from the source PDF.
3. Automatic text repair requires at least two independent evidence sources. Otherwise return `review_required` or `abstain`.
4. Record the failure, distinguish symptom from root cause, then design the smallest discriminating experiment.
5. Base testing on the internal Gold Set, real regulatory/standard PDFs and fixed error categories.
6. Run targeted tests proportional to risk before deciding whether broader regression is needed.
7. Before finishing, update `PROJECT_STATE.md` for code, contract or validation events that change future decisions; record historical events in the relevant ledger.

### Ask first

- Overwriting Gold annotations, manifests or `outputs/baselines/`.
- Running a complete large PDF, a full external benchmark or a costly model task.
- Deleting, moving or renaming user inputs and historical outputs.
- Sending document contents to external services or enabling externally hosted models.
- Refactoring that breaks compatibility entry points or causes irreversible artifact migration.

### Never

- Overwrite or delete PDFs under `data/inputs/`.
- Execute `git commit` or `git push`.
- Treat schema validity, nonempty Markdown, passing tests or `accepted` alone as source-fidelity or release acceptance.
- Allow exporters, domain interpreters or evaluators to overwrite Canonical source facts.
- Present the same evidence used for extraction as independent verification evidence.
- Reduce human workload by lowering thresholds, hiding review items or changing Gold.

### Completion criteria

Code tasks require clear target-module contracts, passing targeted tests, source/semantic inspection of key artifacts, preserved inputs and historical baselines, and appropriate state updates. Report actual blockers when verification fails; artifact generation does not replace acceptance.

### Current domain acceptance priorities

- Full-text header and footer templates.
- Repeating Requirement/Indicator table templates.
- Clause numbering and hierarchy continuity.
- Hierarchy determined jointly by list markers and indentation.
- Consistent column counts, column boundaries and repeated headers across page-spanning tables.
- Detection of silent structural-type errors even when the text is present.

## System3 operating rules

Scope: `system3/`. Paths in this section are relative to that system unless explicitly identified as project-root paths.

### Source of truth

- Stable scope and operating rules: the System3 section of `../AGENTS.md` at the `05` workspace root.
- Design sources, candidate fields and boundaries awaiting validation: `docs/design-basis.md`.
- Current facts, checkpoint and next experiment: `PROJECT_STATE.md`.
- Upstream source text and parsing evidence: existing System2 Canonical artifacts; System3 must not overwrite them.
- Cross-system ownership: `../PROJECT_STATE.md`.

### Stable constraints

- Preserve requirement ID, source version, original text and evidence location. Keep enriched fields separate from source text.
- Record source-supported information, human decisions, inference and unknowns separately. Do not guess missing thresholds, responsible actors, exceptions or time constraints.
- Machine enrichment requires provenance, confidence and review status. Low confidence, evidence conflicts or incomplete sources require human review.
- Interfaces express object types, conditions and actions. The Site Model team owns grounding in actual site instances.
- Information needed for a decision belongs to the collaboration interface. Do not expand it into evidence collection or final compliance decisions before that scope is confirmed.
- Inspect existing System2 domain fields and artifacts before filling real gaps. Do not move existing semantic modules merely because of system names.
- Maintain one requirement identity across views; sheets are views only. Historical deviations may guide priorities but cannot replace source-selection or completeness criteria.
- Follow shared confidentiality, original-protection, external-transmission and submission boundaries. Suggestions in design sources are not external-action authorisation.

### Validation and completion

For document changes, verify source correspondence, links and cross-layer consistency. Trace every prototype interface field to a real source and record Site Model consumer feedback. Do not claim interface acceptance without that feedback, or present examples as real regulatory or site evidence.

Create a separate System3 environment before implementing a running service. Do not create unused source or environment scaffolding. Update this system's state after changes to responsibility, interfaces or validation conclusions, and update `../PROJECT_STATE.md` for cross-system boundary changes.


## Workbench operating rules

Scope: `workbench/`, relative to this workstream root.

- Workbench is the shared Requirement workspace for System1, System2 and System3. Overview must present all three stages with system-scoped units and connection status. Keep System1 source statistics in its own detail area; do not add sources, extraction items and enrichment items into one total or present unavailable/demo data as live zero/completion.
- Use this workstream root's `Open Workbench.command` as the sole normal macOS entry. It launches a single loopback-only service and opens the system default browser. Retired menu launchers are historical artifacts.
- Use this component's own .venv; it has no third-party runtime dependencies. Call System1 through its own Code/.venv/bin/python and system1.workbench_bridge JSON adapter. Never share mutable environments.
- System1 workbook/Data remain canonical source business state. Workbench SQLite owns actor profiles, drafts, request journal and application receipts, not a duplicate source registry.
- Named actors, source/task revisions, stable request IDs, Excel-open deferral, existing write locks, backups and history remain mandatory. A draft/submitted request is not an applied decision.
- Preserve both Excel Dashboard and Human Operation Desktop as veryHidden in browser mode. Instructions is the default visible browser-workflow guide; every controlled save must keep retired surfaces hidden. The hidden sheets remain program-owned compatibility and audit stores; do not delete history or break formulas.
- Serve only registered source artifacts, never client-supplied paths. Keep original HTML download-only; text previews must not run source scripts. Enforce loopback Host, Origin, CSRF and server-bound actor checks.
- Preserve unverified human issues after partial scores or corrections; explicit verification resolves them. Light option fill represents a previous score; dark fill represents a new explicit click. Previous scores do not count as current confirmation.
- Do not start Full Source Check, external models, downloads, parsing or publishing merely on launch/view. Current URL correction saves metadata, not a verified new snapshot.
- System2/3 pages must state actual integration status.
- Weekly QA belongs to the review service itself, never a Codex automation or a device-specific personal reminder. Persist batch identity in the owning system so service restarts or relocation do not duplicate a batch.
- Use the approved reviewer roster in workbench/src/local_workbench/identities.py; preserve original external-review evidence when normalising names.
- Validate writes on isolated workbooks; test request replay/staleness/locks/recovery and rendered UI. Current platform state belongs to workbench/PROJECT_STATE.md; update the workstream integration state and System1 state when entry ownership or adapter behavior changes.
