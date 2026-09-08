# Workbench Project State

Updated: 2026-09-08. Current checkpoint: `CONTINUE`. The English interface, three-person operator roster and service-owned weekly sampling are implemented; see the dated updates below.

Entry-point update (2026-09-08): [README.md](../README.md) and [AGENTS.md](../AGENTS.md) are at the `05` root alongside the three systems and this workbench. The launcher is now [Open Workbench.command](../Open Workbench.command), also at the `05` root; cross-system integration state is in [PROJECT_STATE.md](../PROJECT_STATE.md). This update changes launcher resolution and documentation. Service directories, persistent data and business interfaces remain in place.

## Documentation cleanup | 2026-09-08

Maintained workbench documents are English. Design and implementation-plan documents now live under `docs/` in this component, with links updated. The shared `../Open Workbench.command` uses English messages and resolves this directory from its own location. Executable permission, shell syntax and an isolated path/module check passed. No production service was started and persistent runtime data was not changed by this cleanup.

## Current positioning: the complete Requirement workbench | 2026-09-07

Decision: `ADJUST`. The platform serves System1 source management, System2 extraction review and System3 semantic completion. Requirement overview first presents each system’s responsibilities, actual connection status, pending work and key outputs, followed by five-week sampling trends. Existing System1 source charts move into collapsed-by-default System1 details, retaining chart filters and the full queue entry.

Metrics preserve system and unit boundaries: sources, extraction review items and semantic completion items are not added together. System2/3 production metrics are null and display “Not connected”; demo records do not enter production statistics or sampling accuracy. The System1 card opens the production queue, System2 opens the existing independent demo, and System3 opens its design status. This change covers platform projections, navigation and positioning documentation without connecting or modifying the System2 parsing project.

Validation: Workbench Python 18/18, frontend state 14/14 and script syntax checks passed. The production page was checked for all three system entries, expanded System1 details, the seven-source missing-original filter and return to the full queue. No horizontal overflow at 1024px or 360px. The service loaded the update on its existing port, preserving operators and named receipts. A user-submitted review had already applied before inspection; the observed pending count was 30, so the earlier count of 31 must not be a fixed assertion. Read-only reconciliation: `runtime/requirement-overview-verification.json`.

## Completed alignment: Excel entry and documentation | 2026-09-07

System1’s production Excel Instructions now describes the browser workflow and opens by default. The former Dashboard and human-operation sheets are `veryHidden` compatibility stores. Root entry points, the Agent contract, guides and initial implementation-plan status are aligned. The workbench owns the daily dashboard, named review, drafts and automatic processing; System1 owns source state and history. Exact workbook versions and item-level reconciliation belong solely to [System1 state](../system1/PROJECT_STATE.md).

Workbench Python 17/17 and frontend 14/14 passed for this update. Existing System2 demo and production-interface boundaries were unchanged; the System2 project was not modified. Handoff counts, former names and old hashes below are historical evidence from their respective checkpoints.

## Ownership and handoff scope

The user designated the System2 architecture-planning task as the workbench’s main task, taking over implementation already delivered when the review-synchronization task (`01a07b60-6dd9-78c2-b83a-cb2338759a9d`) was interrupted. Other tasks continue System2 parsing, verification and business rules. This task does not rewrite that system’s code, inputs or Canonical.

- Daily entry: `Open Workbench.command` at the `05` root. The production page uses this directory’s `ui/` and local service. Conversation artifact `compliance-workbench.html` is a read-only snapshot generated from actual data, not a production decision entry. The early PDF interaction prototype remains historical evidence as `compliance-workbench-early-review.html`.
- Inherited implementation: System1 production-data reads, named operators, drafts, persistent requests, automatic application, hidden operation-sheet compatibility and review history. Launch and write boundaries follow [AGENTS.md](../AGENTS.md) at the `05` root.
- At handoff: 87 sources, 26 pending sources, 70 registered originals and 38 effective included sources. Named completed history contained 20 Ana records, 22 DR records and two earlier named records. System1 remained the authoritative business source.
- At handoff, System1 passed 68 regression tests and Environment Doctor returned PASS. The assertion covering the old Dashboard hidden-column issue passed.

## Interface and reliability changes in this round

- Retained the user-selected simple light layout, with two-level sidebar navigation: System → Pending review / Review history.
- Added a Dashboard derived from the same System1 snapshot: source selection, original storage, source composition, pending reasons and priority entries. Dates indicate data-read time, not fabricated historical trends.
- `dashboard.py` projects the adapter’s business results; `dashboard.js` handles charts and navigation. Pending counts use sources; reasons may overlap and must not be summed into a source total.
- `evidence.py` checks registered PDF fingerprints and supports browser Range requests; `evidence-viewer.js` provides the full original reader. Original HTML remains a read-only text preview/download. System2 may reuse the reader later; no System2 production tasks or decisions are connected yet.
- Drafts bind to source/task revisions. A new revision clears selected scores and verification boxes while preserving text drafts. Request IDs persist before sending; uncertain receipts retry the same decision. Named history is deduplicated against corresponding successful browser receipts.

## Validation and integration boundaries in this round

- The complete 134-page CS004 PDF was viewed against an isolated workbook, with native paging and zoom controls available.
- In an isolated browser test, four scores did not submit and survived refresh. The fifth automatically submitted and applied the decision, reducing pending sources from 26 to 25. The production workbook did not participate.
- Component Python 9/9 and frontend state 4/4 passed, covering metric definitions, PDF versions and Range, HTTP boundaries, request idempotency/recovery and draft revisions. Handoff evidence for System1 regression 68/68 and Environment Doctor PASS was verified. This round did not change System1 code.
- Browser checks: the missing-original chart opened seven sources; reported issues opened four. Isolated history contained 45 records, with the test decision appearing once. Production retained 44 named records.
- Updating PA008’s source version in the isolated copy cleared old scores, preserved text drafts and displayed the correct version. The CS004 full reader showed the registered filename and 134-page original. Switching sources cleared a stale version notice.
- Fixed bar widths blocked by the strict page security policy using native progress elements, without relaxing the policy. Production pages had no horizontal overflow at 1024px or 360px, clear legends and no browser errors. Unchanged statistics refresh only the read timestamp, preserving expanded counting explanations and keyboard focus.
- The production service loaded the new code. The root launcher succeeded in a normal macOS environment and reused the same service. A default-browser failure in the restricted tool environment did not indicate desktop-launcher failure. `runtime/server.json` owns the current address; shared configuration does not contain it.
- Final read-only reconciliation remained 87 / 26 / 70 / 38. Production workbook SHA-256 matched the pre-handoff value: `318ca627355911124c090f47830e75a01ea0f850ccb66e6893b9afc5e27321e5`. The production request list was empty; tests submitted no production decisions.
- Pre-handoff source, SQLite backup and before/after checks remain in the [handoff backup](runtime/handoff_20260907/); the final record is [final-verification.json](runtime/handoff_20260907/final-verification.json). The test workspace `/tmp/compliance-workbench-ui-20260907` must not replace production data.

## Visibility of colleagues’ Excel reviews | 2026-09-07

After the user requested synchronization, the original Excel’s 42 rows were independently read and reconciled field by field against the archive, import manifest and production history: Ana 20, DR 22; 15 ACCEPT, 23 REJECT and four INCORRECT. All were already present, with zero new imports or omissions. Original notes and source evidence matched.

The interface now shows original decisions and notes in history, distinguishes synchronization time from unknown review dates, and shows previous colleague decisions with remaining scoring or issues in pending tasks. The 15 historical ACCEPT decisions retain human INCLUDE intent, but scope relevance M still triggers the existing selection gate. This round changed no scores, selections or unresolved states.

Python 10/10, frontend state 6/6 and production-browser checks passed. Production history contained 44 records, including the 42-record batch; the workbook fingerprint was unchanged. Read-only reconciliation and change evidence belong solely to the [review synchronization report](runtime/review_reconciliation_20260907/report.md). The service loaded the new history projection; earlier conversation snapshots do not replace the production workbench.

## Next stage

The isolated test service was stopped. The conversation’s read-only snapshot was checked for chart navigation, two-level menus and layouts at 1024px and 360px. It contains no API calls, draft writes or review submissions.

Continue improving the workbench from actual operator feedback. Connect System2 after other tasks provide production queues, versioned evidence and decision-application interfaces. The full PDF reader is reusable but does not establish completed System2 review functionality. Excel’s old Dashboard and review history remain for compatibility; the browser owns the daily dashboard.

## English interface, unified identities and weekly sampling | 2026-09-07

- All workbench menus, action prompts, validation feedback and charts use English. Source bodies, titles, colleague notes and original review evidence retain their original language. The simple light layout and two-level navigation remain.
- The three current operators are Weijie Tang, Ana Jokic and Daniel Restad. The user confirmed Jay maps to Weijie Tang, Ana / Jokic; Ana to Ana Jokic, and DR to Daniel Restad. The 44 historical signatures were normalized to 1 / 21 / 22 records respectively. Original profile IDs and session ownership remain; original signatures in Excel and import payloads were not rewritten. See the [identity migration audit](runtime/english_ui_20260907/identity-migration.json).
- Sampling now runs inside the service each Monday, five items per connected system, using Europe/Oslo weeks. Persistent batches prevent duplication, retry after lock waits, create only the current week after downtime, record actual sample sizes below five, and exclude unfinished samples. No external downloads, parsing or substituted human judgments occur. The user explicitly excluded Codex automation; the mistakenly created personal task was deleted. The workbench worker owns execution.
- Dashboard provides five-week accuracy charts and weekly details for all three systems. Correct / actual sample size is reported only after all named reviews are applied; missing and incomplete results remain blank. Equal curves overlap without fabricating 100%. System2/3 are unconnected and show no invented samples. See [weekly-qa-contract.md](docs/weekly-qa-contract.md).
- System1 created five production checks for the current week (`QA-2026-W37`); a repeat returned ALREADY_CREATED. At this checkpoint: 87 sources, 31 pending (previous 26 + five checks), 70 originals and 38 effective included sources. All 44 history records and four unresolved colleague issues remained. No production sampling conclusions were submitted in this round.
- Validation: System1 regression 71/71, Workbench Python 15/15 and frontend 8/8 passed; Environment Doctor PASS. Coverage included year-crossing weeks, duplicate generation, unfinished-sample exclusion, small and zero samples, blank incomplete accuracy, overlapping full-score curves and identity constraints. Production-page checks covered English menus, three operators, 44 named history records, five sampling entries and original links; browser errors were empty.
- Production-data verification is in [final-data-verification.json](runtime/english_ui_20260907/final-data-verification.json). Fingerprints before/after identity migration and after sampling were retained separately. Earlier statements that the workbook fingerprint was unchanged apply only to their historical rounds.

Additional checks found and fixed Random QA corrective tasks being cleared by later task consolidation. QA failures now carry persistent `human_reported_issue`, retaining the original note, operator and QA evidence ID. They remain unresolved after another Routine Cycle and require explicit verification. Isolated bridge tests cover CORRECT replay, INCORRECT history retention, repeated cycles and explicit verification closure.

## System2 review demo and queue alignment | 2026-09-07

- The user requested continued workbench presentation work. Other tasks retain System2 parsing and production interfaces. This round did not modify System2 code, Canonical or inputs.
- Five practice scenarios are available: historical CS005 PDF text, sentence/footnote boundaries, omitted tables, and clearly labeled synthetic HTML lists and Excel header mappings. Source-page images and fingerprints were checked, including pages 20/21. The current contract is [system2-review-demo.md](docs/system2-review-demo.md).
- Following user feedback, System2 reuses System1’s vertical Queue, search and selection styling. Pending contains only unreviewed or follow-up items; reviewed items appear only in history, with originals, before/after values and reopening available. System1 queue items add format/publisher while retaining the ID, title and pending-reason hierarchy.
- Named practice decisions, corrections and notes persist in separate browser demo storage. Checks covered automatic advance after correction, required list/column mapping, whole-table omissions remaining in follow-up, and reopening with history and corrections retained. Demo activity is excluded from production history and accuracy.
- The full PDF reader and correction form appear together. Screenshots support region, full-page and zoom views. File buttons are English. Selecting a local PDF checks its header and fingerprint; a match displays only in the browser. A wrong-version notice preserves the previous state.
- Reviewers appear alphabetically by first name: Ana Jokic, Daniel Restad, Weijie Tang. English buttons do not change the operating system’s native file-dialog language.
- Explicit links in the original PA057 and CS004 notes had already been imported into `retrieval_url`. This round checked them read-only and added clickable history links, a registered-but-awaiting-original-verification status and a continued-review entry. It downloaded no new links and replaced no snapshots.
- Isolated browser checks found services on different ports sharing a cookie name, causing operator state to alternate. Cookies are now isolated by port with legacy-session compatibility. The service prefers its previous local port to retain browser storage, falling back to an available port if occupied.
- Validation: Workbench Python 17/17 and JavaScript 14/14 passed. Isolated browser checks covered PDF 20/89, wrong and matching local originals, draft restoration, missing/list/column-mapping flows and history. At 360px there was no page-level horizontal overflow, and switching comparison views retained drafts. Business acceptance still requires operator trial feedback; these checks do not establish production integration.
- Production business projections matched the pre-test read-only snapshot field by field: 87 sources, 31 pending, 70 originals, 38 included and 44 named history records. The production request list was empty. The workbook file fingerprint changed during the round, but sources/tasks/history projections did not; binary fingerprint equality was not used as passing evidence. See [final-business-check.json](runtime/system2_demo_20260907/final-business-check.json).
