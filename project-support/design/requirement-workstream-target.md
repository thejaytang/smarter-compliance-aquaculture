# Requirement Workstream: Target, Design and Acceptance

**Supersession, 2026-09-11:** the [human-led, material-centered workbench goal](human-led-workbench-goal.md) is now the canonical product target. It supersedes this document's automation-first emphasis and default System2/System3 UI/stage presentation. The earlier specification below remains historical context where it conflicts; original/evidence/history protections remain. The new goal is prepared for separate assignment, not an implemented runtime transition.

The [functional delivery contract](requirement-workstream-stage-delivery.md) governed the completed functional phase. Preserve source/history, integrity, human authority and external-action boundaries. Its quality deferrals applied to that phase only; a subsequent quality goal defines its own evidence and acceptance requirements. A usable manual path and truthful saved/pending/output states remain mandatory. Earlier target statements retain their historical or future-target meaning until verified implementation is recorded in the owning state files.

Alignment date: 2026-09-10. Status: target specification and proposed implementation plan, not an implementation or acceptance report.

This remains the long-term aligned target. The [stage delivery goal v2](requirement-workstream-stage-goal-v2.md) now defines the separately prepared, not-yet-started bounded delivery window. Implementation descriptions in this alignment record, including section 8 and its migration proposal, are snapshots from the original discussion; current database/runtime facts belong to the owning states linked from [integration state](../../PROJECT_STATE.md).

This is the canonical specification of the user's target aligned in the September 10 discussion. [Decision boundaries](decision-boundaries.md) owns alternatives, sensitivity and remaining decisions. The root [project state](../../PROJECT_STATE.md) owns implementation status. Existing runtime contracts continue to describe the deployed behavior until their replacements are implemented and verified.

Status vocabulary: **CONFIRMED** is an explicit user decision; **PROVISIONAL** is an agreed working assumption awaiting collaborator confirmation; **PROPOSED** is an engineering recommendation; **OPEN** is unresolved. Proposed thresholds, measures and mechanisms must not be reported as user-approved numbers or existing capabilities.

## 1. Stable objective

Build a traceable, automation-first Requirement Workstream for aquaculture compliance. Govern sources, faithfully recover their content, and identify source-supported Requirements for later semantic enrichment and collaboration with the Evidence and Site Model workstreams. Minimize unnecessary human effort through reliable machine processing and verification. Concentrate every required human decision, correction, supplement and QA task in one usable workbench.

System1 governs sources. System2A reconstructs source content. System2B identifies Requirements from accepted content. System3 will enrich their semantics; its implementation remains outside the current phase. A and B are logical stages with separate acceptance gates, not a commitment to separate deployed services.

The system runs without an external large-model API. Optional API-connected multi-agent assistance improves processing and checking through existing program capabilities. Both modes obey the same evidence, confidence, acceptance and human-review rules. The user's later clarification excludes agents autonomously editing program code or deploying changes from the product target.

## 2. Scope and ownership

### System1: source governance

**CONFIRMED:** preserve previously completed human source decisions. Do not repeat the existing batch's eligibility review. Unresolved matters, such as unavailable paid originals, remain explicit Pending items; do not bypass them or manufacture source content. Current work consumes existing eligible sources; expanding discovery is not a prerequisite for this phase.

System1 continues to own source identity, original retrieval/snapshots, versions, provenance, selection and source-governance decisions. Original files remain retained and linked by stable identity and fingerprint.

**CONFIRMED TARGET:** migrate System1 business-state authority from its current Excel-based implementation to an owning local relational database. Excel becomes a one-way synchronized register. Preserve existing source identities, original files, effective selections, unresolved work, named human decisions and historical records. Agreement on the target does not establish that migration has happened.

### System2A: faithful source reconstruction

**CONFIRMED:** maximize faithful coverage, content accuracy, structure and reading order. Do not remove content because it appears irrelevant to Requirements. Retain page numbers, headers, footers, notes and other auxiliary material, with explicit types and source locations.

Preserve original clause numbering and full source units. Distinguish a parser's mistaken boundary from a source's actual boundary. Corrections change a versioned effective view, not the original artifact.

For PDF, support native-text, scanned and mixed pages/regions. A scanned page is not exempt from text extraction merely because it is stored as an image. Missing-content detection must inspect the original page, not only the set of already extracted units.

For photographs and illustrations, retain the full image and its figure number/title, relevant caption and source location. Do not transcribe text inside these illustrations in this phase. Flag uncertainty about whether a region is an illustration, a table or document text; misclassifying a scanned page as an illustration must not silently excuse omissions.

Retain each table as one coherent source object with original image evidence, title, table notes and footnotes. Also extract readable cell content, rows, columns, headers and merged-cell relationships. Preserve cross-page fragments and their order/relationships. System2A may represent rows and cells structurally, but it does not decide which are Requirements.

**PROPOSED current format baseline:** retain the existing PDF, governed HTML and original XLSX paths rather than narrowing the whole system to PDF. Preserve the existing handling of unsupported formats. Real English/Norwegian coverage must be measured by format and language. This discussion did not approve unlimited formats, all languages or a new source corpus.

### System2B: Requirement identification

**CONFIRMED:** classify source-supported content as Requirement, supporting context, non-Requirement or undetermined. Recommendations can be Requirements; a source need not use mandatory wording. Identifying a Requirement is distinct from deciding whether a particular site complies with it or whether it applies to that specific site.

Keep original text, source identity/version/location, original numbering and relevant context associated with every result. Definitions, headings or explanatory notes may support a Requirement without becoming independent Requirements themselves. A table's numbered requirement entries are identified in B, not discarded or semantically selected during A.

**PROVISIONAL splitting rule:** retain the full original numbered item as the parent. Represent separate requirement subitems as derived children, including when the source has no explicit sub-numbering. Preserve verbatim evidence spans and needed shared context. Original numbering and generated subitem labels must be visibly different. Parent and child views must not be counted as unrelated duplicate obligations. Whether the parent itself is a deliverable Requirement or a containing record, the split criterion and child counting remain for collaborator confirmation.

This is limited requirement subdivision, not permission to invent missing obligations, complete actor/action/object ontology fields, or begin System3. Split generation must have its own quality evidence. An unsupported split remains pending or undetermined.

### System3 and external collaboration

**CONFIRMED:** reserve semantic enrichment of actors, actions, objects, conditions and other ontology fields for System3. It will use the same human workbench and one-way Excel principle. Do not implement it now. Evidence extraction, site-instance grounding and final compliance decisions remain outside this delivery.

## 3. One human workbench

**CONFIRMED:** all three systems share the normal human entry point. No spreadsheet-based review inbox or second normal review application. Separate System1, System2A, System2B and future System3 tasks and counts, while keeping navigation and interaction consistent.

Each pending task presents the exact human decision, the reason it needs attention, applicable machine confidence and the evidence needed to act. For source-content review, place the original on the left and extracted/effective content on the right, including adjacent context. Tables need whole-table context and focused cell evidence. Avoid requiring the reviewer to navigate raw internal identifiers or technical diagnostics to finish an ordinary task.

For an omission: locate the suspected original region; show surrounding extracted content; let the human confirm the omission and copy/type the source text into an appropriate input; bind the addition to the source position; preview and apply it to the effective content. Do not require the user to edit a hidden Excel sheet or database record.

**CONFIRMED flow:** confirmed completion in the workbench -> durable database update and audit receipt -> removal from Pending and inclusion in Review history -> automatic Excel synchronization. A draft or failed save is not completion. Unresolved follow-up remains pending even if a particular action has been recorded in history.

**PROPOSED:** re-check affected dependencies after content correction; previously accepted downstream results that depend on changed content are suspended until their applicable checks pass again. Historical decisions remain attached to the version that was actually reviewed. This supports correction without turning one-way Excel export into an irreversible review process.

## 4. Data and synchronization architecture

**CONFIRMED:** owning local relational databases hold authoritative current workflow state and human decisions. Originals, images and immutable structured source artifacts may remain in managed files referenced by the databases. Database authority over review state does not remove the original source's evidential authority.

Each business fact has one owner. A shared workbench does not require one database for every component. Reuse the existing component boundaries and adapters unless measured evidence justifies consolidation. System1 migration is required; System2 already has workflow database foundations, immutable Canonical artifacts and derived Excel output.

Excel is exclusively a readable, synchronized content carrier and delivery snapshot. There is no normal Excel-to-database import. Protect or label the generated workbook to discourage edits; changes to a downloaded copy cannot alter authoritative state. Direct edits to the generated file are not accepted review decisions.

**PROPOSED implementation:** save decision, version transition and audit event atomically in the owning store. Mark the export dirty or record an outbox event in the same durable operation. Read workbench lists from indexed data, with pagination and lazy loading of full originals. Export a consistent database snapshot asynchronously, coalescing rapid successive changes. Use an input/version fingerprint to skip unchanged work and atomic file replacement to retain the last complete workbook on failure.

The interface distinguishes saved decision, export pending, export synchronized and export failed. Export receipts identify the source state/version represented. Failure retries without losing the database decision. Opening Excel may delay replacement of its file; it must not block database review operations after the migration. A downloaded workbook is a dated snapshot, not a live client. Do not promise that an already open desktop workbook automatically refreshes its display.

## 5. Independent System2A verification

**CONFIRMED priority:** source-fidelity verification is a primary deliverable, including the detector's own reliability. It must not be equated with passing parser tests or checking the output schema.

**PROPOSED contract:** an independently callable verification module takes the original artifact, its version, parser output through an adapter, source-to-output mappings and declared scope. It returns typed findings, original/output locations, evidence origin, checks performed, unverified areas, severity and machine-check signals. Keep this interface separable enough to evaluate results from another parser. Turning it into a separately delivered multi-parser product is an OPEN collaboration scope decision, not assumed work on the other team's project.

The verification design has three layers:

1. **Per-document original comparison.** Native pages: compare original character/word evidence and positions with reconstructed content. Scanned/mixed regions: detect text/table regions from page imagery independently of already recognized strings and compare region coverage, reading order and content using distinct available evidence. Check images, titles, notes, table cells/spans, repeated headers and cross-page connections. A region bounding box that merely covers the page does not prove that every line inside it was transcribed.
2. **Independent reference acceptance.** Freeze representative real-source pages and cross-page windows. Obtain independently checked reference transcription, structure and relationships; adjudicate ambiguous reference labels. Separate development, calibration and held-out acceptance by source/document where feasible. Test both the parser and the verifier on naturally occurring errors and clearly labelled injected omissions, altered numbers/negation, row shifts, wrong note bindings and reading-order errors. Seeded tests demonstrate detection behavior, not the real-world error frequency.
3. **Production QA.** Sample original-side areas as well as accepted output; create normal workbench tasks. Findings can reopen affected results and invalidate dependent deliveries. Retain original sampled versions and denominators.

A repeated call to the same extraction method, multiple agents repeating the same evidence, or rendering output to resemble a page does not establish independent verification. Agreement can be one signal but not the reference truth. Background masking and illustration exceptions must be challenged specifically on scanned pages so that legitimate text is not marked covered without being checked.

Report at least: original-region/line omission detection recall; verifier false-alarm rate and precision; character/word error; critical value/negation fidelity; table cell content and row/column/span accuracy; heading/note ownership; reading-order correctness; and cross-page association. Distinguish file/schema validity, structural consistency, source agreement, empirical error estimates and named human acceptance.

Public benchmarks are supplemental. [OmniDocBench's official project](https://github.com/opendatalab/OmniDocBench) provides annotated text, tables and reading order and associated evaluation methods. Select metrics applicable to this agreed scope; do not import an aggregate leaderboard score or unrelated formula/illustration transcription requirements as the project's completion criterion.

## 6. Requirement judgment and calibrated confidence

**PROPOSED B decision procedure:** establish usable source/context from A; inspect normative or recommendation language, document role, table column meaning, cross-references and exceptions; propose class and a concise source-cited reason; retain undetermined where evidence cannot resolve the class. Preserve advisory versus mandatory character without performing full System3 semantic completion.

Offline rules and source-template structure provide candidates and checkable constraints. Missing a keyword does not establish non-Requirement; finding one inside an example or note does not establish a Requirement. Optional agents use source-restricted evidence to suggest interpretations and critique alternatives. Their output passes through the same independent evaluation, acceptance policy and human-review rules. An API is optional, but equal automation rates across offline and API modes are not an acceptance assumption.

**CONFIRMED:** the user controls stage thresholds; the engineering design owns how meaningful scores are produced. Existing 95% defaults are a starting configuration, not demonstrated accuracy or a user-approved universal error budget.

**PROPOSED calibration procedure:**

1. Define what a correct item means separately for A text, coverage, structure/order, and B class, source association and subdivision. Label critical error categories explicitly.
2. Freeze method/version, configuration, evidence and raw predictions. Collect independent human reference labels, including negative classifications and difficult source regions, not only successful candidates.
3. Calibrate raw signals within supported format/language/stage scopes. A practical initial method is score bins with a conservative Wilson lower confidence bound on observed correctness, following the existing calibration foundation. Report sample support and uncertainty. This is a scoped empirical reliability estimate, not a proven probability for each new item.
4. Validate calibration and stage precision/recall on a separate held-out set. Distribution or method changes invalidate unsupported calibration. Tune thresholds on development/calibration data, not the final acceptance set.
5. Use the lowest necessary calibrated component to route the item, alongside hard blockers. Do not average away an omission or attach model self-reported certainty directly to acceptance. Missing evidence, uncalibrated scores, conflicts and unresolved human findings remain pending.

Threshold policy and empirical corpus quality are different. Measure Requirement precision and recall separately, including missed advisory Requirements. Non-Requirement exclusions also need justified decisions and coverage evaluation. Track automation coverage and human minutes per source/error category alongside accuracy; do not claim success by pushing virtually all items to humans.

**PROPOSED initial error policy:** any detected missing substantive region, altered critical number/unit/negation, incorrect row/column ownership or broken controlling footnote blocks its affected delivery. Held-out acceptance requires no observed unresolved critical defects in the tested scope, plus reported noncritical error measures and uncertainty. This does not claim zero errors on untested documents. Final numeric tolerances beyond user thresholds will be proposed from the first measured baseline and kept distinct from the user's confirmed requirements. Do not lower thresholds, hide defects or relabel difficult samples to manufacture completion.

## 7. Weekly QA

**CONFIRMED working schedule:** one batch each Monday in the configured business timezone, currently Europe/Oslo: System1 five source items, System2A twenty content checks, System2B five judgment checks. Counts are the user's initial specification; System3 remains inactive with no invented sample size. This document does not enable a scheduler.

**PROPOSED sampling:** use stable, frozen identifiers and source/result versions; sample without duplicates within a batch; show short/empty pools without claiming perfect accuracy. Each A check should include an original page or bounded region plus context so complete omissions can be seen. B's five checks should include both positive and negative machine judgments when available; an initial split of three positive and two negative cases is a proposal, not a confirmed user rule. Preserve the sampled category and population for interpretation. System1 QA does not overwrite earlier human decisions or turn all sources into a fresh intake review.

Create at most one batch per week; after downtime, generate the current week's missed batch rather than silently multiplying historical work. Incomplete QA stays visible until resolved. These are proposed scheduling semantics; confirm against actual operating needs during implementation. QA tasks use the same original comparison, correction, receipt and history workflow. Twenty/five weekly checks monitor quality; they do not by themselves establish high statistical confidence or a new calibration model.

## 8. Current evidence versus target

Read-only inspection during this discussion established the following implementation anchors, not live production acceptance:

| Area | Existing documented/code foundation | Target gap |
| --- | --- | --- |
| System1 persistence | Excel remains the source business-state store; the workbench already has its own session/request infrastructure. | Migrate source business state into its owning database without losing human decisions, then derive Excel. |
| System2 review | Workflow database, versioned corrections, two-stage gates and an indexed common workbench exist. | Align explicit A/B contracts with whole-table A ownership and provisional B subdivisions. |
| Excel | System2 already exports a managed register asynchronously; direct workbook edits are not imported. | Apply coherent one-way behavior across systems and verify event-to-export convergence and UX. |
| PDF | Page routing, completeness checks and bounded source-backed repair paths exist; current state records unfinished PDF fidelity and repair acceptance. | Demonstrate reliable independent verification, especially scanned pages, complex tables and omissions. |
| Requirement judgment | Offline proposals use normative wording and source item types and can return undetermined. | Context-sensitive classification, advisory classification quality, splitting and calibrated acceptance. |
| Confidence | Threshold gates and calibration plumbing exist. | Real independent calibration and held-out acceptance, not synthetic plumbing tests. |
| Optional intelligence | Bounded evidence suggestions have an adapter foundation. | The agreed multi-agent enhancement is a target; no working multi-agent orchestration or measured uplift was established here. |
| QA | Existing weekly QA has an earlier five-item policy. | Implement and validate weekly samples of 5 System1 items, 20 System2A checks and 5 System2B judgments, including representative source-side/negative coverage. |

Evidence pointers: [System1 state](../../system1/PROJECT_STATE.md), [System2 state](../../system2/PROJECT_STATE.md), [Workbench state](../../workbench/PROJECT_STATE.md), [System2 workbook contract](../../system2/docs/contracts/requirement-workbook.md), [classification implementation](../../system2/src/pdf_extraction/domains/requirements/classification.py), [acceptance implementation](../../system2/src/pdf_extraction/verification/acceptance.py), [calibration implementation](../../system2/src/pdf_extraction/verification/calibration.py), [completeness implementation](../../system2/src/pdf_extraction/validate/completeness_gate.py), [optional-assistance contract](../../system2/docs/contracts/optional-assistance.md).

## 9. Proposed implementation sequence

Only the next checkpoint is detailed; later steps remain subject to evidence. This plan is not authorization to resume implementation during the current documentation-only turn.

### Next checkpoint: bound the verification and review contracts

- Question: can an independent source comparison find meaningful A failures and carry them through correction to effective output, B invalidation and an Excel snapshot?
- Inspect and reuse the current parser, verification, review and export interfaces; record which findings come from independent evidence and which are self-consistency checks.
- Freeze a small pilot containing a native-text page, scanned page, mixed-content page, complex table, cross-page table and a figure with caption. Include naturally occurring defects and clearly distinguished seeded failures; no full-corpus or external-model run is implied.
- Define reference labels and A/B item identities, including the source parent and derived children. Keep splitting isolated behind an explicit provisional policy.
- Run the verification module against the original and output; measure detected/missed defects and spurious findings. Exercise one text omission, one table/footnote error and one B misclassification through the normal workbench in isolated data.
- Success: localized evidence, correct scope and before/after results; no lost source/history; unresolved regions cannot silently pass; save retries do not duplicate decisions; database and derived Excel versions converge. Report measured reviewer effort.
- If coverage remains dependent on the same extraction evidence or whole-region masks hide missing text, ADJUST the verifier before extending automated acceptance. If a schema cannot preserve source context, BACKTRACK to the representation contract. Do not scale a failed pilot.

### Subsequent horizons

1. Complete System1 database migration on isolated copies with full business-state/history parity and rollback evidence; move over only after the migration gate passes. Preserve paid-source Pending work and existing source selection.
2. Complete A content representation and repair, especially tables, notes and cross-page structures; implement all-content preservation and illustration handling. Run independent source-based acceptance.
3. Complete B classification and provisional parent/child output with positive/negative reference samples; validate no source text is invented and recommendations are treated as agreed.
4. Calibrate confidence and implement weekly QA with 5 System1 items, 20 System2A checks and 5 System2B judgments. Verify offline completion, stage routing and unresolved-case visibility.
5. Add optional multi-agent enhancement behind the same interfaces. Evaluate against the offline baseline on identical frozen sources, reporting accuracy, human workload, latency and API cost. Retain the offline path if measured uplift is absent.
6. Complete unified workbench usability and database/Excel performance acceptance throughout these steps; perform a final end-to-end current-scope audit. System3 stays deferred.

## 10. Acceptance contract

| Gate | Evidence required to call the scoped gate complete |
| --- | --- |
| Source preservation | Existing selected sources, named decisions, pending issues, original hashes and historical records survive migration unchanged; no repeated blanket eligibility review. |
| A fidelity | Independent source comparison covers text, auxiliaries, order, hierarchy, images/captions, table cells/spans/notes and cross-page scope. Unchecked/failed parts are visible. Held-out metrics and critical-error findings are reported by category. |
| Verifier reliability | Independent labelled cases measure both missed defects and false alarms. Naturally occurring and injected defect results are distinguished. No claim of universal correctness from a clean sample. |
| B quality | Reference-labelled mandatory and advisory positives, context/negative examples and difficult cases support precision/recall and provenance checks. Parent/child rules stay marked provisional until confirmed. |
| Confidence | Versioned, scoped calibration plus independent held-out results; no automatic acceptance from unsupported model confidence; hard blockers override scores. |
| Human loop | A reviewer can find the original, understand the question, supplement/correct, confirm and see saved history through the one workbench. Drafts and incomplete work cannot masquerade as completed items. |
| Persistence/export | Save success survives restart/retry; no duplicate decision or overwritten newer state; Excel automatically converges to a consistent saved version, with visible lag/failure and preserved last valid snapshot. No Excel import path. |
| Usability/performance | Measure list/detail load, durable save, Excel convergence, peak memory and human actions/time on declared hardware and representative sources. No synchronous full-document export on normal list reads. |
| QA | Each Monday, target 5 System1 items, 20 System2A checks and 5 System2B judgments; record shortages and original versions, and create actionable workbench tasks. Source-side omissions and negative B judgments are represented. |
| API independence | With provider disabled or unavailable, local processing, verification, manual correction and delivery remain usable. API mode cannot bypass confidence, history or human decisions. |
| Scope discipline | No System3 implementation, evidence-workstream takeover, autonomous code-writing agents, undisclosed external transmission, or declaration of complete source accuracy based solely on regression tests. |

**PROPOSED performance starting targets**, to be benchmarked rather than reported as existing guarantees: p95 pending-list response within 1 second; selected-item evidence display within 2 seconds for a declared representative page/table; durable review acknowledgment within 2 seconds independent of Excel; an ordinary coalesced Excel export converges within 60 seconds after the last edit when its file is writable. Large-document or locked-file cases show explicit pending/progress state and separate measured convergence. These values are engineering proposals; they are not user-approved acceptance thresholds. First measurements establish workload bounds and justify any revision.

Overall completion requires all applicable gates for the declared source scope. A successfully generated workbook, green tests, attractive UI, API connection or a high mean score alone is insufficient. Report unresolved scope and evidence limitations explicitly.

## 11. Reusable goal prompt

This execution-goal template was clarified on 2026-09-10. Reviewing, quoting or editing it does not start a goal or authorize implementation. It takes effect when the user explicitly assigns it as an implementation goal. Stage sample counts below are quantities, not a date.

> Implement and validate the agreed aquaculture Requirement Workstream within its declared source scope, bringing System1, System2A and System2B to the acceptance gates in the target specification. Do not stop at a plan, generated artifacts or passing regression tests.
>
> Start at the active workstream root, locally named `05_Working area of requirements side/`. Read `AGENTS.md`, `README.md`, `PROJECT_STATE.md`, `docs/design/requirement-workstream-target.md`, `docs/design/decision-boundaries.md`, and the relevant component state/environment documents. Preserve CONFIRMED constraints, implement PROVISIONAL splitting as reversible policy, and validate PROPOSED engineering choices with evidence. Do not treat a future target as already implemented behavior.
>
> When I explicitly start this implementation goal, that instruction authorizes in-scope reversible local development and appropriate validation. First reconcile actual code and evidence with the target and report the next bounded checkpoint, then proceed without requiring approval of every routine step. Continue using adaptive planning until the agreed scope passes its acceptance gates or a specific unresolved dependency prevents further progress. Existing explicit authorization requirements for protected actions remain in force. Preserve original files, source selections, paid/access pending issues, named human decisions, evidence and history. Do not reopen the completed source-review batch or broaden source discovery merely to satisfy this goal.
>
> Deliver System1 business-state database authority with one-way Excel output; System2A faithful full-content reconstruction, original-bound corrections and independently evaluated verification; and System2B source-grounded Requirement identification, including recommendations and provisional parent-linked subitems. Preserve whole-table structure, notes, order and evidence in A; perform Requirement selection and subdivision in B. Defer System3 semantics. Use the single shared human workbench, stage-specific calibrated confidence, durable named decisions, completed Pending-to-history transitions, and automatic asynchronous versioned Excel synchronization. Direct Excel edits must not write back into authoritative state.
>
> Implement the weekly QA policy: each Monday, sample 5 System1 source items, 20 System2A content checks and 5 System2B classification checks for human review in the same workbench. These are sample counts, not a calendar date. A sampling must be able to discover original content with no extracted counterpart; B sampling must include negative classifications as well as Requirements. Record short pools and unfinished QA honestly. Live scheduler activation remains subject to the project's explicit authorization boundary.
>
> Keep a usable no-external-API workflow. Optional runtime multi-agent assistance may call program capabilities to improve processing and checking, but must obey the same confidence and human-review gates. The restriction on autonomous code modification/deployment applies to those runtime product agents; it does not prohibit the development Agent from implementing and testing this authorized engineering goal. Do not activate providers or transmit protected evidence without the applicable authorization.
>
> Validate the parser, independent verifier and Requirement classifier on independent real-source references. Separate calibration from held-out acceptance. Measure source fidelity, verifier missed defects and false alarms, Requirement precision/recall, automation coverage, human workload, performance and database/Excel consistency. User-configurable thresholds and existing defaults are not proven accuracy. Propose justified numerical tolerances from pilot evidence and label them as proposals; do not lower gates, hide unresolved work or route everything to humans to manufacture success.
>
> Keep collaborator-dependent splitting decisions explicitly provisional. Continue unaffected work when a decision is pending. At each checkpoint, report scope, evidence, failures and the next decision; update the owning state files after verified changes. Full goal completion requires all applicable acceptance gates for the declared scope. If independent labels, collaborator acceptance or another required input is missing, preserve the incomplete status and state the smallest outstanding input instead of declaring completion.
