# System2 functional workflow audit

Date: 2026-09-09. Scope: offline/local System2 functionality and the shared browser. PDF extraction accuracy is excluded. PDF job scheduling is tested with a controlled parser fixture, not treated as text-quality evidence.

## Outcome

The tested local/manual workflows pass after the fixes below. Current-source completion remains blocked for seven HTML snapshots without full text. No live provider is configured, and System3 remains an input consumer contract without semantic processing. This report supersedes earlier broad regression claims for the defects it identifies; passing the earlier tests did not cover these cross-step cases.

## Reproduced defects and fixes

| Area | Observed failure | Corrected behavior |
| --- | --- | --- |
| Coverage checklist | Its generated instruction could be classified and delivered as a Requirement | Coverage is context-only in both decision validation and export; the browser disables that classification |
| Split/merge | A superseded parent could be classified as a Requirement again | Superseded parents remain historical context and cannot be republished or reused for another boundary correction |
| Structure correction | A correction containing only source-position/role changes was rejected for having no text changes | Structure-only corrections are accepted with a location and evidence note, then require both gates again |
| Dependency invalidation | Indirect dependents could retain an old named acceptance after shared context changed | Dependency readiness follows the complete graph; changes invalidate all affected downstream classifications, including human acceptance |
| Coverage findings | `review_required` parser warnings could disappear from coverage blockers | Images without transcription, unresolved links and other substantive parser findings remain explicit blockers; confidence and bounded-window metadata keep their separate gates |
| Draft/history | Draft saves appeared as applied reviews | Drafts have their own audit event and receipt; new drafts do not enter decision history, and legacy draft rows are filtered from the review-history view |
| Draft save race | Manual Save draft did not await the automatic revision-hold receipt | The explicit save waits for the hold, then records the acknowledged revision in the local draft |
| Stale drafts | Saved drafts were silently rebound to newer result revisions | The draft is retained and requires an explicit comparison with the current result before submission |
| Unsaved changes | Confirming content/classification could ignore edited but unapplied text | The browser requires the correction/recheck action first; absent optional fields no longer count as edits merely because their controls contain empty strings |
| Error feedback | A failed submission's message was far above the long review form | Decision feedback appears beside the submit controls |
| Current pending count | Withdrawn/ineligible sources remained in the active pending total | Historical units remain available, while active totals count eligible sources only |
| Retry | Successful recovery could retain an obsolete parser error message | Retry and successful installation clear the current error while keeping earlier evidence/events |
| Input feed | Browser history stopped at the first 1,000 events | The feed supplies `has_more` and a current accepted list; the browser reads subsequent event pages |
| Large queues | Rendering thousands of queue buttons and unverified merge choices delayed browser interaction | Queues render 60 items per page with source-number/text search; merge options contain only eligible verified parent units |

No source files, Canonical facts, Gold or named production decisions were rewritten. No new dependency or provider was installed. These fixes are local; no commit or publication was performed.

## Verification matrix

| Function | Evidence | Result |
| --- | --- | --- |
| Explicit INCLUDE intake, identity and original hashes | Existing intake contracts, live isolated HTML/XLSX starts, eight additional HTTP checks | Pass; unregistered IDs, wrong hashes and client-supplied actors rejected |
| HTML source coverage | Read-only processing of all 37 current INCLUDE HTML snapshots | 30 produced reviewable units; 7 failed explicitly on empty body |
| XLSX pipeline and original view | Isolated GLOBALG.A.P. reference; browser original sheet/cell view | 2,596 pending units; formulas, saved caches and hidden-region disclosure visible |
| Two-stage gate and full local completion | Small frozen HTML fixture through actual parser and named test decisions | Complete only after both gates; exactly one fixture Requirement delivered |
| Real-source browser gate and partial delivery | PA001, 150 units; isolated test prerequisite checks and review of § 4 | One accepted item available while source remained partial |
| Structure correction and incremental suspension | Same browser item, structure-only correction | Content returned to pending, Requirement blocked, current input count became zero; add event 16 followed by suspend event 21 |
| Threshold changes | Calibrated synthetic 96% regression fixtures at 95/98%, plus isolated browser 95 → 98 → 95 | Machine re-evaluation, human retention, draft/report preservation and event deduplication pass |
| Drafts and concurrent review | Browser save/reload, stale-draft warning, unsaved-edit rejection; store concurrency and HTTP stale-result checks | Pass; no overwritten named decisions |
| Pause/resume/retry and worker exclusion | Controlled seven-page PDF lifecycle with windows [0,1,2], [2,3,4,5], [5,6], plus state and lock tests | Cursor retained, two overlap units evidence-only, paused work not run, no duplicate final processing |
| Crash/restart and transactions | Running checkpoint recovery, persisted receipts/feed cursor, interrupted write rollback | Pass |
| Split/merge/supplement/reopen and conversion | Existing guarded review/conversion tests plus new retired-parent and structure regressions | Pass for exercised local contracts; conversion completeness remains a human judgment |
| Optional assistance | Disabled path, timeout, invalid JSON, unsupported citation and exhausted request budget | Falls back locally; authorized mock proposals remain unaccepted; no live model-effect claim |
| Weekly QA | Persistent/empty/short samples, incorrect-result reopening and current-version checks | Existing regression passes; no production synthetic calibration or fabricated sample |
| System3 input | Current list, event pagination beyond 1,000, incomplete ranges and browser add/suspend readback | Pass; `consumer_connected` remains false |

Final suites: **System2 577 passed, 1 skipped**, **System1 83 passed**, **Workbench Python 19 passed**, **frontend 14 passed**. The skip is the absent user-provided `_PS3_副本.pdf` sample, outside this accuracy scope; it is not an accepted capability. One existing Starlette/httpx deprecation warning remains. The complete System2 suite must run from `system2/`, because existing schema/config tests resolve component-relative fixtures.

The 15 new adversarial regressions are in `tests/integration/test_workflow_audit.py`. Eight additional checks ran against the isolated HTTP service, including anonymous mutation rejection, replay identity, changed payload rejection, cross-reviewer staleness and current delivery readback. Browser checks used named test sessions in isolated storage. Final browser error logs were empty.

## Current input blockers and acceptance boundaries

The following INCLUDE HTML sources still have `HtmlProfileError:html_empty_body`: **PA011, PA012, PA039, PA041, PA042, PA044, PA058**. Their original snapshots need complete body content through System1 before a successful run. No upstream retrieval or source replacement was performed during this test. Other source warnings remain in review; 30 reviewable sources do not mean 30 fully accepted sources.

There is no current production INCLUDE XLSX; the reference XLSX is an isolated test source. Representative independent HTML/XLSX Requirement precision/recall and calibration acceptance are separate from the functional checks above. Actual provider behavior needs an explicitly configured service. System3 semantic execution/consumer acknowledgment is not implemented. This audit makes no PDF extraction-accuracy claim.

## Runtime evidence and isolation

Local receipts and outputs are retained under `system2/tmp/workflow-audit-20260909/`: `system2-final.txt`, `frontend-final.txt`, `real-nonpdf-results.json`, `http-results.json`, `final-readback.json`, isolated registry/sources and workbench storage. This directory is excluded from version control and is not the production source of truth.

Final readback: production System2 still had **zero jobs**, shared production policy remained revision 1 with all values at **95%**, and production registry SHA-256 was `7beb2c9d63afcf693f41b3440b3ed3bb3cb7dd350b149480957d4f2901b8d041`, matching the earlier preserved baseline. Isolated PA001/XLSX source bytes matched their registered hashes after testing. The isolated policy alone reached revision 3. Test decisions do not count as production human approvals.

The isolated browser tab was closed and its service exited cleanly through its normal stop endpoint. Test data and audit receipts remain on disk. During deliberate refresh/closure, the standard-library HTTP handler logged a disconnected-client socket error; the service continued to respond and committed state/readback remained intact. This is residual log noise, not a failed review or lost receipt. The production service remains running.
