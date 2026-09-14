# Product readiness: execution and evidence entry

Authority: [active goal extension](../../docs/design/human-led-workbench-goal.md#active-goal-extension-product-readiness-2026-09-12). Current integration judgment: [PROJECT_STATE.md](../../PROJECT_STATE.md). Goal task: `01a09761-a69b-7640-b7a2-8e399ac01cc3`. Started 2026-09-12; no fixed deadline or duration.

## Current priority, user revision 2026-09-13

Stop further extraction/recognition accuracy optimization. Machine assistance is optional input to human work; the active gates are accurate manual review support, original/version clarity, complete checked/unchecked scope, durable correction/history and safe exchange. The authority above owns this scope change, including deferral of the earlier quantitative quality thresholds. Preserve previous failed/unmeasured quality results; do not relabel them PASS or start new holdout/annotation campaigns.

The already-started source-row change is closed with 189 material-module checks passing and unchanged frozen sources/annotations ([checkpoint](quality/structure-diagnostic/source-line-fidelity/RESULTS.md)). No normal business extraction, confirmation or parent restart was performed. Future training should consume explicitly reviewed, provenance-bound annotations; unreviewed source and machine suggestions must remain distinguishable. Training/schema expansion is not current work.

The standalone reader recovery is verified in [its current checkpoint](ui/pdfjs-reader/recovery/RESULTS.md), with 164 Python / 184 frontend checks and actual page/zoom/retry evidence. Next: finish remaining actual-browser manual-review scenarios;  audit source-range coverage and version-bound decisions; then freeze the integrated candidate and exercise mixed edit/save/reopen, conflicts, package exchange and recovery. Existing PDF.js evidence is in [reader integration](ui/pdfjs-reader/RESULTS.md). The unreadable legacy `system2/ui/review.html` remains a distinct recovery gap with [retained evidence](quality/regression-parser6/file-read-diagnostic/locked-wheel-recovery-03/RESULTS.md); do not invent a replacement or repeatedly rerun its blocked read.

## Preserved evidence and runtime

- [Pre-change manifest](baseline/manifest.json): 337 code files and 411 documentation/test/script files copied and hash checked. Git contains substantial pre-existing untracked work; it is not a complete recovery point. This is a code/document checkpoint, not a new cross-store business snapshot.
- Existing full recovery package `../../workbench/runtime/workflow-correction-final-backup/` verified by the current recovery tool: 8,389 resources and 6 stores. This verifies the historical package, not equality with current live stores. No live business-data mutation is planned; obtain a fresh quiescent recovery package before any such migration or activation.
- Fresh engineering fixture `../../workbench/runtime/product-readiness-20260912/fixture/`, built from the existing fixture helper under a new target. It has independent Data, governance, runtime and config, with copied public originals and synthetic HTML/XLSX/native-scan-blank PDF. Only its explicitly requested material worker runs; coordinator schedules are disabled. `server.json` under that folder owns its current temporary URL.
- Frozen 11-input development baseline and 2 source-annotated reserved PDF windows are indexed in `quality/`. Real-document coverage and historical exposure limits are explicit; synthetic mechanisms do not stand in for real documents. No whole-goal quantitative PASS.

## Historical baseline findings

These are retained baseline observations, not the current work queue. Accuracy experiments and classifier adaptation listed here are deferred by the scope revision above.

| Priority | Observed issue | Original evidence / proposed experiment |
| --- | --- | --- |
| High | Reopened running extraction does not resume UI polling; editing or transient failure can stop polling | Actual frontend module probe; implement identity-safe metadata polling without replacing dirty text, then browser reload/restart check |
| High | Stale-tab comparison lacks explicit deleted-block/order choices | Actual module probe resurrects absent server block into proposed draft; add complete presence/order comparison |
| High | Scan/empty PDF pages can count as covered despite no usable text | Parser/store path inspection; freeze scan/blank controls before changing result semantics |
| High | PDF candidate route emits native lines in vertical/horizontal order with no heading/numbering structure | Freeze native multicolumn and real ASC windows; distinguish order/boundary defects from text recall |
| Medium | Requirement classifier exists only in legacy path; current material blocks do not match its clause/context inputs | Freeze complete positive/negative units before measuring or proposing an explicit adapter |
| Medium | Existing Requirement files named holdout have already entered active debugging | Preserve historical exposure records and select new withheld documents where evidence supports independence |

Frequency has not been measured; priority reflects direct task impact, not invented incident counts.

## Next checkpoints

1. Verify original reading and manual correction through a complete material path, including source ranges with no machine result.
2. Complete remaining actual-browser review-state, reopen/restart, stale/conflict and exchange/receipt scenarios.
3. Validate provenance and separation of drafts, explicit human decisions, machine suggestions and unresolved content; retain these for future annotation use.
4. Finish applicable UI accessibility and component regression, freeze candidate fingerprints, then run predefined isolated mixed-operation recovery checks and hand off.

All business-writing experiments remain isolated. Do not infer Windows or colleague usability acceptance from engineering results. Pending goals remain active rather than marked complete at a checkpoint.

The owned coordinator/reviewer services were restarted again after successful return adoption and manual PDF transcription, using nine integrity-checked isolated store snapshots in `workflow/restart-after-return/manifest.json`. Origins remain 55542/58814. No normal business service restart occurred.

## Historical checkpoints and retained evidence

The candidate remains recoverable and the goal ACTIVE. Source/structure quality fails; full ten-scenario browser acceptance and all-state accessibility remain incomplete. Actual TS002 browser verification now covers independent candidate-order adoption while retaining manual table content, readable parent selection, invalid heading-order rejection with the arrangement retained, and saved comparison choices restored after service restart and return/reopen. See `workflow/ui-checks.md`. New comparisons use version 2 only where all three block-ID sets match; historical version-1 choices retain their meaning. Current Workbench Python regression is 149/149 with stable code/UI bindings (`workflow/workbench-python-04/result.json`); no new frozen mixed-workload PASS follows.

Historical comparison checkpoint: TS002 retained its saved order choice, and the pre-comparison backup contains seven integrity-checked stores in `workflow/pre-merge-v2/manifest.json`. Current runtime and returned-conflict evidence are recorded below.

Recovery of the latest validated code checkpoint: `baseline/frozen-candidate-03-code/manifest.json` verifies 320 exact files against the run's extended product manifest, with zero missing files. This preserves code/config independently of subsequent label improvements; existing environment declarations and isolated database recovery points remain separate. The temporary visual-baseline service has been stopped after final screenshot comparisons; its copied data and all screenshots remain.

Latest bounded native-backend experiment: the installed Docling route failed again on its Helvetica AFM resource after a successful isolated import-readiness probe; this route is stopped and its earlier successes/failures remain in `quality/structure-diagnostic/native-assembly-comparison/`. No dependency or backend was switched. A separate PDFium development-page probe retained all 1,269 native characters, supplied 173 words rather than 30 line-level entries, and reproduced the existing line text/bboxes. The downstream structure comparison did not establish a measurable quality gain and was not integrated; richer metadata alone is not extraction-quality improvement. Evidence belongs to `quality/structure-diagnostic/pdfium-granularity/`.

Current additional HTML fix: actual archived PA001 review exposed duplicated/partial section labels. Parser /5 now preserves full section suffixes; its exposed DOM-label diagnostic is 42/42 versus 0/42 before, with all other 412 block fields exact. This is separate from PDF quality and awaits wider integration binding (`quality/html-numbering/RESULTS.md`). The UI numbering helper changed after frontend-04; its targeted checks and subsequent full frontend run passed; the latest reader-specific binding is in the reader evidence above. The archived engineering spot-check records this finding against revision 2; it does not confirm the complete source or rewrite the archive. Recursive Requirement group/time modelling is now an active discussion proposal in System3 DESIGN, not a schema change.

Current runtime and workflow checkpoint: [returned text-conflict evidence](workflow/return-conflict/RESULTS.md) records explicit master-4 adoption, actual receipt import, preserved reviewer work, durable download recovery and exact future receipt summaries. Coordinator 55542 (session 29169), reviewer 58814 (session 69115) and fault 60905 (now session 20726) retain their separate fixtures; the report owns their exact backend differences. Normal 62742 was not restarted. The preceding Workbench regression: 160 Python and 178 frontend checks passed; the prior import-graph assertion failure remains recorded.

Current reader experiment: [local PDF.js integration](ui/pdfjs-reader/RESULTS.md) replaces the plugin-dependent reading path on capable parents. It is loaded only in isolated 60905, session 20726, with actual continuous reading, search, current-page full-reader opening, image fallback and native/scan/blank status checks. Current bound regression is 164 Python / 180 frontend checks. Clipboard round trip and broad complex-PDF fidelity remain unmeasured. Normal 62742 and the other isolated parents were not upgraded for PDF.js. The original HTML reflow and absent assets remain open.

These reader/workflow checkpoints remain evidence only. Current next steps are defined at the top of this file; automatic-quality work is deferred. No new global candidate freeze or whole-goal PASS is claimed. Windows/colleague acceptance remains pending.
