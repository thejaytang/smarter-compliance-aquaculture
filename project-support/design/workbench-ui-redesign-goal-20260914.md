# Workbench UI and interaction redesign goal

Status: implementation activated as an app Goal by the user's explicit request on 2026-09-14. Current evidence belongs to the owning PROJECT_STATE files and the [execution checklist](../ui-redesign-20260914/execution.md).

## 1. Objective and authority

Implement and deliver the approved minimal, efficient source/material workbench, not just an audit, plan, mockup, screenshot or renamed menu. Continue through implementation, relevant regression, actual browser workflow verification, recoverable local activation and handoff. This is a new authorized phase after the completed local-delivery-rc1 closeout. Earlier stop/visual-expansion restrictions do not prohibit this redesign. Existing preservation, human authority, confidentiality and external-action boundaries remain in force.

The actual workstream root in this authoring workspace is `/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side/`. Read its AGENTS.md, README.md, PROJECT_STATE.md, applicable component states, ENVIRONMENT.md and dependencies before executing product code. Read this goal, project-support/design/PRODUCT.md, DESIGN.md and relevant source/collaboration contracts. Check current source and running code before making state claims; recorded ports and acceptance evidence may be stale.

This file owns the new goal and acceptance criteria. Update PRODUCT.md and DESIGN.md to express the accepted final implementation direction when implementation starts; retain historical evidence. Use existing project-support organization for the rolling plan and verification evidence, with concise current-state links. Do not create duplicate root entry documents or parallel goal specifications. Keep maintained project prose and shipped UI in English, original evidence in its source language, and user updates in Chinese. The Chinese module names below are the user's conceptual names, with English UI labels stated once.

## 2. Fixed information architecture

There are exactly two business workspaces and six ordinary modules:

- Source workspace: 新增来源 / Add sources; 来源审查 / Source review; 来源管理 / Source register; 审查历史 / Review history.
- Material workspace: 材料审查 / Material review; 归档 / Archive.

Source register is the complete numbered source table, not review history. Source review history contains actions, not another source list. Material extraction and review share one workspace and are never separate routes or wizards. Do not add a Material register, material action-history module, separate extraction page, mandatory Overview or System3 navigation. Internal system ownership and stable identifiers do not change merely because UI labels change.

## 3. Global shell and space

Use one compact top navigation row: workspace selector, current workspace's module links, collaboration entry and current operator. Selecting a workspace replaces the module links in that same row. Remove the persistent global left rail, oversized brand/header cards, duplicate headings, descriptive slogans and repeated status blocks. Restore the last module/context on return; first use enters the appropriate pending review queue without starting work automatically.

List views use the full content area. Opening a record replaces the list with the working detail. A named back/switch entry and previous/next navigation provide access to a temporary list, preserving query, filters, list position and unsaved work. Do not permanently combine a global sidebar, material library and three content panes.

Detail views have one compact record/task bar for identity, meaningful version/status and the applicable primary/secondary actions. Normal working mode already uses the available viewport. Do not retain a separate expanded mode that hides or moves core actions. Keep Save and the final decision in stable locations. Layout/reset/fullscreen preferences belong to a named secondary menu; collaboration packages/inbox do not own a permanent extra toolbar. Show reviewer name compactly; switching is an explicit action. Settings, runtime, backup and exit are secondary application actions; actionable failures remain visible.

At 100% zoom on 1280x720 and 1440x900 app viewports, aim for combined global/task/pane headers of 120-140 px or less, leaving roughly 80% of height for task content. Measure actual rectangles against the old baseline; this is a target, not pre-existing evidence. Do not meet it by hiding required decisions, clipping controls or shrinking evidence text. Justify any exception with a specific readability or decision need. Preserve restrained existing styling, system typography, readable opaque evidence surfaces, modest controls, accessible contrast and visible focus. Avoid card nesting, excessive borders/shadows, decorative motion and simultaneous coloured status badges.

## 4. Source modules

### 4.1 Add sources

Two modes share a page: manual intake and automatic discovery. Manual intake begins with file or source URL, then editable extracted metadata such as title, publisher and version/date. Show missing/uncertain values and a clear Add to review action; other fields are disclosed on demand. Preserve exact originals. Parsing metadata is not evidence of completeness or an INCLUDE decision.

Discovery uses explicit scope/keywords/start, a compact result table, duplicate/new-version signals and selected addition to review. Reuse and connect existing bounded discovery/intake services; inspect provider availability. Do not fake search results, auto-include candidates or silently create duplicate sources when a new version belongs to an existing source. New provider credentials, paid services or external document transmission require their own authorization. A missing dependency must have an honest capability state and precise blocker; it is not proof that discovery works. Finish independent modules while that dependency is unresolved. A UI-only or mocked discovery path cannot be reported as live discovery acceptance.

The user clarified on 2026-09-14 that automatic search should remain an API integration placeholder for this delivery. When no interface is configured, show that a search API service must be added and keep execution unavailable. Connecting a live discovery provider is deferred by this explicit decision; an honest unavailable capability and visible setup requirement satisfy this delivery, without claiming real search.

### 4.2 Source review

One source row summarizes its pending tasks. Default columns: ID, title, reason for this review and current selection. Opening uses resizable original/document comparison and a review area. Display essential identity, publisher, version/date, a short sourced or clearly attributed introduction, useful links, all required H/M/L criteria, original checks, specific pending issues and INCLUDE/EXCLUDE/PENDING decision with necessary rationale. Expand detailed criteria, prior decisions, machine evidence and extra metadata only when needed.

Highlight exact questionable fields or evidence locations and explain why a human check is required. Initial review covers all required checks; periodic review prioritizes assigned scope without implying that unchecked content passed. Old scores are reference values, not new confirmation. H/M/L controls change the draft only: no automatic submission or silent final selection change. Saving progress and explicitly applying/submitting the review are separate. Preserve coordinator/reviewer authority while consolidating unnecessary screen transitions.

Periodic source tasks use this same queue and detail. Missing/invalid originals continue to block INCLUDE where the existing contract requires them. Inclusion and pending re-review are independent states.

### 4.3 Source register

Show every registered source including PENDING, ordered by source number. Default columns: ID, title, publisher, version/date, selection and original availability. Search and a small set of useful filters belong above the table. Do not place full descriptions, scores, long URLs, history or a row of repeated action buttons in every row. Title opens details; original availability provides the original entry. Reuse review readers/fields in read-only detail and create an explicit review task when needed.

### 4.4 Source review history

One row is a review action. Default columns: time, operator, source, action and result. Filters cover source/operator/time. Expand before/after, rationale and bound version in place. Keep file hashes, raw payloads, unrelated runtime logs and large evidence bodies out of the default table. Source links navigate to the corresponding record/version.

## 5. Material review and archive

### 5.1 Unified review workspace

Review queue columns: material ID, title, task type and concrete pending work. First processing, periodic review and conflict review are task types/filters in one module. Do not create duplicate material rows for individual issues where one material task summary suffices.

Every material opens the same three panes: Original document, Extracted content, Requirements. They always remain side by side, with operator-adjustable widths and independent scrolling. Persist sensible operator/device layout preferences across materials and reopen. Do not hide, auto-collapse or replace a pane with tabs at narrower widths or browser zoom. If three readable panes cannot fit, preserve their side-by-side structure with an explicit accessible overflow strategy instead of shrinking text or hiding a pane. Changes here supersede the old responsive pane-tab defaults.

The original pane has compact position/search/zoom controls; outline, alternative readers and original details are secondary. The middle pane presents continuous editable content rather than a card and full toolbar per block. Place explicit Extract in the middle-pane header and future Process in the Requirements header. Select/click text to edit naturally; show structure/split/merge/table tools in the relevant selection context. Provide discoverable controls and keyboard alternatives, not right-click-only or hover-only essential actions. Retain original-bound images, numbering, hierarchy, tables, associations, omissions and source traceability. Exact Requirement fields/forms must follow an approved schema, never be invented merely to fill the right pane.

Source-linked navigation locates and briefly highlights the corresponding evidence while preserving manual independent scrolling. Issue markers expand concise reason/evidence/action in place. Previous/next issue controls do not create an additional full-width toolbar. Conflicts show current and incoming content inline in the owning pane with explicit keep/adopt/edit decisions; preserve the original pane and all three-pane structure. Label each input's actual source/version when it differs. No new extraction or incoming package silently overwrites human work.

### 5.2 Save and finish

Keep unsaved/saving/saved/error state distinct from review completion. Save and Cmd/Ctrl+S have the same meaning. Local recovery is not a confirmed server save. Preserve draft, selection, scroll and source identity on navigation or failure; protect unsaved work when leaving or changing actor. Do not force unnecessary save-preview-master-navigation loops. Streamline the finish flow with explicit target, version and decisions while retaining authority, expected-revision checks and separately recorded save/adopt/confirm outcomes. Transaction failure or partial success must not masquerade as finalization.

Normal completed work ends with an explicit Archive action. Periodic review without changes ends with Complete review and retains the same archive. Conflicts must first be resolved and explicitly applied; resolving conflicts alone does not confirm complete content. Primary-action position stays stable even where the task-specific label differs.

### 5.3 Archive semantics and deferred Requirements

Archive presents finalized material versions, not an action log or general material register. Default columns: ID, title, source version, finalized revision, date and operator. Show the latest finalized version by default with older versions available from an explicit version entry. Opening reuses the complete three-pane reader in read-only mode; all saved content and traceability remain visible. Editing/extraction/save controls are replaced by concise finalized status and deliberate review/revision actions. Retain export and version access without cluttering the default view.

Finalization is a server-enforced, version-bound state transition, not a relabelled button. Require complete applicable review scope and no unresolved substantive issues/conflicts; retain immutable finalized versions. Define and test the exact archived snapshot, source binding, reviewer authority and completion scope before implementing its entry.

The user explicitly confirmed on 2026-09-14 that new content-only archives are allowed while the right-pane schema/processor are deferred. Their visible status must be Content finalized · Requirements unfinished. Finalization checks the complete source-content scope, issues, conflicts and authority, and records that scope explicitly; it never confirms Requirements. Preserve previously content-confirmed archives with their true content-only historical scope. Show a concise Not connected state in the right pane, not a large promotional placeholder. Missing schema must not launch semantic research or block this content-level archive workflow.

### 5.4 Weekly and conflict re-review

Weekly inspection selects finalized versions and creates review tasks linked to those exact versions in Material review. Original archives remain intact. Passing an unchanged review closes that task only; modifications create a revision draft that requires explicit later finalization and retains prior archives. Incoming changes and source-version changes enter the same review/conflict flow.

Use the owning application's inspection mechanism, durable batch identity and restart-safe deduplication, not a Codex reminder/automation. Implement and verify weekly behavior with an isolated store and controllable clock; do not wait a real week. Reviewer installations must not run coordinator schedules. Do not newly activate a normal-business recurring schedule as a side effect of development or page navigation. Any unconfigured real scheduling choice/activation is reported separately from tested mechanics.

## 6. Execution method and preservation

Start with a recoverable baseline and a capability/route/state map. Identify source records, governed stores, material and archive records, extraction candidates, collaboration receipts, active services and newer unsaved work. Preserve originals, Canonical, Gold, completed human decisions, archive versions and runtime history. Backups must include live database state correctly; copying a database file without accounting for its WAL is not a verified recovery point. Prefer existing components and environments; no unnecessary framework rewrite, global dependency install or duplicate business-state source.

Use rolling-horizon planning: next useful experiment, implement a coherent workflow, validate, then proceed. Prioritize shell/navigation and the complete source-review and material-review/finish paths, then remaining modules and integration. Necessary local UI, API, routing and state-transition changes are authorized; do not stop after CSS or labels. Investigate failures with discriminating checks, adjust the plan and continue independent work. Ask only for decisions that materially alter product truth, unavailable access, external transmission or irreversible effects; routine reversible design/engineering choices do not need repeated approval.

Use relevant Impeccable/UI design guidance without allowing generic simplification advice to remove the three panes or required evidence. Reuse or delegate bounded independent checks where authorized and useful; the primary agent verifies integration. Keep updates concise and milestone-based. Do not start parser-accuracy research, model training, a final semantic schema, ontology, Site Model or a compliance engine.

All engineering decision/save/adopt/archive/package/inspection tests use isolated owning stores and local test copies, never genuine named business confirmations. No git commit/push, external upload/message/publication, paid/API activation or important-file deletion is authorized by this redesign. Local incoming test files/packages may be exercised against isolated local services. Preserve original confidentiality and source ownership.

## 7. Acceptance and completion

Maintain one compact checklist with PASS/FAIL/UNMEASURED/BLOCKED and linked evidence. Verify at least:

1. The exact two-workspace/six-module navigation; no permanent global rail/library stack, duplicated overview or separate extraction/material-history route.
2. Actual 1280x720, 1440x900 and 1920-class browser layouts, plus 200% zoom and keyboard operation: all three material panes remain side by side, resizable and usable; core controls do not disappear or change location with a layout mode. Measure header occupancy and compare task space with baseline without hiding required information.
3. Manual source intake to a pending candidate, including missing metadata/original handling; duplicate and new-version discovery handling through a real available path. Clearly distinguish configured live discovery from isolated adapter tests and unavailable providers.
4. Source original comparison, explicit H/M/L and selection decisions, preserved prior values, periodic task scope, source-register sorting/filtering and action-based review history.
5. Material open, optional explicit extraction, text/structure/table correction, exact original navigation, save/reopen and unsaved-input recovery. Navigation alone produces no extraction/review/adoption.
6. Source and material collaboration paths remain usable without a permanent collaboration bar; incoming/local conflicts resolve inline with explicit application. Check stale revisions, duplicate requests and relevant returned-table conflicts against owning stores.
7. Version-bound finalization and read-only three-pane archive replay; unavailable semantic stages and historical content-only scope remain truthful. Incomplete/problematic/conflicted material cannot be falsely finalized.
8. Isolated weekly selection creates a pending task while retaining the archive; unchanged completion, revision/re-archive and restart/deduplication paths work with exact version bindings.
9. Reading/extraction/save failures retain current work and expose relevant recovery at the failing location. Regression tests cover meaningful state, data and cross-module risks, not mirrored implementation details.
10. Verify preservation and a recovery path; update relevant source/workbench integration checks and documentation links. Old tests or screenshots are usable only where still bound to unchanged behavior.
11. Identify the final runnable code version and actual loaded frontend/backend. Deliver the redesigned local UI through the normal local launcher once affected checks pass and current business/unsaved work is protected. A recoverable local UI/service activation is distinct from adopting a business main revision or deploying a formal environment. If active unsaved work or another concrete constraint prevents a safe local switch, keep the isolated candidate available and report the precise remaining action; do not falsely report the normal entry updated.

Finish when the agreed UI/workflow scope is implemented, relevant acceptance passes, the actual local loading state is verified and recovery/handoff are usable. Report incomplete dependencies and product decisions as unresolved, not passes; do not quietly redefine scope around successful modules. Broad extraction fidelity, real colleague usability, actual Windows round trips and formal deployment remain separate claims. Stop open-ended polishing after the accepted goal is satisfied; rerun broader tests only for new changes, failures or unresolved risks.

Final handoff: what changed, how to open the actual result, version/loading state, key workflow evidence, remaining substantive gaps and recovery location. A prototype, generated artifact, green tests or screenshot alone is not completion. Do not create a scheduled Codex task to continue later unless separately requested. If continuation uses an app Goal, create or update it only under an explicit request to start that Goal; this prompt-preparation document itself does not assert that one has started.
