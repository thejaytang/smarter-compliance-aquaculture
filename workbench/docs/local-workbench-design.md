# Local Unified Review Workbench Design

Date: 2026-09-07. Status: System1’s browser workbench is implemented; System2/3 remain design and future-interface work. Current platform facts belong to [Workbench state](../PROJECT_STATE.md); usage is in the [user guide](../USER_GUIDE.md). This document distinguishes target design from historical demos; demonstrations do not establish production integration.

Current Excel boundary: the System1 workbook retains authoritative source state and opens the updated Instructions. The old Dashboard and Human Operation Desktop are `veryHidden` compatibility and history stores. Daily dashboards, tasks and review history use the browser. Action chains below that are not marked implemented are design targets, not replacements for the current guide. For example, saving a corrected URL currently updates register information without retrieving the original again.

## 1. Design decision and scope

The workbench is the shared workspace for the entire Requirement workflow across System1, System2 and System3. Overview and common review capabilities belong to the platform, not to an auxiliary System1 page. Double-clicking the entry starts the local service and opens the browser. The shared entry includes overview, all three systems and operator selection. The interface presents evidence and receives decisions; each system retains business judgments and authoritative data.

The user accepted System2 reading effective local System1 snapshots and Canonical JSON storing authoritative parsing facts. They also requested a browser replacing daily Excel review, system-specific task areas, visual Dashboard, one-time operator selection and automatic processing after actions. Implemented System1 access and Dashboard behavior are defined by platform state and source code; System2/3 details still require validation against real interfaces.

First-version assumption: one trusted local work computer with switchable operators, without multi-user LAN login. The launcher targets current macOS first; Windows requires separate validation. System1 is implemented in the local browser. Login startup is disabled.

In the target experience, Excel is an export and communication format. During transition, System1 still stores business state in the production workbook. Moving state completely out of Excel is a separate migration, not part of the initial interface release.

## 2. Information architecture

| Area | Main question | Content and actions |
| --- | --- | --- |
| Overview | Where is each stage, and what needs human action? | Three system statuses, pending counts in their own units, key outputs, work entries and five-week sampling trends. System1 source details collapse within its area. Unconnected metrics remain blank and labeled; demo activity does not count as progress. |
| System1 · Source management | Should a source be included, and are its original and metadata correct? | One aggregated task per source: selection, candidates, manual files, exceptions and Random QA, with explicit action-specific buttons. |
| System2 · Extraction review | Is extracted content faithful to the original, with no omissions? | File-processing status, item/field review, source comparison, document completeness, versions and exports. |
| System3 · Semantic completion | Are types, conditions and actions supported by sufficient source evidence? | Initially labeled as design work; later field gaps, ambiguity and consumer feedback, without invented tasks or compliance conclusions. |
| Operator | Who is reviewing now? | Enter/select a name once, show the current operator continuously, and allow switching or exit. History retains the identity used at the time. |

The sidebar expands as System → Pending review / Review history, using indentation and vertical lines for hierarchy. System-specific tasks do not mix into an indistinguishable list. Overview may aggregate compatible counts, but System1 counts sources while System2 lists files and review items separately; their sum must not be called files.

## 3. Core review pages

### Minimal review revision | 2026-09-07

Principle: each task directly provides the evidence and actions required for its judgment. Simplicity reduces searching, switching, form filling and mistakes; it does not remove essential tools and transfer their work to the operator.

Initial sketch issues and changes:

| Issue | Change |
| --- | --- |
| A review reason without a specific judgment question | One sentence at the top states what to decide, what to compare and the completion criterion. |
| No direct entry to the original | Explicit `official_url` and `retrieval_url` links open in new tabs, preserving the task; show publisher domain and target version. |
| The same edit/Accept form for every task | Use source verification, replacement-file submission or extraction comparison according to task type. Buttons name the actual decision. |
| Statistics occupy review space | Keep most statistics in overview; review pages show unresolved/completed counts and exceptional blockers. |
| Persistent notes and technical details distract | Collapse notes unless populated or required; place versions, hashes and logs in evidence details. |
| Deferring leaves the same item open | Advance to the next unresolved item while retaining the deferred task in pending counts. |
| No convenient recovery after confirmation | Reopen recent decisions through a new event, without deleting review history. |

### Required actions by task type

- **Source verification**: route issues to scoring, link correction, provenance, version/duplicate handling or sampling. Show source title, publisher/domain, target version/language and direct official-page/original links. Visiting a link does not automatically complete verification.
- **Manual file submission**: acquisition entry → select/drop file → automatic basic checks → original preview and identity check → submit full validation with acceptance intent → automatic acceptance after validation passes. Merge identical official-page and direct-file links. Restricted resources link to official acquisition; a payment page is not a direct download.
- **Extraction accuracy**: show exact source pages/paragraphs/cells with context and highlighted differences. State confirmation scope and provide correction and missing-content actions. Distinguish the current online version from the local snapshot used for this run; compare against that snapshot by default.

### System1: routing by source issue | 2026-09-07

The user confirmed that System1’s core is source management. Scoring is itself a human judgment and must not require another Accept afterward. The interface uses one aggregated task per source, retaining multiple independent issues and states inside it. Existing `operation_type` is coarse; the frontend combines `issue_codes`, file state and candidate metadata to select interactions instead of exposing a generic APPLY/RETURN form.

| Issue and trigger | Evidence shown | Action and automatic follow-up |
| --- | --- | --- |
| Missing/damaged/mismatched original: `MISSING_FILE`, `REGISTRY_FILE_MISMATCH`, manual replacement | Target title, format, version, language, official acquisition link and current valid snapshot. | Upload/drop, validate and check identity as needed. “Submit full validation” expresses human intent to accept this candidate original; passing checks accept it automatically without another Accept. Failures explain recovery and preserve the old snapshot. |
| Pending inclusion: `SELECTION_PENDING` | Five defined dimensions, score meanings, source evidence, existing scores and provenance. | Select H/M/L for every criterion. The final selection submits the scoring decision and recalculates selection automatically, without another Accept. |
| Missing URL or download failure: `MISSING_OFFICIAL_URL`, `MISSING_RETRIEVAL_URL`, `DOWNLOAD_FAILURE` | Previous URL, failure time/reason, title, publisher, target version, official entry and existing snapshot. | Enter the correct URL and use the proposed “Check link and retrieve again” action, applying after target verification. Alternatives are uploading, deferring with a reason or excluding with a reason. A download failure does not imply irrelevance. |
| Payment/login/licence blocker: `PAYWALL_BLOCKED` | Official acquisition entry, restriction and existing permission information. | An authorized person obtains and uploads the file or supplies permission evidence; otherwise keep it pending. Avoid repeated futile retries and treating a restriction page as the original. |
| Unconfirmed identity/provenance/applicability: `PROVENANCE_UNVERIFIED`, `APPLICABILITY_UNCONFIRMED` | Known publisher, acquisition channel, provenance and applicability, with missing fields highlighted. | Fill missing fields only and attach proof when needed. “Save evidence and verify” rechecks affected conditions only. Equipment/OEM originals retain supplier, applicability and inclusion-rationale gates. |
| New source candidate: `NEW_SOURCE_CANDIDATE` | Candidate, discovery channel, identity and similar registered sources. | Confirm identity/ownership first. A new candidate still needs named human acceptance, expressed as “Register this source and begin assessment”; completed five-criterion scoring then applies automatically. Identity acceptance and inclusion judgment remain separate. |
| Duplicate/version change: `POSSIBLE_DUPLICATE`, `DUPLICATE_OFFICIAL_URL`, `ROLLING_CONTENT_CHANGED` | Side-by-side sources or versions, with titles, IDs, versions, dates, differences and current primary source. | Choose same/different source or use/retain version, adding a reason when needed. Preserve old IDs, versions and relationships. Matching URLs alone do not justify merging; latest does not necessarily mean the required version. |
| Random sampling: `RANDOM_QA_CHECK`, `RANDOM_QA_FAILURE` | Sampling scope, registered values, corresponding original and evidence locations. | “Information matches the original” records the QA decision. An error selects its type and opens correction within the same source. The issue persists until correction and verification pass. |
| Lock, stale page or program failure | Specific blocker and current revision. | Wait for Excel release and resume; preserve stale-decision drafts for renewed comparison; offer retry for program failures. Scoring or Accept must not be used to dismiss these errors. |

`SOURCE_REVIEW` may contain link, original and scoring issues simultaneously. Obtain evidence needed for judgment first. If evidence already suffices, scoring may precede replacement of the original. Expand one main action at a time and show remaining issues alongside it, without creating duplicate sources. Completed scoring need not repeat unless source/evidence revisions invalidate the judgment.

### Five-criterion scoring and automatic application contract

The existing [selection implementation](../../system1/Code/src/source_updater.py), including `SCORE_FIELDS` and `selection_from_scores`, and the production workbook’s `Categories` were checked:

| Field | Interface label | What the operator checks |
| --- | --- | --- |
| `authority_quality` | Authority | Publisher and document status. |
| `scope_relevance` | Scope relevance | Project scope, applicable entities, jurisdiction and inclusion rationale. |
| `version_currency` | Version currency | Target version, date and supersession relationships. |
| `traceability` | Traceability | Exact provenance, source version and acquisition record. |
| `access_permission` | Access permission | Acquisition and usage basis. |

Existing H means verified with sufficient evidence; M means potentially suitable but requiring confirmation; L means unsuitable or clearly insufficient evidence. Interface questions are prompts, not new score thresholds. `automation_readiness` is outside these five selection gates and only informs acquisition/processing methods.

1. Each score requires explicit human selection. Old scores and machine suggestions may be shown but cannot count as confirmation for this review. Unscored is neither M nor L; an uncertain operator may defer and record missing evidence.
2. Once all five current human scores exist, automatically submit `SOURCE_ASSESSMENT_COMPLETED`, retaining each value, operator, time, evidence and source revision. No additional Accept is needed; the first L must not prematurely end incomplete scoring.
3. The System1 adapter expresses completed-scoring intent: any L → `EXCLUDE`; no L but any M → `PENDING`; all H → `INCLUDE` intent. An M reason must identify the criterion and what remains to verify. Selected criteria may generate structured reasons, with optional human notes. Ordinary note typing does not trigger this event.
4. System1 still derives authoritative `selection_status`. Even after all H, it requires publisher, acquisition channel, verified provenance, required official URLs, equipment/OEM applicability evidence, `download_status=SUCCESS` and `snapshot_status=STORED`. If the original is not ready, retain scores and automatically enter replacement/correction within the same source without displaying formal inclusion.
5. Unrelated later field updates must not silently overwrite explicit exclusion. Rescoring reopens review as a new event; downstream receives a new revision without erasing the previous exclusion.
6. Each selection saves a review draft; the final selection forms the complete decision automatically. Show submitted/processing until server-side write confirmation. Idempotency, source fingerprints, Excel locks and backups remain enforced. If writing is temporarily unavailable, retain the decision for execution instead of requiring rescoring.
7. The legacy entry still requires `decision` and `operator_selection_decision`. Production integration needs a narrow scoring command mapped internally to the controlled entry. The frontend must not simply default every APPLY/ACCEPT field or remove the global named-human gate. This design round changed only documentation and the interaction demo, not production fields or execution logic.

### Deferral, exclusion and correction

- “Set aside and continue” changes order only, preserving score/file drafts. “Keep pending” records the missing evidence and remains unresolved. Explicit review dates/conditions may be added later; this design round enables no scheduling.
- “Remove from collection scope” requires a reason and records a human `EXCLUDE`, not deletion. Preserve original files, old URLs, source ID, scores and logs. Downstream marks the source no longer included without erasing parsed results. Existing `RETURN/REJECT` means return for handling and must not impersonate exclusion.
- URL correction distinguishes `official_url` (identity/landing page) from `retrieval_url` (actual resource). Do not make users guess and refill an entire row. Validate format, redirects, content and target identity; a reachable website is not proof of the correct file. Cross-publisher/document changes require identity review.
- Missing originals, provenance or permission may coexist with score drafts. Insufficient evidence retains unresolved reasons; the program must not guess scores to reduce task counts.

### File upload and validation contract

1. Tasks supply `source_id`, target version, language, format and original fingerprint. Operators need not re-enter IDs or name files. A selected file is staged before it can replace a valid snapshot.
2. Files transfer to the local workbench service with progress, failure reasons and retry. UI selection is not durable backend storage. Upload, machine checks, human decision and formal acceptance are separate stages.
3. Check extension against actual content, empty files, configured size limits, complete readability, encryption and corruption. Calculate hashes, detect duplicates and retain provenance. Check PDF opening/page counts, real HTML content rather than error/login pages, and Excel containers/worksheet structures. Conflicting or insufficient evidence remains pending review.
4. A duplicate hash does not create another snapshot. Show precise source-version differences. Filenames, HTTP success or successful hash calculation do not prove file identity or content correctness.
5. Show validation outcomes and next actions first, expanding failure details only. Extract title/version/language when possible and compare them with targets. Unreadable values are unknown, not assumed passes.
6. Human checks cover what the program cannot adequately prove: matching target identity and expected content/completeness. Show task-relevant checkboxes rather than a repeated mechanical checklist. Opening a file does not automatically confirm correctness.
7. Submission includes staged file ID/hash, expected source fingerprint and operator. A replacement file or source revision clears that candidate’s previous checkboxes and requires renewed checking. Leaving the page preserves drafts with clear upload status.
8. “Submit full validation” carries a named human’s conditional acceptance: the person checked candidate identity; complete machine validation then automatically accepts it without another Accept. New conflicts return specific questions for human judgment. Failure preserves the old valid file, candidate and evidence. Accepting an original and including a source are separate business decisions, not one ambiguous Accept.

Example links in this design round came from System1’s CS005 register fields and were checked online at that time: [official resource page](https://programme-centre.asc-aqua.org/resource-hub/?filter=farm), [target PDF v1.0](https://programme-centre.asc-aqua.org/app/uploads/2025/04/ASC-CAR-001-ASC-Farm-and-Feed-CAR-V1.0-May-2025.pdf). The demo’s replacement-original task is synthetic and does not assert a current CS005 failure. Its state was not changed.

Desktop layout: compact system navigation at left, followed by the queue, source evidence, extracted results and decision panel. Source/results receive most width. Narrow windows collapse or move the queue above, with switchable comparison panels. Long text retains full-document reading mode.

Tasks display file ID, clause ID, reason, severity and status. Default order prioritizes blockers and high risk, then waiting time. Multiple issues for one clause are grouped but retain field-level targets and unresolved counts. Confirming one field does not automatically close other issues.

Evidence presentation follows input type:

- PDF: rendered original page, exact page and highlighted region, with adjacent pages, cross-page body and footnote context. Text-layer and OCR evidence are expandable.
- HTML: an isolated read-only local-snapshot preview, locating DOM elements with neighboring sections, lists, tables and footnotes. Retain the unmodified HTML file. A cleaned preview is not a new authoritative original.
- Excel: read-only worksheet view locating sheets and cell ranges with merged cells and neighboring headers. Distinguish formula expressions, cached values and missing caches. Do not execute macros or external links.

Common issues state what is uncertain and where to compare. Display confidence only with a defined, validated meaning. Uncalibrated values are labeled “Uncalibrated”; model scores are not accuracy.

### System2: review centered on original-page evidence | 2026-09-07

The main flow follows the user’s requested PDF page image + red box + parsed text. The left shows a direct rendering of this input PDF; the right shows text from that Canonical revision. OCR or another text output from the same parser must not be labeled authoritative original and used to make two machine outputs validate each other.

By default, show the current issue, original-page evidence and two main actions: “Accept” and “Correct text”. Editing changes the main button to “Save correction and next”. Typing alone does not submit; leaving retains a draft. Text correction does not require a duplicate reason. Original value, correction, operator and time are retained automatically; specialized structural judgments may require reasons.

#### Review types and minimum actions

| Type | Evidence required | Human action and completion scope |
| --- | --- | --- |
| Recognition/transcription error | Original-page box, nearby context and current parsed text, emphasizing numbers, units, negation and clause IDs. | Accept correct text or enter and save a correction. Confirms the specified text target only. |
| Missing paragraph, row or clause | Page-by-page original images and existing output, allowing omission discovery without an existing task. | Select the missing region and add source content as a block/unclassified item. Do not invent content absent from the page. Adding it does not confirm whole-page completeness. |
| Table, list hierarchy or reading-order error | Header/cell relationships, parent-child structure, neighboring paragraphs/columns and cross-page context. | Select row/column/parent, reorder, split or merge. Prefer targeted rebuilding for complex tables instead of whole-page transcription. Correct words do not imply correct structure. |
| Footnote, attachment or cross-page association error | Both linked body and footnote/continuation boxes. | Choose the correct target or unlink the wrong one. Preserve footnote text and identity rather than pasting it into body text and losing the relationship. |
| Header/footer/body classification error | Page position, repetition, context and current type. | Change structural type or downstream exclusion purpose while retaining source evidence. Generic Reject must not delete source text or mean regulatory inapplicability. |
| Illegible page or conflicting evidence | High-resolution original, available evidence differences and affected scope. | Mark inability to confirm and request targeted OCR/reparsing or a clearer original. Keep it unresolved without guessing. |
| Wrong screenshot, box or page location | Complete registered local PDF and parsed text. | “Screenshot does not match? Open full PDF” expands the reader for paging, zoom and search. Confirm/correct after comparison without first requiring coordinate selection. |
| Widespread content anomalies | Affected pages, uncovered regions, structural statistics and missing output. | Request targeted reparsing with failure evidence retained. Reparsing creates a revision; affected previous human judgments require renewed review. |

An expandable “Other issue” entry handles rare actions instead of displaying many permanent buttons. Common text review stays within two steps. Uncertainty, missing content and structural changes must not share an ambiguous Reject action.

#### Item checking and page completeness remain separate

- The item queue includes machine-detected low confidence, conflicts, structural anomalies, missing provenance and new issues manually selected by reviewers. No machine-generated item does not mean no omission.
- Independent page checks list empty-output pages, suspected missing paragraphs/tables and pages requiring coverage checks. Reviewers can add issues without an existing item and open ordinary pages proactively. Completeness must cover the project-required scope, not only machine-highlighted regions.
- Document completeness combines page range, content-region coverage, table/list/footnote ownership and unresolved issues. Zero pending items and zero unchecked pages are distinct facts; neither pair alone proves source fidelity.
- Accepting current text does not close page-level structural/completeness issues. Merging body text does not confirm footnote relationships. Unchecked scope displays “Not checked”, not “Passed”. Unresolved document-level structural or source-fidelity issues continue blocking delivery.

#### Page-image, location and failure-state contract

1. Page images bind `source_id`, `snapshot_id`, source hash, `document_id`, Canonical revision and target ID. The newest online PDF must not stand in for the version used by the current parse.
2. Use sequential PDF page indexes as stable locations and display one-based page numbers, with printed labels separate. Small-window `page_index=19,20,21` cannot index a three-item `pages` array; look up by page index.
3. Boxes record page, bbox, coordinate origin, page dimensions, CropBox/rotation and rendering transform. Zoom and crop share that transform. Display boxes may add a small margin to avoid obscuring text while retaining original coordinates. Cross-page targets support multiple segments, not only the first.
4. Focus on the target and required context by default, with full-page, zoom, previous/next and return-to-target controls. Red boxes mark scope for checking, not certain errors. Tables include neighboring headers; footnote images can expand alongside them.
5. Disable Accept when images fail to load, file identity mismatches, targets are absent or locations are invalid. Explain the reason and recovery action. Loading an original image does not itself prove human review.
6. Location changes, original replacement or Canonical revisions invalidate affected decisions for renewed review. Human approval of an older revision must not apply to new content.

#### Saving decisions and text

Save events distinguish `accept_text`, `modify_text`, `add_missing_content`, `change_structure`, `link_content`, `correct_location`, `mark_unreadable`, `request_reparse` and `complete_page_review`. These are proposed interface contracts, not claims that current APIs support every action. Preserve native/OCR evidence, machine-selected/review/final values and change mappings without overwriting originals or machine evidence.

`mark_unreadable` and `request_reparse` acknowledge human feedback while fidelity issues remain unresolved/blocked. Recording an action must not remove the quality blocker. Human confirmation and machine confidence remain independent; a post-human-selection `1.0` must not be shown as calibrated accuracy. Cross-field/structural changes revalidate affected scope and recalculate related tasks and downstream derivatives.

#### Original-page and code evidence from this design round

- Original pages came from System1’s local CS005 PDF, pages 20 and 21. SHA-256 matched the 2026-08-31 historical Canonical: `77e1d87383382fda4f27dc9be79937cc3017ce350b8b1d436a74500561083838`. Only two pages were rendered; parsing was not rerun.
- Text came from [historical Canonical](../../system2/outputs/runs/smarter-compliance-requirement-sample-20260831/cs005-certification-requirements-p020-p022-runtime-restored/canonical.json). Page 20 Scope demonstrates exact text checking. Page 21 item 2 is stored as two paragraphs; the table object has only 2 rows × 3 columns, with body text stored separately as paragraphs. Review tasks were created for the demo and do not represent a current production queue or new-version quality conclusion.
- Original images directly confirmed page numbers 20/21. Historical `printed_page_label` values contained errors and were not copied. Paragraph boxes use historical segment coordinates; the full-table body region was visually located in this round. Their provenance remains separate.
- The [existing review frontend](../../system2/ui/review.js) already supported original-image boxes and editing, but small windows looked up pages by array position, leaving a gap for nonconsecutive indexes.
- At this historical inspection, the [review service](../../system2/src/pdf_extraction/review/service.py) targeted only `block/span/cell`, without missing-content, structure or whole-page contracts. `reject/unreadable` cleared target review flags and an empty queue then produced document accepted status, conflicting with this design’s unresolved-quality gate. Production integration required targeted repairs and tests; renaming buttons alone could not safely reuse those semantics. Later implementation status belongs to System2 state.

## 4. Human-action semantics

| Action | Meaning | Does it complete the review item? |
| --- | --- | --- |
| Accept extraction | The specified target in this revision matches the source. | Completes that target after validation and confirmed writing. |
| Modify and confirm | Submit a correction and reason while retaining the original machine result. | Completes the corrected target; related results remain subject to validation. |
| Add note | Record questions or context, saving a draft automatically while editing. | No. |
| Defer | Retain a reason and postpone the item while it remains unresolved. | No. |
| Mark non-Requirement | State that an item is not a requirement and explain why. | Retains an exclusion record; neither deletes source text nor declares regulatory inapplicability. |
| Add missing content / split / merge | Repair completeness or boundaries with bound source evidence. | Recheck affected targets and retain mappings from original IDs. |
| Reopen | Correct a prior decision through a new event. | Creates pending work without deleting history. |

System1 candidate acceptance, source inclusion/exclusion, original confirmation and QA correct/incorrect decisions each retain explicit semantics instead of a shared ambiguous Accept. System3 confirmation covers semantic fields and evidence only; it does not accept a Site Model or compliance result.

Automatic note saving does not apply decisions. Task-specific actions express human intent: System1’s final required score completes scoring; file submission expresses acceptance conditional on validation; proposed URL correction uses “Check link and retrieve again”; System2 extraction review uses “Confirm and next”. Avoid duplicate Accept steps or per-item popups. Required reasons stay in the current panel. Keyboard shortcuts must not intercept ordinary letters while typing and cause accidental confirmation.

## 5. Automatic execution after an action

```text
Complete the task-specific human action, such as the final score
  → Validate identity, target, required fields and current version
  → Persist the decision and unique request ID; show Submitted
  → Obtain the owning system’s write lock in the background
  → Recheck source snapshot and result revision
  → Back up/create a revision, apply the decision and validate affected scope
  → Update tasks and metrics; show Applied or the specific blocker
```

No additional manual program run is needed, and each click need not trigger full parsing. Lightweight validation runs immediately; expensive parsing enters a persistent queue. Automatic rule execution does not require an LLM.

Two state layers remain separate: review items use `pending / resolved / deferred / reopened`; execution requests use `queued / running / applied / blocked / failed / stale`. The interface distinguishes received, executing and formally applied. Machine accepted, human confirmed and whole-file checked are shown separately.

Reliability contract:

- Requests contain `request_id`, `actor_id`, `task_id`, `target_id`, `system`, `source_id`, `snapshot_id`, `expected_revision`, `action` and `payload`. Server-side sessions bind the operator; arbitrary client-supplied names are not trusted.
- Unique request IDs deduplicate repeated clicks/retries. Each business resource has only one writer at a time.
- Stale pages cannot overwrite newer results. Source/result changes produce `stale`, preserving the decision draft and requiring renewed comparison.
- Persistent decisions, system receipts and rebuildable task projections remain separate. SQLite and JSON/workbooks have no shared transaction. Idempotent system receipts, revisions, atomic temporary-file replacement and restart reconciliation handle crashes between writes.
- On restart, a write without a receipt is checked against request ID/target revision, never blindly reapplied. Errors remain visible and retryable without silent loss.
- Automatic derivation refreshes affected items, metrics and exports only. Unknown dependency scope explicitly escalates to file-level revalidation.
- New upstream file versions mark related downstream tasks/results for updating. Old-version history remains; previous human confirmations are not replayed automatically.
- Ordinary clicks do not trigger Full Source Check, whole large-PDF jobs, external models or publication. Those require dedicated entries and project-defined authorization.

Closing the browser does not cancel submitted tasks while the local service runs. Sleep/shutdown pauses execution; reopening the entry resumes it. The first version does not install login startup or an operating-system background service by default. “Exit workbench” stops the service safely.

## 6. Enter the operator once

The first design uses local operator profiles: enter a name once to create a stable `actor_id`, shown continuously with a switch option. The browser retains only a session identifier; the server stores profiles and decisions. Refresh/reopening can restore the previous operator with a clear reminder of the current identity.

This is identity registration, not password authentication, for a trusted local computer. Switch or lock the operator at handoff on shared machines. Note drafts belong to their operator. Editing a profile name does not rewrite historical name snapshots.

If simultaneous collaboration across computers becomes a requirement, use one shared service with authenticated accounts and roles. Do not let devices modify separate data copies and merge them through file synchronization.

## 7. Backend modules and data ownership

The initial design proposed `workbench/` alongside the three systems as a separate platform component with its own environment, not a fourth business system. Code and environment creation were deferred until implementation; that original round added only this design document. The component is now implemented to the extent recorded in Workbench state.

| Module | Responsibility |
| --- | --- |
| `ui` | System navigation, task lists, evidence comparison, forms and Dashboard, without business judgments. |
| `identity` | Operator profiles, sessions and current identity. |
| `task_center` | Shared task contract, filters and state projections, retaining original system task IDs. |
| `decision_service` | Request validation, persistence, idempotency and version control, without replacing system judgment. |
| `worker` | Persistent execution queue, retries, recovery, resource locks and background status. |
| `adapters/system1..3` | Invoke owning systems through stable contracts without copying rules into the platform. |
| `evidence_viewer` | Safely read registered originals, check versions/hashes and provide a full PDF reader or safe text preview. Opening an original does not apply a decision. |
| `reporting` | Derive metrics and exports from business snapshots and task projections. |
| `audit` | Track decisions, note versions, application receipts and revisions. |
| `launcher` | Check runtime state, start one instance, wait for health, open the browser and stop the service. |

Do not mix the three systems’ Python environments inside the platform process. Initial adapters may call each system’s own interpreter and narrow command entry, moving to local APIs later if useful. Dashboard must not bypass adapters to write the workbook.

| Data | Sole authoritative owner | Workbench storage |
| --- | --- | --- |
| System1 source selections and snapshot information | Existing production workbook, Data and system history. | Rebuildable views, pending requests and system receipts. |
| System2 extraction facts and revisions | Canonical JSON and source/audit evidence. | Rebuildable index, review requests and notes, without a duplicate fact store. |
| System3 semantic fields | Not yet frozen; future System3 contract. | Design status only in the first version. |
| Operators, interface notes and submitted requests | Local workbench SQLite. | The authoritative record for these data types. |
| Charts, queue statistics and Excel exports | Rebuilt from each authoritative store. | Caches labeled with refresh time and source revision. |

The design uses SQLite for local task/audit storage with short transactions and a single-writer queue. Large concurrent write workloads or direct database-file sharing over a network would require reassessing storage architecture. [SQLite use cases](https://www.sqlite.org/whentouse.html)

The transitional System1 adapter must preserve Excel-open checks, process locks, backups, source fingerprints, named human decisions and complete history. While Excel is open, show that the decision is submitted and awaiting closure before writing; the worker resumes afterward. Reduce pending counts only after confirmed authoritative writing. Full migration out of Excel needs separate design and acceptance.

## 8. Local data and preview isolation

Listen only on `127.0.0.1`. Production writes require sessions, Origin/CSRF checks and restricted Host values. Original-file endpoints map registered artifact IDs to allowed directories and do not accept arbitrary browser-supplied paths. Do not send originals to external pages or services.

Original HTML is untrusted and must not execute as an active page on the workbench’s origin. Use sandboxed previews with scripts/forms/network disabled and verifiable location mappings, preventing source scripts from accessing review sessions. Do not combine capabilities that defeat isolation. [MDN iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe#sandbox)

## 9. Historical code evidence and gaps

This design-round inspection was read-only and did not run the production service:

- The [System2 review page](../../system2/ui/review.html) already had source comparison and Accept/Modify/Reject/Unreadable controls.
- The [frontend](../../system2/ui/review.js) supported original-page boxes and submission, but fixed the operator as `review-ui`.
- The [API](../../system2/src/pdf_extraction/api/app.py) exposed review queue, reviews, source, pages and job endpoints. Their existence alone did not establish complete backend recovery.
- [ReviewDecision](../../system2/src/pdf_extraction/review/service.py) targeted only `block / span / cell`. Requirement/field, completeness and split/merge domain contracts still needed design; actor, action and reason were reusable foundations.
- [JobStore](../../system2/src/pdf_extraction/api/store.py) already used SQLite, without establishing this design’s review-request idempotency, cross-file receipts or crash recovery.
- [System1 human operations](../../system1/Code/src/human_operations.py) and [lock management](../../system1/Code/src/system1/workbook_guard.py) provide adapter foundations without bypassing business constraints.
- System3 remained design work; a page placeholder did not represent an implemented service.

## 10. Implementation stages and checkpoints

Ownership update: System1 integration is complete, with evidence in platform state. This task builds the workbench; other tasks own System2 parsing and business-review services. Parsing implementation in stages B and D below is outside the workbench task.

### A. Experience and contract confirmation, historical

Early stage: an interaction demo plus this design. System2 PDF comparisons used two historical pages with verified source fingerprints. Other examples were clearly labeled synthetic, demonstrating system switching, evidence comparison, names, notes and decision feedback without production writes.

Success: the user can select an operator → open a task → compare source → note/edit → confirm → inspect the result, understanding submitted versus applied. Choose CONTINUE or ADJUST from feedback; demo appearance does not establish backend availability.

### B. Minimal production System2 review cycle

First connect existing page evidence and review interfaces for a small PDF window in an isolated copy. Implement real operators, persistent tasks, revision checks and decision application. Use a known extraction error to verify that correction changes the intended target while retaining original evidence. Zero pending tasks does not replace completeness acceptance.

Required checks: repeated submission applies once; stale decisions are rejected; execution crashes recover; notes do not complete tasks; refresh preserves decisions; files remain recoverable; tasks, Canonical revisions and audit records agree.

### C. System1 integration and cross-system navigation, implemented

Source decisions were connected using isolated copies of the production workbook; results belong to platform state. Acceptance includes Excel closed/open, missing operators, old fingerprints, duplicate requests and worker restart. Reading overview does not download or check sources.

Success: one action produces the correct write without manually running a program, with frontend state matching the workbook and Leader records.

### D. HTML, Excel and Requirement completeness review

Engineering plan at that stage: turn `Parser v1.py.txt` into maintained code, compare sample behavior, then remove the original loose file under existing authorization while preserving provenance. Validate real HTML templates first and define Excel structural contracts. Add source locations, Requirement/field decisions, missing-content and split/merge interactions before expanding formats.

### E. System3 and storage migration

Connect real tasks only after semantic-interface examples receive consumer feedback. Moving System1 out of the workbook, multi-device collaboration, formal login and persistent startup each need separate requirements and validation; they must not block the first local version.

## 11. Historical interaction-demo validation

The local browser demo was checked for operator selection, expanded source context, saved notes, disabled submission buttons while processing, updated metrics and automatic advance after application, corrections remaining pending without a required reason, confirmation after adding that reason, and corresponding overview progress. Layouts were visually checked at 1024px and 360px, with desktop side-by-side comparison and narrow vertical stacking. No JavaScript error was observed.

The demo used in-memory state and reset on refresh. Its two historical System2 PDF pages are documented above; other examples were synthetic, without a production persistence service. It validated interaction direction, not production writing, backend recovery or account security. Not every failure simulation or dark theme was accepted in this round.

The simplified revision added actual file selection/drop controls and browser-local checks for empty files, size, extension and PDF headers. In a separate local preview, `wrong.pdf` containing only HTML produced an explicit type mismatch, leaving checkboxes and submission disabled. No file reached a service; full parsing and automatic identity verification were unimplemented. Passing basic checks could not complete formal acceptance. Browser tools did not capture file-selection events in the conversation preview, so the invalid-file path was checked in the separate local preview. This did not establish acceptance of every upload interaction.

That round changed no production workbook, Canonical business result, original input or existing parser. It did not install a launcher, enable automation or delete `Parser v1.py.txt`. The user separately requested a task for System2 engineering; this task retained the shared workbench.

### System1 action-type validation | 2026-09-07

Added usable five-criterion scoring, URL correction and source sampling, combined with file selection into four synthetic source tasks. New candidates, provenance supplementation, duplicate handling and version selection had defined contracts but not complete forms/backend connections.

Browser checks:

- No operator meant scoring was unavailable. Four scores did not close the source. A fifth M automatically recorded pending; changing it to H automatically included the source in the demo list, without an extra Accept.
- Reopening retained score history; complete scoring containing L automatically displayed exclusion.
- A source missing an original and needing scoring returned to file submission after all H. All four sources remained unresolved, without a fifth source or premature inclusion.
- URL input rejected non-HTTP(S). Valid syntax showed syntax passed only, explicitly leaving reachability/file identity unverified and the source incomplete.
- Explicit deferral or exclusion without a reason was blocked; adding a reason and deferring retained it.
- A URL error found during sampling opened correction, then uploading, within the same source task and unchanged count. Submission was unavailable without a selected file.
- Layouts were checked at 1024px and 736px; 360px had no horizontal overflow. No JavaScript error was reported. The separate preview used the same demo file and did not upload, request URLs or write business data.

Production integration still needed persistence of individual scores and complete decisions, idempotency, write locks, stale revisions, conditional file acceptance, reconstruction of multi-issue tasks and real source-identity checks. Demo results could not replace these checks.

Inline-preview compatibility revision: the user reported `TimeoutError: MCP sandbox RPC timed out`. The original file loaded in a local isolated iframe; the host RPC timeout was not reproduced. Removed optional host Tweak registration and document-title writes, adding duplicate-initialization protection and a startup message while retaining business interactions. The revised isolated iframe passed initial load, operator entry, automatic processing of five H scores, the next source’s file controls and disabled submission on empty selection, with no JavaScript error. This reduced host dependencies but did not prove RPC-service recovery.

### System2 original-page comparison validation | 2026-09-07

Browser checks covered actual page images, boxes/text positions, previous/next and return-to-target controls, one-save text correction, paragraph joining with footnote markers, page checks, manual coordinates and actual drag selection.

- No operator meant decisions did not apply. Accept was unavailable on an adjacent page. Blank corrections could not save.
- Saving text corrections and paragraph merges reduced only corresponding item counts; unchecked-page counts stayed unchanged. No duplicate correction reason was required.
- Adding the first original table-heading line retained the parent task and pending page check. Coordinates now synchronize through `input`, fixing delayed saving when relying only on blur-triggered `change`.
- Actual drag reselection produced coordinates and saved a location revision while content remained pending review. Marking illegible did not reduce pending counts and disabled Accept.
- The same file loaded actual page images in both standalone preview and isolated iframe without JavaScript errors. Narrow windows stacked source and text; 360px had no page-level horizontal overflow. Zoomed source view supported horizontal panning. Temporary window sizing was restored.
- Evidence was read-only from historical Canonical and direct rendering of two PDF pages. No Canonical, production workbook, historical output or original PDF was written, and no reparse ran.
