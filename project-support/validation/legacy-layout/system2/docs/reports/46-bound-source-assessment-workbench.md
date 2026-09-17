# Checkpoint 46: bound source assessment in the shared workbench

Decision: **STOP after this checkpoint at the user's explicit request to pause**. The PDF quality goal remains incomplete. Do not start a subsequent experiment until the user explicitly resumes work. This is a requested pause, not a quality pass or a declaration that all engineering is blocked.

## Implemented behavior

A saved source-reference candidate can now start an assessment in the existing workbench. System2 freezes the exact reference revision, effective records and current original-page verification report from owning records and the retained verification evidence artifact. Browser requests cannot supply replacement reference answers, output records, reports, evidence class or operator identity. Current source eligibility/bytes, evidence hashes and request/revision guards are checked before writes.

The first stage inventories original/output errors while the assessment interface withholds machine findings. Every reference region and output record must be reviewed, with content, structure and relationship scope explicitly checked. Errors may reference original regions without any output record or machine finding, so completely omitted content can enter the denominator. An incomplete inventory cannot advance.

Freezing the inventory reveals the already frozen verifier report. Each finding then needs a supported decision: matched error, duplicate, false positive or unresolved, with a location judgment where applicable. Pending decisions cannot complete the assessment. The existing diagnostic evaluator counts unique errors, false alarms, duplicates and correct locations separately and explicitly retains critical misses and unverified scope. Empty categories remain unmeasured.

Changing an inventory after findings have been exposed requires an explicit reopening and reason. Exposure remains recorded and previous errors, decisions and reports remain in history. Changes to the reference, effective output or verifier report make an earlier assessment stale and prevent current confirmation. These checks do not delete historical assessments or treat a revised reference as the old answer.

References and assessments use their own database tables and history. They do not accept A/B content, create deliveries, rewrite Canonical/Gold or enqueue an Excel publication. All current study tasks remain unqualified development evidence. A local named submission receipt authenticates the recorded operation; it does not establish independent human truth, held-out qualification, calibration or release accuracy.

## Actual browser experiment

The experiment reused the already exposed, one-page synthetic scanned notice from checkpoint 38. Its original and old fixture were preserved. A new isolated System2 copy at `workbench/runtime/pdf-assessment-pilot` used the existing synthetic source's read-only System1 configuration. The shared Handler, UI and subprocess adapters were exercised with **Engineering validation** and an explicit engineering banner. Background workers and ordinary business submissions were disabled. The normal workbench service was not restarted.

A current page comparison on the unmodified copied result produced zero findings and seven unverified scope items. The new isolated effective-result copy then received one deliberate decimal substitution, `0.01 mg` to `0.10 mg`. A second real local comparison reported one critical-token difference at the correct body line and retained seven unverified scopes. The [seed record](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/seeded-error.json) and separate [before](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/page-check.json)/[seeded check](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/seeded-page-check.json) preserve this distinction. The evidence class is synthetic: the mutation is not a naturally occurring error in a real source.

Through the browser, the complete four-line synthetic reference was entered and confirmed. Inspection exposed undersized initial vertical boxes. A reasoned revision corrected the boxes without changing the transcription and retained both confirmed versions. An assessment bound to the first reference became visibly stale and read-only. This failure was preserved, not removed to improve a score.

A new assessment bound to reference revision 4 then:

1. Refused inventory completion before the original/output review was checked.
2. Recorded the deliberately changed decimal as a critical error, with source and output IDs.
3. Froze two original regions, six output records and the three review dimensions before revealing the finding.
4. Refused completion while the finding had no decision.
5. Saved the matched error and correct location with an explicit engineering explanation.

The saved case contains one recorded error, one matched finding, no recorded false alarm or duplicate, and seven unverified scope items. Its diagnostic ratios are 1/1 for this constructed case; independent metrics remain null. This is evidence of the workflow and known-control accounting, not measured PDF accuracy, real-scan reliability or population generalization. False-positive, duplicate and original-only-miss arithmetic have transaction/evaluator tests, not a representative actual-browser quality study.

The reference history has four successful events: create, confirm, revise, confirm. Two assessment records remain: one stale inventory and one saved diagnostic assessment. Failed submissions added no successful event. [The readback](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/assessment-readback.json) and retained reference/assessment histories bind these states.

## Validation, failures and limits

The full System2 suite passed **815 tests with one existing skip** and the existing Starlette/httpx deprecation warning. Twelve new assessment transaction controls cover original-only errors, duplicates, localization, incomplete scope, evidence tampering, exposure retention, source/reference/output/report changes, ownership and request replay. The Workbench suite passed **30 tests**, including rejection of browser-supplied study evidence and identity. The frontend suite passed **23 tests**; the new module also passed syntax checking and the actual browser flow above.

The initial reference boxes were corrected through retained history. A multi-select containing long error descriptions caused horizontal overflow after saving; bounded fieldsets and controls corrected this display issue. A saved critical-token error also exposed a display inconsistency: its editor retained the earlier Major selection while the persisted error correctly had Critical severity. The editor now reflects the saved severity and applies the critical-token rule visibly. The final page was reopened for saved-state and layout inspection. Diagnostic ratios are presented with case counts and explicit qualification limits; full bindings remain available in a details view.

The [isolated business comparison](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/business-preservation.json) shows nine ordinary business tables unchanged during reference/assessment operations. Intentional result seeding and page checks occurred before that baseline and are separately recorded. The [normal preservation check](../../outputs/runs/pdf-verifier-reliability-20260910/cp46/preservation.json) again matched 18 tables in two normal stores, 73 managed files and 51 Gold files. No normal source decision, threshold, scheduler or provider changed. Excel workers were disabled in this fixture; its visible pending/stale export state is not an Excel synchronization acceptance result.

No independent human reference was created. Real-human operation time, representative workload, real scanned-body quality, source-family separated calibration/held-out evidence and release thresholds remain unresolved. The paused goal's remaining scope is unchanged. Resume only on explicit user instruction, starting from the retained current implementation and evidence rather than repeating this control.
