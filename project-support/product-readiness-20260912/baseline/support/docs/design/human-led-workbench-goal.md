# Human-led, material-centered workbench: target and acceptance

Alignment date: 2026-09-11. Status: **ACTIVATED by explicit user assignment on 2026-09-11; bounded implementation/acceptance recorded in the current state and acceptance report.** The preparation statements in section10 describe the earlier documentation-only checkpoint. This document is the canonical new product target; the [goal prompt](human-led-workbench-goal-prompt.txt) activates work against it and does not maintain a competing specification. Actual implementation/activation belongs to [integration state](../../PROJECT_STATE.md) and component states.

This target supersedes the automation-first emphasis and default review-interface structure of the [September 10 target](requirement-workstream-target.md) and the [stage v2 quality goal](requirement-workstream-stage-goal-v2.md). Their measured results and unfinished quality gates remain historical evidence, not retroactive successes. Preserve source, evidence, confidentiality, history and human-authority protections. Existing runtime contracts remain descriptions of deployed behavior until a verified transition.

## 1. Outcome and scope

Deliver a usable local workbench organized around **one material at a time**. System1 continues source management. In the shared workbench, the reviewer selects a governed material, reads its original, explicitly requests extraction, corrects and reviews the extracted content, saves work and confirms the reviewed material version. A reserved third pane will later turn confirmed content into precise structured Requirements.

The user's priority is human processing and review. Existing parsing/checking programs become assistance behind explicit buttons. High machine confidence or a completed parser run cannot replace human review in the new workflow. Improve machine routines only where needed for a usable extraction/correction path; do not resume an open-ended automatic-accuracy campaign as the main objective.

The old System2/System3 workbench screens are not a design constraint. Reuse useful services, evidence readers, correction primitives and persistence, but redesign the normal interaction around the three panes. Preserve existing records and recoverability; permission to replace an interface is not permission to delete its underlying history.

**Current implementation scope:** the material-centered workspace, original readers, explicit original-to-content extraction, middle-pane correction and confirmation, durable material-level save/resume/history, human-led server-side completion rules, and an honest unconnected third-pane boundary. **Deferred:** the user's precise nested Requirement schema, final Requirement forms and actual middle-to-right semantic processor. Missing deferred parts do not block this bounded workbench goal, but cannot be reported as completed capabilities.

## 2. Confirmed decisions and proposed mechanisms

### 2.1 Confirmed by the user

- Keep System1 source management; do not redesign or repeat completed source decisions.
- One normal shared workbench, collapsible navigation and three working panes: **Original document**, **Extracted original text**, **Structured requirements**.
- Read PDF, HTML and Excel originals in the left pane with scrolling and text selection/copy where supported.
- Place separate **Extract** and **Process** actions between adjacent panes. Without a conversion action, downstream content must not change automatically.
- Let reviewers correct extracted text, hierarchy and missing content, including tables and images.
- Present future Requirements as visual forms; persist their information in a nested structure rather than asking people to edit raw dictionaries or lists.
- The user will provide that nested schema later. Leave the third-stage processor empty for now, but design for its later integration.
- Preserve already completed human work and flag conflicts when upstream corrections affect it.
- Use each material as the unit of work, saving and review completion.
- Prepare the goal and project documents now; do not create/start a Codex goal or implement the application in this preparation task.

### 2.2 Engineering design defaults

The version model, partial-scope review, interaction details, adapter envelope and validation methods below are proposed ways to implement the confirmed needs. They are not claims of existing capabilities or user-specified storage technology. Routine reversible choices may be refined after inspection when the implementation goal is assigned.

## 3. Material-centered daily workflow

1. Open the material list and select a System1-governed source snapshot. Show its title, format, version, saved progress and actual content-review status. Keep material counts separate from block/Requirement counts.
2. Enter the three-pane workspace for that material. The active material and version stay visible. A new snapshot of the same source starts a new versioned workspace without discarding prior work.
3. Inspect the original. Click Extract to request a candidate from the existing appropriate parser. Show running, partial, failed and candidate-available states honestly. Viewing or switching panes starts no jobs.
4. Review and correct the middle pane against the original, including omissions and structure. Save draft work at any point, including after a partial extraction or a failure.
5. **Save material** durably saves that material's current edits and review progress. Distinguish unsaved, saving, saved and save failed. Saving never means that review is complete. Autosave may supplement this explicit action but cannot remove visible save state or replace explicit confirmation.
6. **Confirm content review** records a named human confirmation bound to the complete reviewed material version. Optional chapter/range confirmations accumulate as progress; the material is content-confirmed only when its required full scope and dependencies are reviewed, omissions addressed and unresolved substantive issues cleared.
7. Close/switch and later reopen the same material with saved work and review status recovered. Prompt to save or stay when unsaved changes would be lost. Switching between two materials must never leak drafts, selections or results across their identities.
8. The future Process action uses confirmed content to produce a separate Requirement candidate. In this phase it is disabled with an explanation; content-confirmed materials display **Content review complete · Requirement structuring not connected**, not an end-to-end Complete badge.

A material is the user-facing work unit. Internally, stable source/snapshot identities, content blocks, review ranges and versions support efficient partial edits; users need not manage opaque internal IDs. Group complete and in-progress materials separately and allow opening saved/confirmed versions and their history. Business reviews remain the named reviewers' responsibility; engineering completion does not require clearing the real material queue.

## 4. Three-pane workspace

Keep the existing light English interface and original-language source text. Use independently scrollable, resizable panes under a compact material/actor/save bar. Keep all three panes visible at practical desktop widths; at narrow widths use clear pane switching instead of shrinking text or clipping actions. Collapsing navigation must preserve the active material and draft.

| Pane | Required experience | Boundary |
| --- | --- | --- |
| Original document | Whole-material reading, location navigation, zoom, selection/copy as supported and clear source-version identity. | Read-only original. Never substitute a current remote website for a saved source version. |
| Extracted original text | Ordered text blocks, headings, tables, images and source links; readable inline editing; hierarchy/order correction; add omitted content; explicit material save and review confirmation. | Human edits are a versioned effective layer, separate from the original and parser candidate. |
| Structured requirements | Reserved pane with future-purpose explanation and actual connection status. | Initially `Not connected — structure and processor pending`; Process disabled with a visible reason. No invented form schema or fake processing success. |

Place Extract and Process on the respective pane boundaries or adjoining headers rather than adding a fourth working column. Prefer a pencil or Edit label to a cross that can mean Delete. Keep routine forms and table controls free of raw JSON, parser diagnostics and confidence-heavy technical details. Diagnostics may live in secondary disclosure panels.

### 4.1 Format-specific original reading

- **PDF:** full original paging/continuous scrolling, zoom and copying native text where present. Scanned content needs an explicitly identified OCR assistance layer for copying; copied OCR is not verified original truth. Do not promise selectable text from a raster-only preview. Provide a manual transcription/supplement path and retain the page image for comparison. Native text also needs visible-source checking when text and rendered appearance conflict.
- **HTML:** render a useful isolated view of the registered snapshot, preserving headings/tables and selectable text. Strip active/external content, sandbox the preview and disclose missing assets or fidelity limits. Retain the untouched downloadable original. No live fetching merely to view a stored document.
- **Excel:** worksheet switching, continuous row/column navigation, selectable cell text, recognizable addresses and preserved merged-cell relationships. Distinguish stored formulas and saved values, disclose unavailable caches/hidden-content limitations, and avoid claiming native styling fidelity without evidence. A fixed page of flattened cells is not the requested reading experience. Retain the explicit compatibility path for legacy XLS; do not silently convert or alter an original.

Selecting a middle-pane block should offer navigation to its original page, HTML location or sheet/cell range. Manual scrolling remains independent. Unsupported locations are disclosed; do not guess a page or region. Original incompleteness/access problems remain linked to System1 source follow-up, not silently repaired by fabricated extraction.

### 4.2 Human correction and completeness

Support correcting text and block type, heading level/parent, reading order, mistaken split/merge boundaries, omitted paragraphs, tables and images. Retain source numbering separately from generated labels. Table editing must preserve rows, columns, cell values, merged relationships and linked notes; images use original-bound regions or explicitly attributed local attachments, not generated illustrations presented as evidence. Preserve full-content coverage rather than filtering to likely Requirements in the middle pane.

Every correction has provenance and history, with a recoverable earlier version. Review must include original ranges where extraction found no blocks, otherwise omissions can disappear from the review queue. Completion cannot be derived solely from accepting all machine-produced items. Unknown machine scores do not prevent a human from confirming checked content, but unresolved source/content issues do.

## 5. Save, version and conflict model

The user requires button-only conversion and preservation of reviewed work. Implement these as separate concerns: conversion changes candidate content only on explicit action; upstream edits can immediately change **staleness metadata**, never silently rewrite the downstream body.

1. Keep immutable source snapshots, parser candidates, human drafts, confirmed content snapshots and future confirmed Requirement snapshots distinct. Use the existing owning stores and audit patterns where feasible; do not introduce another authority for System1 sources.
2. Extract captures the original version and produces a middle candidate. Re-extraction compares with current corrections instead of replacing them. First-run and repeated-run adoption behavior must be explicit in the interface.
3. Future Process captures a confirmed input revision and scope, including headings/tables/notes/context dependencies. It produces a separate right-pane candidate. A confirmed chapter/range can be processed independently when its dependency closure is confirmed; whole-material completion remains a separate full-scope action.
4. A middle edit retains right-pane values and historical confirmations but marks affected items as requiring reconciliation. Old confirmed versions remain available as history. The current material cannot claim final structured completion while required reconciliation is unresolved.
5. Record stable block identities and dependencies. Heading, ordering, table, footnote and location changes may affect descendants and linked Requirements even without body-text changes. Deletion/split/merge requires explicit association review. If impact cannot be established safely, widen the review scope and explain why.
6. Compare the previous input/candidate, current human result and new input/candidate. Use field-level differences only for reliable mappings. Offer Keep, Adopt and Edit/merge. Keeping an existing value requires checking it against the new evidence and recording renewed confirmation; a reason alone cannot waive a factual conflict.
7. Preserve unaffected items and manual changes. A processor's omission cannot silently delete a Requirement. New/missing/ambiguous entries remain visible until resolved.
8. If upstream edits arrive during a processing job, retain its result bound to the captured older revision and label it stale. Do not adopt it automatically or relabel it as current.
9. Preserve unsaved drafts through stale-write conflicts. Use server-bound actors, optimistic guards and durable idempotent receipts. Retrying an uncertain save/job must not duplicate revisions, decisions or jobs. Respect existing locks and component environments.
10. Draft saves, candidate adoption, content confirmation, Requirement confirmation and exported output are distinct operations/statuses. Existing Excel output stays one-way; there is no Excel review-input path. Retain the last valid version and distinguish current/partial/stale/historical data.

Suggested material statuses: Not extracted, Extraction running, Content draft, Content review in progress, Content review complete. Requirement status is separate: Not connected in this phase; later Draft, Needs review, Needs reconciliation or Confirmed. Technical failure is reported separately from review progress so already saved work remains discoverable.

## 6. Verified code baseline and adaptation map

The following is **source-inspected evidence**, not a fresh browser/runtime acceptance result. Existing state documents provide dated, scoped runtime evidence; recheck before implementation.

| Component | Current evidence | Required adaptation |
| --- | --- | --- |
| [Evidence reader](../../workbench/ui/evidence-viewer.js) | Complete PDF iframe, isolated HTML-region support, text fallback and worksheet/cell-window preview. | Reuse left-pane evidence binding; complete safe HTML and continuous Excel reading; validate real copy/location behavior by format. |
| [Extraction UI](../../workbench/ui/extraction.js) | Source selection, explicit Start processing, content/Requirement queues, corrections and drafts. | Replace the queue-first normal experience with a material list and three-pane workspace. Preserve useful repair/history behavior rather than preserving the old layout. |
| [Workbench server](../../workbench/src/local_workbench/server.py) | Guarded start/control/decision routes with server-owned actor identity and allowed fields. | Reuse security/receipt boundaries; expose material-level saves, confirmation and explicit candidate actions. |
| [Extraction runner](../../system2/src/pdf_extraction/orchestration/workflow.py) | Governed intake and explicit jobs using current parsing programs. | Connect appropriate existing parsers behind Extract; keep parser candidates separate from human correction/adoption. |
| [Review workflow](../../system2/src/pdf_extraction/review/workflow.py) | Revisions, drafts, history and dependencies exist. Recompute also invokes classification, evaluates machine/human acceptance and updates output. | Decouple automatic recomputation from button-triggered downstream generation. Enforce human confirmation in the owning service; hiding automation controls or raising thresholds is insufficient. |
| [Requirement domain conversion](../../system2/src/pdf_extraction/domains/requirements/canonical.py) | Some evidence-linked action/applicability/domain fields already exist. | Audit reuse after the actual schema arrives. Existing classification/partial fields do not implement the requested precise nested transformation. |
| [System3 state](../../system3/PROJECT_STATE.md) | Design and a versioned input feed exist; no semantic consumer is recorded as running. | Reserve the right-pane interface. Do not present UI consolidation as a implemented semantic service or move modules merely to match pane numbers. |

The new experience is not a CSS-only change. Existing automatic acceptance/output coupling must be adapted and tested for the new workflow. Preserve legacy history and compatibility entry points until a reversible replacement is verified. Historical machine-only acceptance must not be silently relabeled as a new human confirmation; display its provenance and review requirement when bringing it into the new workspace.

## 7. Future Requirement processor interface

Reserve a small, versioned adapter and capability contract. No actual semantic algorithm, final domain schema, third-stage service or unused environment is required now.

- **Capability:** connected/not connected, supported operation and schema versions. Initially unavailable; a real processing request must return a clear unavailable state without changing results or claiming success.
- **Input envelope:** source/snapshot identity, confirmed content revision and selected scope, ordered blocks and dependencies, evidence references, requested schema version and request identity. Nested Python dictionaries/lists can be serialized through a JSON-compatible boundary; they do not dictate the database technology.
- **Output envelope:** exact input revision, processor/schema version, candidate payload, evidence mappings, warnings, unresolved/unmapped coverage and actual run state. Empty, partial, failed and unavailable results remain distinct.
- **Human adoption:** separate guarded operations save edited candidates and confirm them. The processor cannot directly write human-confirmed values or acceptance.
- **Schema evolution:** preserve old values, evidence and human edits. Unknown/unmapped fields remain recoverable; future migrations need explicit versions and validation. Do not fix actor/action/modality nesting or other domain fields from the user's examples alone.

The third pane may eventually combine earlier System2B identification and intended System3 enrichment in one form-based step. Functional reuse and interface placement are confirmed directions; final module/service boundaries depend on the supplied schema. Evidence collection, site-instance grounding and final compliance decisions are not added to scope.

## 8. Bounded implementation strategy

When the user assigns the goal, inspect current source, environments, applicable rules and actual runtime before editing. Establish a preservation baseline and implement in small reviewable increments using the existing normal workbench. Maintain a short rolling plan in the existing plans area; do not carry forward the old quality goal's expired clock, presentation deliverables or usage-reset permission.

1. **Material workflow and shell:** list/open/resume one material, collapsible navigation, three panes and honest third-pane status. Validate an early rendered skeleton before polishing.
2. **Readers and correction:** provide usable original views and middle editing through existing source-bound primitives. Verify paragraphs, hierarchy, tables and image supplements; avoid raw-structure editing in the normal UI.
3. **Extraction and persistence:** wire Extract, explicit candidate adoption, durable material save and full-scope human confirmation. Decouple unintended downstream generation; protect historical/manual results.
4. **Recovery and evolution:** verify stale input, repeated requests, failed/partial extraction, concurrent saves, re-extraction conflicts and material isolation. Exercise future-contract rejection and generic version/adoption invariants with clearly labeled isolated fixtures, without pretending a third-stage processor exists.
5. **Handoff:** validate representative native PDF, existing scanned/mixed controls, HTML and Excel paths; inspect actual rendered screens and recovery. Update code/interface documentation, actual feature status, evidence and launch instructions. Distinguish source implemented, isolatedly exercised and loaded in the normal instance.

Do not rerun every full production PDF merely to verify an interface. Use small existing non-confidential samples and isolated stores, retaining real versus synthetic evidence labels. Follow existing protected boundaries for costly whole-document runs, native Excel acceptance, external actions and normal-instance transitions. Complete safe implementation and preparation before seeking any genuinely required protected final action.

## 9. Acceptance and definition of done

Every in-scope requirement must have actual evidence; a static mockup or passing internal tests alone is insufficient. Suggested acceptance scenarios:

| ID | Scenario and required evidence |
| --- | --- |
| M1 | Two materials can be opened, saved, switched and resumed independently; no cross-material draft/result leakage; clear current snapshot. |
| U1 | Three working panes and collapsible navigation are usable at normal desktop sizes; independent scrolling, readable text, accessible editing and narrow-screen behavior are inspected in a real browser. |
| R1 | PDF, HTML and Excel originals are readable with tested selection/copy where supported. Scan/OCR, asset and formula/cache limitations are disclosed with a usable manual path. |
| E1 | Viewing, scrolling, saving and confirming do not trigger extraction or Requirement processing. Extract runs the real existing appropriate parser and returns a correctly bound candidate. Repeated requests do not duplicate work. |
| C1 | A reviewer can correct text, hierarchy/order, a table and missing image/text content in the interface; corrections persist and retain source evidence and history. |
| S1 | Save succeeds durably or shows failure; drafts survive reopen/service restart; stale/concurrent saves preserve work and cannot overwrite a newer revision. Test on isolated owning stores. |
| H1 | Save and Confirm review are distinct. Unknown/high machine confidence alone never completes material review. Full-scope omission/dependency checks and named human confirmation are required, including original ranges with no extracted items. |
| V1 | Re-extraction and source-version changes retain human corrections and old confirmations; present candidate differences/conflicts and current-versus-historical status. Partial or stale results cannot become current automatically. |
| F1 | The third pane is visibly unconnected, Process cannot fabricate success, and the versioned adapter contract records future input/output/adoption/error behavior. Deferred domain fields are not invented. |
| P1 | System1 authority, original files, immutable Canonical artifacts and prior decisions/history survive. Existing compatibility/output paths are not silently broken; old machine decisions are not relabeled human. |
| D1 | Updated guide, actual status, runnable entry, representative browser evidence and targeted behavior tests identify what is implemented, loaded and deferred. Engineers do not complete real reviews on behalf of business owners. |

**Goal completion:** deliver and verify the current-scope human workbench and dormant extension boundary, with all applicable rows above satisfied. Absence of the user's future schema/processor does not block this bounded goal; absence of a required reader, save/review flow or integrity guarantee does. A local engineering fixture is validation evidence, not a real business review. An unavailable protected deployment/acceptance step must be reported precisely rather than converted into a PASS.

**Material completion:** content review can complete independently of future Requirement structuring. Overall structured-Requirement completion remains unavailable until that capability exists and the actual material's human review is done.

**Not new completion gates:** universal PDF correctness, formally calibrated automatic release, a cleared production queue, Canva/Sites publication, expanded source discovery, new providers or schedules. Existing quality defects remain visible where they affect reviewer effort or a safe manual path.

## 10. Authorization and preparation record

This conversation authorized preparation of the new goal prompt and project updates only. No Codex goal is created or started by preparing these files. Future explicit goal assignment authorizes necessary reversible local implementation and proportionate isolated validation within this scope; it does not silently authorize publishing, messages, commits/pushes, external document transmission, new models/schedules, destructive history changes or spending usage-reset credits. Do not import one-off permissions from the earlier goal.

Prepared in this checkpoint: the new target, its activation prompt, entry/state links and supersession notices. Source interfaces and their automatic-recompute coupling were inspected. Application code, dependencies, business stores, original files, parser jobs, running services, thresholds and schedules were not changed. This is a design/preparation outcome, not a workbench implementation or a new quality result.
