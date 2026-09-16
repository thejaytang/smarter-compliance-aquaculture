# Local Workbench User Guide

## Continuous Markdown content

The middle pane opens as one directly editable document. Select across paragraphs to edit or delete text. Hover a passage for To requirement and upper/lower + insertion controls (Context, H1, H2, Table). Table cells are editable, with edge controls to add or remove rows and columns; merging is not offered. Save explicitly before Requirement intake. Changes retains red/green differences after Save/reopen. [Workflow and tools](docs/markdown-content.md). Re-extract can refresh an untouched machine preview, while preserving its prior result. Existing human edits remain protected.

## Manual requirement splitting

In personal material work, save the content and choose **To requirements** beside a text passage. Work through **Outer relationships → Unit fields → Result** in the right pane. Every applied step is saved separately. [Full instructions and storage boundaries](docs/manual-requirement-splitting.md). Automatic requirement extraction remains disconnected; the new personal splitting records are not yet included in collaboration ZIPs.

## Settings and collaboration (current)

Open **Settings**, or your name at the bottom left. Keep using **Current reviewer** to switch identity. All saved work remains attributed to its author.

- **Collaboration → Export full workspace** prepares a complete saved-work snapshot and displays its size. Click **Download full workspace** to save the ZIP, then send it to your colleague. Save any open edits first. Exporting does not remove work from future exports.
- **Import work** accepts a full workspace ZIP, checks originals and saved versions, and presents a comparison. Resolve each overlap with **Keep this version** or **Use imported version**, then choose **Confirm synchronization**. Unchanged or older records do not overwrite newer work. Records absent from the package remain on this computer. If an interrupted import is listed in history, resume it; if saved work changed, choose **Refresh comparison** before confirming again.
- **View synchronization history** shows who imported whose work, the precise local-time timestamp and affected records. These events are shared through later exports; there is no live network synchronization. Source task evidence is retained without dispatching imported tasks or silently closing local source gates.
- **Automation** holds confidence thresholds and Archive spot-check settings: interval in days, sample size, reviewer and timezone. Saving a schedule does not run it immediately. Schedules stay local and are never enabled by an imported package. Offline reviewer installations do not dispatch shared checks.
- **Runtime status** reports service activity and failures; it is separate from content quality or review completion.

Full snapshots include originals once plus saved work/history, and exclude the application, caches and old ZIPs. The measured current snapshot was 20.7 MiB; size grows with material/history. Both collaborators need a version supporting full snapshots. Earlier work/result package code and history remain retained for compatibility, but the new Collaboration dialog accepts full snapshots. [Verification and limits](../project-support/settings-sync-20260914/RESULTS.md).

## Saved data for GitHub

The 2026-09-16 retention decision protects **System1 human records** and **explicitly exported, selected Workbench import packages**. It replaces the earlier all-runtime publication scope for subsequent synchronization. Historical backups remain historical; they are not the default restore path.

| Data | Repository location / rule |
| --- | --- |
| System1 applied human decisions and operation history | Consistent authority snapshots in `system1/saved-records/`, including the hash-matched immutable migration workbook, named human assessment holds and recovery manifest. Keep source identities/version links and their referenced originals under `system1/Data/`. |
| Workbench work selected for retention | Save the downloaded full workspace ZIP into `workbench/saved-packages/`. This directory is outside ignored runtime and is eligible for an explicitly requested Git sync. |
| Workbench edits saved only in the local application, unexported work and old engineering ZIPs | Outside the selected Git retention scope. The existing local service is not reset or cleaned by this policy. |
| Sessions, caches, logs, temporary extraction results, machine execution state and `.venv` | Remain excluded. Rebuild environments using [ENVIRONMENT.md](../ENVIRONMENT.md). |

For Workbench retention, use **Settings → Collaboration → Export full workspace → Download full workspace**, then select `workbench/saved-packages/` as the save location or move the downloaded ZIP there. Export includes all saved work within the exporter scope, with referenced originals and history; it does not cherry-pick individual fields. Merely pressing Save in a material does not add anything to Git. A downloaded package is not automatically pushed. Only deliberately selected packages belong here; old test packages are excluded.

On another computer, rebuild the environment and use **Import work** to preview the ZIP, resolve conflicts and confirm synchronization. Do not extract it over live SQLite stores. No Workbench package is selected in the initial 2026-09-16 catalog. The System1 recovery package is a separate authority restore, not a Workbench Import work ZIP. See [System1 recovery instructions](../system1/saved-records/RESTORE.md).

The repository is public as checked on 2026-09-16. Only files selected for publication belong in these directories; credentials and confidential customer originals stay local. Packages above the ordinary Git file limit require a separately authorized GitHub asset/LFS route rather than unignoring runtime.

## Current source workflows

Add sources expands into three nested entries in the left sidebar. **Official website** needs only the official URL: click **Inspect source**, wait for retrieval and content inspection, then review/edit the generated fields and click **Add to review**. Inspection alone does not create a source-review task. **Upload file** keeps the original local: select an original PDF, HTML or XLSX, then click **Parse file**. Submitting an unparsed attachment runs the same mandatory inspection first. Both routes display a loading spinner and stage text, block repeat submission while busy and retain input after a failure.

Basic inspection proposes title, publisher, version, classification, jurisdiction, language, document type, source description and review-field values. The five rating suggestions include their reasons and evidence. Unknown values display **Needs review**; public readability is not proof of reuse permission. Expand **Generated review information** for editable metadata. Source review retains original inspection evidence separately from later human edits. Adding creates a PENDING candidate; human registration and inclusion remain separate.

For uploaded files, Official source URL is optional and should be supplied when available. Use × to remove the selected file and reset the form. Switching subpages or leaving Add sources clears unsubmitted files and fields. Source-review and material drafts keep their existing protection. Basic source inspection is separate from material content extraction; it uses bounded local native-text rules, reports unreadable/limited scope and does not run OCR, an external model or legal interpretation.

**Source discovery** separates **Check existing sources for updates** (registered URLs and file hashes, no search API) from **Discover new sources with API** (currently Not connected). Changed files request source re-review; they never overwrite the retained original or establish a legal version. Skipped and failed checks are listed explicitly.

In Source review, filter **Review needed** by any individual check type, including a type within a combined task, and sort by source ID, type or age. **Pending-Include** retains previous human Include intent while effective selection remains Pending. Explicit re-review restores Include; routine sampling alone preserves current eligibility. Every status stays in the database for traceability.

In Source register, **Open file** opens the fingerprint-checked original from its classified folder in the OS default application. The **Version / last check** column preserves explicit version numbers. Otherwise it shows the latest recorded system check attempt as **DD-MM-YY**, including completed update-check results from the local database. Publication dates are not used as this fallback. Opening or refreshing the list does not advance the date; absent check evidence displays **Not checked**. Full timestamps remain available on hover.


## Current UI (2026-09-14)

Open the root Open Workbench.command or http://127.0.0.1:62742/ for the loaded redesign. Activation, completed zoom acceptance and recovery boundaries are recorded in [the execution checklist](../project-support/ui-redesign-20260914/execution.md). The older local-delivery-rc1 examples below are retained historical evidence, not the redesigned runtime status.

Use the left sidebar to choose **Sources** or **Materials**. Sources contains **Add sources**, **Source review**, **Source register**, and **Review history**. Materials contains **Material review** and **Archive**. One Settings entry sits at the bottom of the sidebar and displays the selected reviewer name. Its menu opens Collaboration, Runtime status and Automation as global dialogs. The Smarter Compliance mark toggles the sidebar. Page-switching child navigation belongs under its parent on the left; search, filters, sorting and Refresh stay with the page content.

- Add sources accepts a source URL or an original PDF, HTML or Excel file and editable metadata. Adding creates a pending candidate. Source discovery has separate registered-source update checks and API-based source expansion. The expansion entry displays Not connected until a search API service is configured.
- Source review groups outstanding work by source. Open a title to compare the original and review fields. H/M/L changes remain personal edits until Save or explicit Confirm review. Save preserves progress without changing the effective source. Confirm review previews the proposed effective selection before application. Missing originals and unresolved conditions remain governed by their existing checks.
- Source register is the complete numbered table, including PENDING. Details are read only. Request review creates a pending task. Review history presents recorded review actions, including applied reviews whose source still needs work; it is not another source register.
- Material review uses a full-width list and the same four-pane detail for extraction, content review and inspection. The original, extracted content, Requirements and Interpretation panes remain side by side; each has a collapse/restore control. Drag a separator or focus it and use arrow keys; narrower views retain readable panes with horizontal scrolling. Each pane scrolls independently.
- Save (also Cmd/Ctrl+S in material review) is separate from completion. Archive saves the current draft first and requests an explicit saved-content confirmation. Any approved reviewer can finalize it; no separate administrator merge-save is required. Content-only archives display **Content finalized · Requirements unfinished**. Automatic Requirement extraction remains **Not connected**; manual splitting and interpretation are available.
- Archive opens the same complete four-pane reader as read-only finalized content. A review task can refer to an exact archived revision without removing that archive. Completing an unchanged inspection closes its task; modified material requires a new explicit archive. Earlier revisions and review evidence remain retained.




The weekly material inspection dispatcher is opt-in. An absent `workbench/runtime/material-inspection-settings.json` leaves it disabled. An authorized operator must choose the timezone, sample size and named assignee before enabling it. The coordinator checks this configuration at most once per minute, freezes the current week's selected archive revisions and creates review tasks with restart-safe deduplication. A reviewer installation cannot dispatch. This redesign does not enable a normal weekly plan.

## Local-delivery-rc1 handoff

**Local trial gate reached, 2026-09-13.** The fixed local closeout is complete for this recoverable candidate. It is not a new formal-environment release. The [fixed checklist](../project-support/product-readiness-20260912/execution.md#fixed-local-delivery-checklist) owns status.

Open the isolated coordinator at **http://127.0.0.1:55542/** or reviewer at **http://127.0.0.1:58814/**. Both use the current frozen workstream code and existing component environments; [loaded fingerprints](../project-support/product-readiness-20260912/workflow/archive-inspection/rc1-loaded.json) match [local-delivery-rc1](../project-support/product-readiness-20260912/baseline/local-delivery-rc1/manifest.json). The root Open Workbench.command still opens the normal workspace, whose service was not switched. Third-pane Process remains unavailable.

Complete engineering example: open TS002 **ENGINEERING FIXTURE · Excel measurements** in Pending materials; read the saved worksheet and use each block's Original action. Correct a table cell and note, then Save material. Reopen to verify the saved partial version. Review my changes shows differences; explicitly adopt only the reviewed result. Whole-material content confirmation is separate. Archive retains accepted revision 2. Its engineering spot-check history contains a passed Empty sheet check and a resolved formula-warning follow-up. My submissions exports selected saved work; the coordinator imports it, compares, explicitly adopts and returns an adoption receipt. The verified table conflict used reviewer 13 and coordinator 14, explicitly reconciled to original 12; current master revision 4 remains unconfirmed. These are synthetic engineering decisions, not real colleague review.

For an old spot-check page that cannot save, use **Compare saved check**, inspect both notes and deliberately combine needed text. Opening combined progress does not save; range checks reset. Recheck the displayed original, then **Save check progress**. Passing/resolving is a separate explicit action.

All fixed local engineering items pass. Actual Chrome 200% zoom verified original/content switching, table editing/save/reopen and the keyboard-accessible confirmation dialog; zoom was restored to 100%. Post-restart saved-material/archive/receipt reads and the existing reduced-preference/width checks are complete. No additional product optimization belongs to this finished round. The final zoom exercise saved reviewer personal revision 4 with unchanged table content; no adoption or confirmation occurred.

The three most useful later colleague checks are: (1) complete one real material, locate omissions and distinguish saved/adopted/confirmed states without coaching; (2) recover their own work after refresh, interruption and a second editor's conflicting changes; (3) perform an actual Windows work-package/result/receipt round trip and verify original locations and history. These remain independent later acceptance, as does formal deployment.

Recovery: the [candidate code copy](../project-support/product-readiness-20260912/baseline/local-delivery-rc1/code/) and [stopped isolated data checkpoint](../project-support/product-readiness-20260912/baseline/local-delivery-rc1/isolated-checkpoint/manifest.json) have verified hashes. The latter covers the coordinator fixture and reviewer, with links to existing project code/environments; it is specific to this workstation and the recorded paths. Preserve any newer saved work first, stop the affected isolated service through Exit workbench, and restore only the corresponding recorded isolated paths. Never restore these files into normal business stores or over a running service. The full normal-data backup/restore procedure remains in [Explicit local backup and restored inspection](#explicit-local-backup-and-restored-inspection).

If an isolated service needs to be resumed, maintenance uses the existing `project-support/product-readiness-20260912/serve_isolated.py` with `coordinator` or `reviewer`, through `workbench/.venv/bin/python` from the workstream root. It reuses the preserved fixture and never creates a replacement project. The candidate manifest is a file-set identity, not a Git commit; no repository push, distribution or new service installation occurred.

## Human-led material workspace

This section describes the implemented material interface and its intended operation. It is a usage guide, not an acceptance or runtime-activation claim. Check [PROJECT_STATE.md](PROJECT_STATE.md) and the [workstream state](../PROJECT_STATE.md) for the currently loaded version and dated evidence. The [human-led goal](../project-support/design/human-led-workbench-goal.md) governs current scope; the legacy workflows later in this guide retain their own history and compatibility meaning.

Open [Open Workbench.command](../Open Workbench.command), select the named reviewer and enter the material workspace. Source Management System has its own source/task list and detail area. In Requirement Extraction System, **Pending materials** directly lists eligible originals, including unstarted ones. Open a listed material; **Open a source snapshot** remains a secondary shortcut. The active source version stays visible. Opening creates no extraction or structured Requirement result.

### Read and correct one material

The workspace contains **Original document**, **Extracted original text** and **Structured requirements**. Each pane scrolls independently; drag the separators to change widths. The Materials list and navigation can be collapsed. At narrow widths, use the clearly labelled pane buttons.

1. Read the saved original in the left pane. The updated PDF reader displays the saved document with continuous pages, selectable original text when present, **Find**, **Page**, **Zoom** and **Rotate**. **Open reader** opens the same current page at full browser size. **Page image** switches to the independent image preview, retaining the current page; **PDF reader** switches back. Older loaded backends retain the image reader with Previous/Next/Go controls. Reading does not extract or confirm content. Use **Location** for HTML, or **Sheet**, **Row** and **Column** for Excel. **Open original** retains access to the untouched file. The full reader retains its current page, zoom and rotation when refreshed or retried. If loading fails, use **Retry**, **Open original**, or **Workbench** to return and check the selected material/reviewer. Reading recovery does not change review content or confirmation.
2. Choose **Extract** when you want a machine candidate. Your saved human content remains unchanged while extraction runs. **Refresh candidate** checks that request's status; opening, scrolling or saving does not start another conversion.
3. On an untouched empty material, the first candidate appears as an editable preview. Correct it and **Save material** to retain personal progress with machine provenance; no review is confirmed. For subsequent extraction, use **Compare / resolve** to inspect the prior candidate, current human work and new candidate, then choose **Keep**, **Adopt** or **Edit / merge** explicitly.
4. Correct text, block type, heading level/parent, source numbering and order in the middle pane. Use **Split at cursor**, **Merge with next** and the add-content controls for omissions. Use heading level arrows separately from sequence arrows. **Rebuild table** previews selected adjacent blocks as rows/columns or pasted tab-separated values, retains original text and links in transformation history, and replaces only those selected blocks. Tables retain editable cells, insertion/deletion at a chosen position, merge relationships and notes. Images link to original pages or regions; they are evidence references, not generated illustrations.
5. Keep source links and related-content associations accurate. **Original** on a block navigates to its recorded page, HTML location or worksheet range. If a precise location is unavailable, inspect the complete original and correct the association rather than assuming one.


### Sources, submissions and repeat work

**Source Management System** retains source ratings, links, provenance, applicability, candidates, acquisition/file operations, inspections, reported problems and historical re-review. It uses its own list/detail interface. The coordinator previews a source review then confirms and applies once; colleagues save personal proposals. Missing originals prevent INCLUDE but do not prevent source review. See the [source guide](../system1/USER_GUIDE.md).

**My submissions** stays inside the active workspace. Select saved source reviews, material drafts, source-task proposals or spot-check results, describe completed scope and remaining work, and download one immutable collection ZIP. Only selected saved results are frozen. Import produces pending items; source/material conflicts remain in their content context. **Task results** compares inspection and dedicated source-task outcomes, with explicit per-item choices and downloadable adoption receipts. Changed task versions require a new check instead of applying the old result as current.

**Archive** holds main versions adopted by the coordinator and explicitly confirmed for content review. **Continue editing** restores an existing personal draft or seeds from the current main, and places work in Pending. **Create spot-check** also places its task in Pending while retaining the original archive. Saving, submitting and passing a selected check cannot independently claim whole-material completion. Names, versions, original bindings, reports and prior decisions remain available in history.

### Save, resume and confirm

**Save material** durably saves partial content, issues and checked scope. It does not mean review is complete. Check the visible unsaved/saving/saved/error state. A failed save leaves the local draft available. Save before switching materials, leaving the workspace or changing the reviewer. Browser draft recovery supplements the server save; it does not replace it.

Browser recovery is local to the current browser profile and origin (including the service port), named reviewer, material and editing tab. Small drafts use browser local storage; large drafts use IndexedDB. **local recovery saving** means the browser write is still pending; keep the page open. **local recovery saved** appears only after the local write succeeds. On reload, the workspace reads the recovery record before announcing recovery. If browser storage is unavailable, the warning tells you to keep the page open and use **Save material**; a failed local recovery write does not prevent a server save. Closing or refreshing while the latest write is pending can lose those latest unsaved edits despite the close-page warning.

Each tab keeps its own recovery record. A browser Web Lock prevents a duplicated or opener-created tab from sharing a live tab’s writable record; refreshing keeps that tab’s owner identity. If Web Locks are unavailable, each document uses a fresh owner and reads its previous document’s record for recovery, without deleting another live tab’s record. A separate reference for each reviewer and material changes only after a successful local journal write, so repeated refreshes without editing still recover the last written draft even when another tab has a newer shared draft. If that tab has no draft, it can offer another tab's draft for the same reviewer and material; a newer server revision requires comparison before merging. Switching reviewer, browser profile or service port does not move recovery records. Clearing browser data removes them. Local recovery is not a server save and is not included in the server backup package. Save each material on the server before backing up or moving the workbench.

Reopen the material to recover its saved version. **History** displays earlier revisions and recorded actions. **Restore this version as a new draft** creates editable work for a later save; it does not reactivate a historical confirmation. **Review existing work** opens retained legacy review, while **Import existing content** brings available earlier effective content into a separate candidate. Old automatic or human A/B decisions remain historical and do not become new whole-material confirmations.

If the original cannot be opened, **Retry reading original** retries only the reading pane and preserves unsaved edits. If access remains unavailable, save your work and use **Report original problem**. A failed extraction retains its earlier attempt and saved content; check the original before explicitly using **Extract** again. Detailed failure evidence remains available without filling the main workspace with internal paths.

At the end of the middle pane, complete **Whole-material review**. Inspect every required original range, including PDF pages or worksheets where extraction found nothing. Correct omissions, resolve content issues and check source associations/dependencies. Save that work, then use **Confirm content review**. The dialog names the saved content version and missing original ranges; **Open review checklist** takes you to the remaining checks without marking them reviewed. The final button becomes available only after all prerequisites and the explicit final declaration are checked. The server checks the saved version, full scope, substantive issues and current System1 source status. Machine scores and block counts cannot complete this review.

An original that is incomplete, unreadable or incorrect needs **Report original problem to System1**. Describe the location and problem. This creates local source follow-up; it does not replace the original or mark the issue resolved. Source follow-up must be resolved before content confirmation.

The completed content label is **Content review complete · Requirement structuring not connected**. The third pane remains **Not connected** and **Process** is disabled because the final structure and processor have not been supplied. No final Requirement form/schema or semantic result is claimed.

### Changes, conflicts and failed extraction

The middle pane opens in **Reading** mode. Use a block's **Edit** control for a focused correction, or switch to continuous editing. Content search covers the entire draft, including blocks outside the current page; chapter navigation uses its recorded headings. Large tables display bounded row/column windows. Edits in earlier windows remain in the same draft when navigating or searching.

Use a block's original link to locate its evidence; where several links exist, choose the intended original range. From the original reader, inspect the linked content for the current page/location. PDF region selection supports dragging a rectangle and entering numerical bounds. A rectangle preserves an original image association; it does not recognize text or perform OCR.

After saving a correction, **Review impact** explains which original ranges need another check. Provably unaffected checks retain their previous reviewer/version provenance. Changes with uncertain impact still require full review. Every body change or withdrawn check revokes final confirmation; the last valid confirmation remains in history. Complete the remaining checks on the saved version and confirm explicitly again.

If an older open tab reports that the material interface was updated, refresh it and recover its retained local draft. The server refuses old-client mutations rather than allowing an outdated candidate comparison to submit decisions.

Re-extraction creates another candidate. It never overwrites human text, deletes omitted blocks or updates downstream content automatically. An upstream source change flags the affected workspace as stale while preserving its body and history. Open the newer snapshot and compare the retained work against it. A result produced from an older input stays labelled stale.

If another tab or reviewer saved a newer revision, the workbench retains your local draft and offers a comparison with the newer server version. Reconcile and save a new revision; repeated requests must not duplicate saved operations. After extraction failure or a service restart, saved human work and request/history records remain separate from the failed or pending candidate.

### Original-reading limitations

| Original | What the reader provides | What the reviewer must distinguish |
| --- | --- | --- |
| PDF | Local PDF reader with continuous pages, source-position text selection, search, zoom, rotation and a full-reader link; independent Page image fallback | Scanned/blank pages can lack selectable text; no OCR runs on viewing. Text layers can differ from visible marks and are not confirmed extraction. Errors require original comparison or the image fallback. Older parents retain the image reader and optional browser plugin, whose availability is not guaranteed. |
| HTML | Complete isolated saved markup with selectable text, headings, tables and stable locations | Scripts, source styles and external assets are disabled. Static disclosures are opened. Missing images or layout differences remain visible limitations; no live website replaces the snapshot. |
| XLSX | Worksheet switching, continuing rows/columns, cell addresses, merge relationships, formulas and saved values | Missing caches are not calculated. Hidden content is labelled and remains navigable. Native styling, drawings, charts and conditional presentation are not reproduced. Inspect the preserved original for those features. |
| XLS | Preserved download and explicit compatibility notice | A human-created XLSX parsing copy needs recorded lineage; no silent conversion occurs. |

The [material interface guide](../system2/docs/contracts/human-material-workbench.md) documents service boundaries, source references, worker behavior and isolated engineering commands.

## Retained System1 and legacy review reference

The dated sections below describe existing System1 operations and retained older System2 A/B interfaces. They do not supersede the material workflow above or establish new runtime/quality acceptance. Legacy classification and output operations are separate compatibility actions.


## Saved decisions and source-aware Excel status | 2026-09-10

System1 and System2 show saved decisions separately from their Excel snapshots. System2 also checks the current source version: a source-information change can make Excel pending even when no content decision changed. Failed, missing or stale source checks show an unconfirmed status; already saved decisions and the previous verified download remain available. Synchronization and retries run in the background.

## Original-page comparison | 2026-09-10

In System2 Content proofreading, choose Inspect original PDF pages, open a page and select Check this original page. The saved comparison includes original-region highlights, correction drafts and explicit unverified scope. Recheck after modifying content. A saved correction is not A/B acceptance. Excel synchronization status shows the database and snapshot versions separately. See [the comparison workflow and limits](../system2/docs/contracts/original-verification.md). The new stage-specific weekly sampling rules remain pending implementation.

## Legacy two-stage workflow | 2026-09-09

Open the shared launcher and select a named reviewer. System2 → Pending review shows real jobs; choose an INCLUDE source and click Start processing. Confirm full-text coverage and content/structure before classifying Requirements, context and exclusions. Use source evidence, corrections, split/merge or missing-content supplementation where needed. Save draft is not acceptance. Include reviewed content to reopen an earlier result. Pause is checkpoint-based; Request reprocessing preserves the old generation and invalidates its deliveries.

Confidence settings owns all thresholds, initially 95%. Uncalibrated results require manual review regardless of threshold. Raising thresholds reopens affected machine results; human decisions/drafts remain protected. Optional assistance is disabled without explicit configuration. System1 Machine assessments shows evidence-supported five-dimension proposals and preserves named human decisions.

In each System2 task, expand **Scores and evidence by dimension** to inspect A text accuracy, original coverage, structure/relationships and reading order, and B classification, original association and parent/subitem correctness. Missing or unsupported dimensions remain unknown. A human confirmation does not create a machine score; the lowest supported required dimension controls automatic routing.

System2 Weekly checks samples original-side A scopes and completed positive/negative B judgments, including human decisions. Normal A/B activation remains disabled pending authorization. System3 Incoming requirements displays incremental deliveries and source completeness; semantic processing is not connected. Original HTML is a script-free text view, PDF opens its registered full original, and XLSX supports paged cells, formulas/caches, hidden state and merged-region metadata.

See the [current workflow contract](../system2/docs/contracts/two-stage-review.md) for authority, operations and compatibility. Older dated integration/demo descriptions below are historical; they do not replace this workflow.


The daily entry point is [Open Workbench.command](../Open Workbench.command) at the root of `05_Working area of requirements side/`. Double-click it to start the local service and open the default browser; subsequent launches reuse the same service. Closing the browser does not stop submitted jobs. Select “Exit workbench” at the bottom left to stop safely. No login startup or operating-system background service is installed.

## Overview and navigation

The redesigned top row provides Sources and Materials with the six modules described above. There is no persistent global sidebar or separate System3 navigation.

Overview is retained only as a compatibility surface, not ordinary navigation. A saved original, a personal draft, an accepted main version and a complete content review remain distinct. Counts do not establish extraction quality. Sources may have multiple unresolved reasons; reason counts cannot be summed into a count of sources. Historical A/B review remains available only through the explicit compatibility links.

## Retained weekly source and legacy A/B checks

The workbench service checks for a missing current-week batch while running. Monday targets in Europe/Oslo are System1 5 governance records, System2 A 20 original inspection units and System2 B 5 completed classification judgments; System3 is off. System1 retains its existing schedule. Normal A/B activation remains pending explicit authorization. A running interface does not activate it. An enabled stage catches up only the current week after downtime. Preserve the owning databases, managed originals and histories when migrating the project so batches are not sampled again.

System1 randomly samples currently effective included sources with no unresolved tasks, excluding items still awaiting a previous check. If fewer than five are eligible, it samples all and records the actual count; zero eligible items produce an empty batch. Tasks appear under System1 → Pending review. Dashboard’s “System1 checks” opens the filtered list. Check the links, original and register details, then select “Correct”, or enter a note and select “Report an error”. An error creates a corrective task.

In System2 choose Weekly checks, then Pending or Review history. A shows complete original scopes even when nothing was extracted; B retains positive and negative classifications where available. Compare the original on the left with the result on the right, add the exact evidence and record agreement, a problem or an unverified result. Reported problems stay pending. Open the repair task, correct the ordinary A/B result, then return to record a separate follow-up. B shows the current subdivision/counting policy during follow-up. Failed submissions retain the draft. Earlier machine-only checks remain separately available.

The overview displays the current week and four preceding weeks. Observed agreement is initially correct items divided by sampled items, displayed only after the target is met and all findings are resolved. Missing B classes, short samples, catalog failures and unfinished checks remain explicit. This monitoring measure is not independent acceptance accuracy. Excel contains a one-way Weekly checks audit sheet after background synchronization. See the [sampling contract](../system2/docs/contracts/weekly-original-sampling.md) for original-unit definitions and limits.

These are retained source and legacy A/B inspection mechanisms. Current material spot-checks use the independent Archive/Pending flow below. No new schedule or background service is enabled by this workflow correction.

## System2 repairs and previous decisions

Use the [System2 daily repair guide](../system2/USER_GUIDE.md#daily-repairs-source-follow-up-and-history) for failed-original follow-up, scan transcription and linked source context. The same screen supports table cells, rows, shared cells, footnotes and cross-page context; there is no Excel decision entry. For an original empty cell use **Clear cell text** and supply the source evidence before applying.

In **Review history**, expand a decision and choose **Open current result to review**. This opens its current A or B state without applying a change. The saved human classification is displayed and remains selected until explicitly replaced. New B entries retain classification before/after, time and source version; unavailable older fields are not inferred. The source can remain incomplete while an individually checked Requirement is available.

## Legacy source-operation reference

1. At the top right, select Ana Jokic, Daniel Restad or Weijie Tang, listed alphabetically by first name, then select “Use this name” or “Switch reviewer”. This identifies the operator on a trusted local machine; it is not password authentication. Switch names when the operator changes.
2. Select a System1 task and inspect the official page, registered retrieval link and local original. PDFs open in a full reader with paging, zoom, search and a separate-window option. The reader verifies the registered version and file fingerprint. HTML has a read-only text preview; open the original through the download link. Source scripts do not execute in the workbench.
3. When scoring is required, select H / M / L for each criterion. Light styling shows the previous score; dark styling shows this review’s selection. A previous score is not confirmation. All five selections trigger submission automatically. Scoring and original-file gates remain separate.
4. Deferring a source or removing it from scope requires a reason. Notes save automatically as drafts; saving a draft does not complete a decision.
5. Correcting a link saves register information only. It does not download a file or claim verification. After checking a reported issue, mark it verified, enter the evidence and record the verification result.
6. Replacement files are staged locally first. After the initial format check, a person confirms identity, completeness and usage permission before submitting acceptance. System1 validation and snapshot rules still apply. A format check does not prove regulatory identity or semantic completeness.
7. Recent submissions show submitted, applying, waiting for release, applied, needs attention or stale-page states. System1 database decisions save independently of Excel. Its saved/exported revision bar distinguishes pending, synchronizing, synchronized and failed output; closing Excel permits automatic synchronization. If the submission result is unknown, “Retry submission” reuses the original request ID. Stale or field-invalid decisions remain available; reload and check them again. A source-version change preserves note and corrected-link drafts while clearing confirmation of old scores.
8. Review history presents named database operation history and browser requests, including retained imported workbook history. Complete sources and receipts are retained; the interface is not a second source register. Imported Excel reviews display the original ACCEPT / REJECT / INCORRECT result and notes. If the original has no review date, the displayed date is explicitly the synchronization time. Sources with remaining tasks show colleagues’ previous decisions and the unresolved reasons. An old ACCEPT does not backfill five-criterion scores.

Connected source actions cover scoring, selection, link correction, verification of reported issues, replacement files and random checks for enrolled sources. New discovery/registration is outside the current authorized scope. System2 has live processing and two-stage review; System3 semantic processing remains unconnected. The retained sample practice below is historical.

## Historical System2 review demo

System2 → Pending review uses the same vertical queue and search field as System1. Items display their source ID, title and pending status. Only unfinished and “Needs follow-up” items remain in the queue. Completed items move to Review history, where the original and decision details remain accessible. “Reopen sample” returns an item to pending review.

Five samples demonstrate PDF text checking, sentence joining, omitted tables, HTML list relationships and Excel header ownership. For PDFs, the historical source page and red box appear on the left, with zoom and full-page viewing. On the right, “Accept & next” or “Correct text” advances after saving. An omitted table records its scope and requests reparsing without requiring transcription of the whole page. Illegibility, omissions and reparse requests remain follow-up items, not accepted reviews.

“Screenshot does not match? Open full PDF” expands the full reader while preserving the draft on the right. “Choose PDF” selects the same original from the desktop and checks the PDF header and complete SHA-256. A matching file is displayed only in the browser and is not uploaded. Page buttons are English; the operating system controls its native file-dialog language. HTML and Excel are clearly labeled synthetic examples, retaining adjacent headings, headers and cell coordinates in the source panel.

Demo drafts and history are stored per operator in the current browser. Refreshing or switching items preserves drafts. Clearing browser data removes practice records; they do not synchronize across devices. The demo does not call production decision, parsing or upload interfaces and does not enter production history or Dashboard accuracy. See the [System2 demo contract](docs/system2-review-demo.md) for boundaries and provenance.

## File ownership

- `ui/`: browser interface.
- `src/local_workbench/`: HTTP service, operator/request storage, serial worker, environment adapters and launcher.
- `runtime/workbench.sqlite`: operators, sessions, note drafts, requests and receipts. This is persistent data that requires backup, not disposable cache.
- `runtime/uploads/`: staged files and source records. Retain pending files and failure evidence.
- `runtime/server.json`, `listen-port.json`, lock files and `service.log`: local runtime information, excluded from shared configuration.
- System1 owns authoritative source state in its configured governance database; Data retains originals and Excel is a protected one-way view. Excel opens Instructions and exposes Instructions, Categories, Source Register and Machine confidence. Dashboard and Human Operation Desktop are `veryHidden` compatibility sheets preserving calculations and review history. Daily dashboards and human actions use the browser. Controlled saves maintain this layout; do not delete hidden sheets or rewrite formulas.

This component uses its own `.venv` and the standard library only. Follow the shared [environment guide](../ENVIRONMENT.md#system1-and-the-workbench-on-macos) to recreate the workbench and System1 environments on a new computer. Copying an environment directory is not a portable installation.

Validation commands, run in this directory:

~~~text
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
node --test tests/*.mjs
PYTHONPATH=src .venv/bin/python -m local_workbench --no-browser
~~~

Frontend state tests use the development machine’s existing Node.js; it is not part of the production Python environment.

The service listens only on `127.0.0.1`, preferring the previous port recorded in runtime and choosing an available port if occupied. A port change creates a separate browser storage space; demo records remain in the old space. POST requests validate Host, Origin, CSRF and the local session. Originals are not sent externally. Remote access, automatic downloading, external models, full parsing and publication are not authorized.

See [PROJECT_STATE.md](PROJECT_STATE.md) for current status and [Workbench design](docs/local-workbench-design.md) for design rationale. The shared operating rules are in [AGENTS.md](../AGENTS.md) at the `05` workspace root.

## Requirement subitems in B

In **System2 → Pending review → Requirement judgment**, a content item that passed A can use **Create / replace requirement subitems**. Add exact original selections or unique pasted quotations. The complete parent and its shared footnotes remain available. Review unassigned text, choose a provisional count rule, and submit the decision. Generated subitem labels are never original source numbers.

Accepted items can be reopened through **Browse all original content**. Replace the subdivision or choose **Remove subitems and classify the complete parent**; both preserve history. If original content or related footnotes change, recheck A and then B before delivery resumes. Drafts and rejected submissions do not complete the task. Excel shows saved parent/subitem counts after background synchronization. [The B contract](../system2/docs/contracts/requirement-subdivision.md) states current limits and pending peer decisions.

## Runtime status

**Runtime status** shows Source service, Material extraction, Saved material storage, Excel output, Source Excel output and Legacy processing separately. It reports the current operation, last check/success, running duration and any sanitized failure. A successful later check clears the active error; the prior error remains available for diagnosis after recovery or restart. A version conflict or known form validation refusal is not an infrastructure outage. Unknown failures, database errors and timeouts remain visible.

`GET /health` identifies the local service and loaded source version; it is not a complete readiness check. `GET /api/runtime-status` provides component evidence and a read-only saved-store probe. Runtime evidence is persisted in `runtime/runtime-status.json`; `runtime/runtime-events.jsonl` records failure/recovery transitions. Neither stores document bodies or raw exception text. Request identifiers, when available, link failures to an action receipt. Successful heartbeat writes are throttled. A failure to persist monitoring evidence is itself shown in the response.

Existing background checks use bounded infrastructure backoff. Extract consumes only explicitly submitted, durable candidates. A failed parser result requires another explicit Extract action, producing a new candidate; viewing Runtime status cannot enqueue extraction. Interrupted pending candidates resume under the owning worker lock. A stopped worker or unreadable saved store is reported rather than treated as healthy. Process-lifetime peak resident memory, thread count and uptime support diagnosis; peak memory is not current memory or proof of a leak.

## Explicit local backup and restored inspection

Save browser drafts, close Excel, use **Exit workbench**, and wait for all processing to finish before backup. The tool refuses an active service, another process writer, a busy owning database, missing Canonical evidence or a missing immutable governance companion. It holds process locks and simultaneous writer reservations on the five owning databases plus the optional System2 job database when present while taking SQLite backup snapshots and copying required resources. If an asset changes during copying, the package remains incomplete and cannot be restored. It does not install a schedule or delete previous packages.

Run from the workstream root, replacing the destination with a new local directory:

```sh
PYTHONPATH=workbench/src workbench/.venv/bin/python -m local_workbench.recovery backup --root "$PWD" --destination /path/to/new-backup
PYTHONPATH=workbench/src workbench/.venv/bin/python -m local_workbench.recovery verify /path/to/new-backup
PYTHONPATH=workbench/src workbench/.venv/bin/python -m local_workbench.recovery restore /path/to/new-backup --destination /path/to/new-restored-workspace
PYTHONPATH=workbench/src workbench/.venv/bin/python -m local_workbench.recovery serve-restored /path/to/new-restored-workspace --code-root "$PWD"
```

The package includes the configured source-governance, source-assessment and Leader databases, the System2 workflow database, the optional System2 job database when present, workbench requests/drafts/policies, source Data, immutable migration companion, referenced Canonical evidence, material originals/artifacts, uploads and owning operational logs. The v2 manifest records file hashes, sizes, references, creation time and code revision. A separate `code/` archive stores the exact local source, UI assets, parser schemas/configurations, public configuration examples, dependency declarations/locks, setup scripts and `ENVIRONMENT.md`. This preserves uncommitted source bytes independently of Git HEAD. Live provider configuration, `.env`, component environments and caches are excluded. Source changes during copying or mismatched source hashes make verification fail. Unrelated old acceptance backups and rebuildable environments/caches are not recursively copied. Browser-local unsaved drafts are outside the server backup.

Restore requires a new destination and verifies every file and database before exposing it. Database payloads and history remain byte-identical; `recovery-mapping.json` records the old and restored roots without rewriting human history. The inspection service links the existing project's code/environments, runs against restored configuration and data, and disables background workers, business actions and legacy evidence endpoints that could follow old absolute paths. Material history, saved content, bound originals and readers are available for inspection on a separate loopback port. The package and original data directories are not required for those material reads after restore. Stop the inspection process after validation.

If the original code changes or is no longer available, extract the verified source archive into another new directory:

```sh
PYTHONPATH=workbench/src workbench/.venv/bin/python -m local_workbench.recovery extract-code /path/to/new-backup --destination /path/to/matching-code
```

Recreate the three component environments using **the extracted** `/path/to/matching-code/ENVIRONMENT.md`, its System1 pinned requirements and setup script, System2 `pyproject.toml`/`uv.lock`, and Workbench `pyproject.toml`. Do not launch the normal workbench from this code-only tree. Once environments are available, run the matching recovery module with `--code-root /path/to/matching-code`:

```sh
PYTHONPATH=/path/to/matching-code/workbench/src /path/to/matching-code/workbench/.venv/bin/python -m local_workbench.recovery serve-restored /path/to/new-restored-workspace --code-root /path/to/matching-code
```

The inspector verifies the selected code against the archived runtime/dependency fingerprints before linking it. Source extraction does not install packages, run setup scripts, apply business decisions or enable scheduling. Older v1 packages still verify their business files but do not contain a source archive; `extract-code` explicitly refuses those packages.

This is an isolated restoration and inspection path. Replacing a live workspace, enabling restored writers or migrating legacy absolute references into a new operational deployment requires a separate, explicit operational action. The package contains recoverable source and dependency declarations, not installed interpreters, native tools, downloaded libraries or models. Rebuilding environments on a new machine remains a separate installation step; the isolated acceptance exercise reused existing component environments while loading source from the recovered archive.

## Offline review with colleagues

Use **workbench/deployment/Open Reviewer Workbench.cmd** on Windows for a reviewer-only workspace. Follow [Windows setup and actual acceptance](docs/windows-offline-review-checklist.md). The ordinary launcher opens the coordinator workspace; those modes are deliberately separate.

1. In the main workspace, Weijie Tang uses **Create work package**, selects sources, source tasks and material spot-checks, and downloads one work ZIP. Give that ZIP to colleagues manually.
2. Each colleague imports it into their own reviewer workspace and selects their real name. **Save material** and **Source review → Save** preserve personal progress. Neither changes the coordinator's main version.
3. Read the original beside the editable text. **Extract** creates a candidate. Compare differences inline and explicitly keep, choose or edit; current human content is retained until application. A resolved identical candidate does not repeatedly demand the same decision.
4. **My submissions** lists saved source reviews, personal materials and checks. Select several results and download one frozen package, including partial results and remaining issues. Frozen packages can be downloaded again; later saves do not change them. The older single-item export remains compatible.
5. In the main workspace, **Import package → Submission inbox → Review submission** opens a merge preview. Disjoint edits appear as pending contributions; conflicting paragraphs, cells and source fields display both versions. Choose **Keep current**, **Adopt submitted**, or **Edit result** at each difference.
6. **Adopt reviewed result into master** creates the new main version and separate source/content receipts. Source partial success is shown separately. **View master → Confirm master content review** is a later, explicit complete-original check.

The coordinator also saves into personal work and uses **Review my changes** before main adoption. No one's local SQLite database should be returned or merged. A work package contains the selected original; a return package cannot create sources or replace originals. Bound-original image references remain linked to that original. External assets are not fetched automatically.

A reviewer's confirmation applies to their saved version. The combined main version inherits only valid unaffected checks and remains unconfirmed until its own full-range confirmation. Main version changes after a preview require a new comparison. Received packages, saved choices and prior versions remain available after failures and restart.

## Unified navigation

Use **Source Management System** for source management and **Requirement Extraction System** for the four-pane human workbench. There is no standalone System3 queue or incoming-feed entry. Manual splitting occupies the third pane and interpretation/check design the fourth. Automatic processing remains disabled. Historical backend records and design interfaces are retained.

## Material archive, spot-checks and working space

**Pending materials** contains unfinished work, conflicts and open spot-checks. **Archive** displays an explicitly accepted and fully human-confirmed main version. Personal save/confirmation alone does not archive a material. Both categories use the same workbench.

From Archive, **Create spot-check** selects a named reviewer, reason and original ranges. Its task returns to Pending; the accepted archive remains visible and unchanged. **Save check progress** permits partial work. **Pass selected checks** needs the selected range checks, evidence note and explicit human confirmation. **Record a problem** retains an open finding. After main content repair, review the current main and explicitly resolve the finding; whole-material confirmation is still separate. If another accepted version supersedes a pending check, **Restart check on latest archive** preserves the old record and starts fresh coverage. Select tasks in a work package and return saved results through My submissions. The coordinator compares and adopts each task under Task results, then can return selected adoption receipts. Importing a result does not pass the check. A changed incoming assignment is retained as a warning without changing the existing personal check or its original baseline; finish or return the old check and request a new task for a changed archive.

The normal material detail fills the available workspace. Drag the three vertical separators, or focus one and press Left/Right (Shift for larger steps). Layout preferences retain widths for the operator. All four panes stay beside each other at narrow widths and browser zoom, with horizontal scrolling when needed. Layout changes never invoke Extract or Process.

## Requirement interpretation and shared API

Use [the current four-pane guide](docs/requirement-interpretation.md) for source colours, reading modes, six editable interpretation fields, checking logic, shared Settings → AI service, candidate adoption, save/review and recovery boundaries. Version-2 full workspace ZIPs include saved splitting, interpretations, rules, candidates and histories. Working copies remain local until Save interpretation.

## Tracing and mapping a check design

Select a saved Requirement card to load its interpretation in the fourth pane. Enter the six formal fields; open **Evidence & gaps** or **AI assistance** only when needed. **Save interpretation** (Ctrl/Cmd+S while editing pane four) saves the design without marking it reviewed. **Source trail** shows the saved Requirement, splitting step, source version and extracted passage, even if later versions change.

**Site Model mapping · optional** holds explicit field comparisons and nested all/any groups. Configure agreed fields once in Settings → Site Model fields, then select their labels in the rule editor. No downstream fields are invented by default. Each comparison records which interpretation field supports it. The QueryBuilder preview is a handoff format, not an executed query or compliance result. Leave unknown groups unmapped. See [the maintained contract](docs/requirement-interpretation.md).

Working copies save automatically without submitting a formal interpretation. Use **Interpretation drafts** to resume, and **Review changed sources** to find affected fields after source changes. Choose **Not explicitly stated** with a reason when the reviewed source omits a field; this never means an unconditional rule.

## Simplified Requirement checking

See the [current relationship and interpretation workflow](docs/requirement-interpretation.md#simplified-relationship-and-interpretation-workflow-2026-09-16). Open an Rx entry in either pane. Scope, Conditions and Demands follow the third-pane decomposition; each has an editable Logic field and an optional AI suggestion. Accept adopts the candidate; Save persists the draft.
