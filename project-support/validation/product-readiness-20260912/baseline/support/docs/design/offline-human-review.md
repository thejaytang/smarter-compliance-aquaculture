# 1. Offline human review and main-version adoption

Status: approved implementation scope, 2026-09-12. This extends the [human-led workbench goal](human-led-workbench-goal.md). The user's approved offline plan governs collaboration conflicts and personal/main boundaries. The exact third-pane schema and semantic processor remain deferred. Actual Windows round-trip evidence is mandatory before this round can be called complete.

## 1.1 Human workflow

| Step | Human action | Durable result |
| --- | --- | --- |
| Distribute | Coordinator chooses an existing source, original and material and exports a work ZIP | Immutable common baseline and the selected original |
| Review locally | Named colleague imports into a separate reviewer workspace, reads and corrects | Personal work; main remains unchanged |
| Save | Save partial text, source proposals, scope checks and open issues | Recoverable personal version; not complete review |
| Submit | Select saved source, material and inspection results with a scope/issue summary | Independent immutable submission, including saved history |
| Compare | Coordinator imports and opens a submission | Three-way merge preview; disjoint human changes are prefilled and labelled pending |
| Adopt | Keep current, choose submitted or edit each conflict, then explicitly adopt | Separate source/material receipts and a new main content version |
| Confirm | Check affected and uncovered ranges, unresolved issues and complete original coverage | Independent confirmation bound to exact main content and original |

The coordinator's own work follows the same personal-draft and explicit-adoption path. A colleague's confirmation belongs to that personal version. It does not become a confirmation of the combined main version. Partial adoption is permitted and cannot mean whole-material completion.

## 1.2 Display and decisions

Keep Original document, Extracted original text and Structured requirements within one Materials workbench. Navigation and Overview expose Source Management System and Requirement Extraction System only; there is no standalone System3 UI, queue or incoming-feed entry. Internal design files and historical interfaces are retained. Default material editing uses the named person's workspace. Main view and merge preview are explicitly labelled. A fresh personal workspace is seeded from the distributed baseline or current main; an existing personal draft is not silently rebased.

Changes are shown beside the affected paragraph, table cell or source field. Compare common baseline/current/submitted values; the baseline can be expanded. A change to the same content, deletion against editing, ambiguous split/merge/order, table layout or original association requires a human decision. Different positions may combine in preview, but dependency/coverage review is still required. Time order never selects a winner.

Machine extraction is button-driven. First extraction into empty content offers a candidate preview. Re-extraction leaves saved human content unchanged. Machine differences use the same inline comparison components and explicit keep/choose/edit actions in the personal workspace. Repeated identical candidates may reference an already recorded decision when source and current content still match; that reuse is audited, not a new human confirmation.

## 1.3 Data and exchange

System1 governance SQLite and System2 Workflow SQLite remain the owning stores. Additive collaboration records in Workbench hold baselines, received submissions, saved choices and adoption receipts. Separate personal System2 stores hold local work, pinned originals and version history. Never merge SQLite files from colleagues.

ZIP format `aquaculture-offline-collaboration`, version 1: a small `manifest.json` carries identity and a SHA-256 file inventory; `files/review.json` carries versioned review data. Work ZIPs include only the selected original and its source/material evidence. Return ZIPs do not introduce sources or replace originals. Bound-original image references travel with the selected original. External image retrieval is not implicit.

Imports check archive/path/size/inventory/JSON integrity, UUID identity, roster identity, source/material/original binding, complete material history and common baseline. A repeated identical package returns its receipt; conflicting content under one UUID is rejected. Unknown baselines stay pending without a guessed merge. Original paths use portable single segments, including Windows filename constraints. Package transport is manual; no sending, pushing or synchronization is added.

Personal save history, edits, original references, candidate evidence and prior decisions remain separate from main acceptance. Imported historical candidates are evidence and never an executable queue. Source proposals use the owning System1 validation rules. A new review of a closed old task appends a new operation, preserving the old decision.

## 1.4 Adoption and failure rules

Only the trusted local coordinator, Weijie Tang, can distribute main work, adopt into main and confirm main content. Named identity is trusted local attribution, not authenticated online multi-user security. Roster remains Ana Jokic, Daniel Restad and Weijie Tang.

Adoption stores its exact request before dispatch. Apply source first and persist that receipt, then apply material against the checked revision and original. Each owning store supplies idempotent replay. A failure after one step leaves a resumable partial record; it cannot report total success. Changes to main after preview require renewed comparison. Changing a choice after an adoption has begun is rejected.

Checks retain the original reviewer, content reference and scope only when original and affected-content analysis support inheritance. Altered or ambiguously linked ranges need renewed review. Main confirmation also explicitly checks omissions and dependencies. Pending candidates and unresolved issues prevent false completion. Original/global historical confirmations are retained rather than copied onto new content.

## 1.5 Runtime and acceptance

Reviewer mode starts only explicitly requested material extraction work. It does not run source governance, legacy parsing, QA, model or workbook schedules. Normal migration needs a complete backup first. Recovery includes collaboration journals, personal stores including committed WAL content, originals, packages and historical evidence.

Local validation uses one coordinator and two completely separate reviewer roots. Required scenarios: serial A-reviewed/B-edited history; same paragraph and same cell conflicts; disjoint contribution preservation; machine/human disagreement and repeated resolution; unchanged machine portions; partial work and multi-reviewer checks; source field/rating/issue conflict; changed originals, duplicate/unknown packages, failures/restarts; and a main change after preview.

macOS tests and browsers are local evidence only. The office Windows user must run startup, import, original reading, Extract, correction, save, restart and submission export; return that ZIP to macOS for import, conflict resolution and adoption verification. Until that evidence exists, Windows and this round's full completion remain pending.

## 1.6 Material categories and archived spot-checks

Pending materials and Archive are the two material categories. Save, export, compare, adopt and confirm remain actions within the same three-pane workbench. Archive reads an actual human-confirmed main revision, never a personal confirmation. A later draft, candidate or spot-check does not replace the accepted historical version. Pending is filtered on the server before pagination and contains unfinished main/personal work, incoming submissions, source follow-up and open spot-checks.

From an archived material, the coordinator explicitly creates a named, scoped spot-check. It appears in Pending and opens the frozen accepted content in the same three panes. Save check progress is separate from Pass selected checks. Recording a problem keeps follow-up open and blocks a new whole-material confirmation. Resolve checks the current main version and affected range; it does not itself confirm or archive that main version. A newer archive requires an explicit restart against that version, preserving the older check history. No schedule is created.

Version 2 collection work packages can carry specified inspection tasks, their exact accepted archive and source history. Reviewer results return as independent items. Imported checks do not change the main task: a coordinator explicitly accepts or retains each result. Old-archive checks remain evidence of that version; a changed task requires renewed comparison.

## 1.7 Work area and column proportions

Expand workspace fills the browser viewport, hides global navigation, material library and auxiliary toolbars, and retains the material title, save and exit controls. More tools reveals auxiliary actions when needed. Escape or Exit expanded view restores the normal layout without saving, extracting or changing content. Narrow screens retain pane selection instead of squeezing three unusable columns together.

Drag either column separator horizontally, or focus it and use Left/Right (Shift for larger steps). Adjacent panes resize with minimum readable widths; proportions are retained in this browser across material changes, reload and expanded view. Reset column widths restores the defaults. This preference is not a material revision or a collaboration decision.

## 1.8 Queue and inspection interfaces

Authenticated GET `/api/material-queue` takes `bucket=pending|archive`, `query`, `offset` and `limit`; GET `/api/material-inspection` takes `task_id` and optional `current=true`. Material reads with `view=archive` bind to a confirmed historical main revision. Original readers use the corresponding saved original, not a client path.

POST `/api/collaboration/inspection-create` requires `material_id`, exact `archive_revision`, named `assignee`, `reason`, selected `scope` and `request_id`. POST `/api/collaboration/inspection-save` requires task/material identity, `expected_revision`, `request_id`, `action`, `note`, `checked_scope` and explicit confirmation for completion. Actions are `save`, `pass`, `finding`, `resolve` and `restart`; current-main resolution also requires `expected_master_revision`. The server enforces actor, source/version validity, complete selected scope, replay identity and concurrent revision guards. Task history and receipts live in the existing collaboration journal and are included in full backup/recovery.


## 2. Workflow correction, approved implementation

This is the current workflow contract. Acceptance evidence and runtime loading belong in PROJECT_STATE.md. It preserves all existing source-management scenarios; examples do not narrow the source scope. The requirements processor remains deferred.

### 2.1 Source scenario coverage

Source Management System uses Pending review, Source records and Review history in an independent source/task list and detail workspace. A source can be reviewed before an original is available. It cannot become INCLUDE until the owning acquisition, original, provenance and applicability gates pass. A coordinator uses one explicit Confirm and apply action; personal contribution and adoption remain distinct stored records. Colleagues save proposals and return packages.

| Existing task or trigger | UI and service path | Completion boundary |
| --- | --- | --- |
| SOURCE_REVIEW / SELECTION_REVIEW; machine ratings and selection | Five rating slots, selection proposal, evidence note, preview and source adoption | Scores and selection must agree; missing originals or other unresolved conditions remain pending |
| Missing links, issuer/version, unverified provenance, applicability | Expand source fields, retain evidence, apply a named proposal | Metadata correction alone does not verify a replacement original |
| DOWNLOAD_FAILURE, PAYWALL_BLOCKED, MISSING_FILE, REGISTRY_FILE_MISMATCH | Task-specific Retry retrieval or Supply authorised original | Explicit action only, one source/task; preserve former original and downstream version binding |
| NEW_SOURCE_CANDIDATE | Inspect candidate fields; accept, reject or defer | Registration belongs to the coordinator; a returned opinion cannot create a source during import |
| MANUAL_FILE_REPLACEMENT; rolling original changes | Inspect retained evidence and proposed file; accept/reject/defer or supply an authorised file | Replacement is a main-workspace action; old files and downstream text are retained |
| RANDOM_QA_CHECK / RANDOM_QA_FAILURE | Dedicated Correct/Incorrect outcome and evidence note | Incorrect creates specific source follow-up, not material-content acceptance |
| HUMAN_REPORTED_ISSUE | Report a source problem; verify individual evidence-bound reports | Each report has a stable identity and digest; old general flags cannot close new reports |
| Pending, exclusion and repeat review | Selection with reason; Request another source review from source records/history | A new review record preserves all prior decisions; explicit task checks close only their exact task versions |
| Failure, concurrent edits and retry | Version checks, retained local draft, persisted pending request and owner receipt | Retry resumes the same payload; it does not apply unrelated staged tasks |

`issue_checks` binds each selected issue digest; `task_checks` binds each selected source-review task revision. `new_issues` contains bounded, identified personal problem reports. A successful main adoption creates their follow-up records and keeps the outcome partial. Historical tasks and inspection outcomes do not act as material-content confirmation.

### 2.2 Material correction and archive continuation

Pending lists eligible unstarted originals directly as well as existing drafts, incoming results, stale content and open spot-checks. Listing creates neither a material nor an extraction. Explicit opening establishes the original binding. First Extract on untouched empty work displays an editable candidate preview. Saving it atomically retains a machine baseline and the edited personal version, with no review confirmation. Later extraction uses explicit three-way comparison.

Level arrows change heading hierarchy and its subtree; sequence arrows change position. Rebuild table accepts adjacent blocks and tab-separated cells or dimensions. Preview and confirmation replace only those blocks, retain original text/links/actor in transformation evidence and update references. Row/column edits use explicit positions; original history remains available.

Archive holds accepted, fully content-reviewed main versions. Continue editing restores an existing personal draft or seeds from the current main and returns that material to Pending. It neither rewrites the archive nor invents another material identity. Source problems and later original versions remain visible. Process stays disabled.

### 2.3 Collection and receipt interfaces

The original version 1 single-item archives remain readable. Version 2 `collection` archives have a bounded manifest, collection identity, direction and independent item identities. Every embedded archive is fully checked, including baseline/history/original associations, before business import begins. Duplicate identities with changed bytes are refused; receipts make interrupted imports and adoptions resumable. Database/environment/session files remain excluded.

`GET /api/source-workspace` and `/detail` supply source/tasks and individual draft evidence. POST `/api/source-workspace/{preview,save,apply,reopen,task-save,task-apply}` binds reviewer, identity, expected source/task/draft version and request ID. Scoped owner processing never performs an unrelated source sweep.

`GET /api/collaboration/collection-catalogue?kind=work|submission|receipt` supplies selectable saved items. POST `collection-export` freezes selected results; `collection-download` retrieves the same immutable bytes. Normal `import` accepts both archive versions. `collection-preview` and `collection-adopt` compare and choose a specific task/inspection result; normal source/material comparisons continue through `preview`, `resolve` and `adopt`. A changed task cannot receive an old outcome as a current check. Received receipts are evidence only and do not rewrite personal work.

Source/material adoption receipts remain separate. Related source decisions must be processed before material adoption. Stale material previews are rejected and must be reopened. A partially applied collection has per-item receipts and cannot display an overall review-complete state. The My submissions drawer is part of the existing workspace, not another business page.

### 2.4 Acceptance boundary

Use one coordinator and two independent reviewer data roots with synthetic originals. Verify source task isolation, missing originals, first candidate editing, structural correction, per-cell/paragraph conflicts, repeat extraction, partial results, corrupt/repeated packages, unknown/stale baselines, interrupted application, archive continuity, recovery and named histories. Browser checks and actual service loading are distinct evidence. Actual Windows open/read/extract/edit/save/restart/multiple-export and returned Mac adoption remain mandatory before full-round completion. No model, new scheduler, external sync, publication or transmission is enabled by this extension.
