# Actionable source failures

Date: 2026-09-10. Decision: **CONTINUE** under the [current-stage functional contract](../../../docs/design/requirement-workstream-stage-delivery.md). This closes a missing human entry for failed originals; it does not complete those originals or establish extraction accuracy.

## Observed problem and implemented route

The seven enrolled Lovdata HTML snapshots PA011, PA012, PA039, PA041, PA042, PA044 and PA058 have an empty `documentBody`. Their local metadata and contents navigation are present. The parser correctly refuses to treat them as full text, but the previous zero-unit screen lacked an actionable content task.

Each now has a separate source-follow-up entry, with its failure reason, unknown content confidence, snapshot identity and a sanitized preview of the saved original. The HTML probe reports the empty registered body and displays the original complete-document link as literal text. It executes no scripts and follows no links. Failed attempts remain in append-only history across retry; installing usable content clears only recovered processing errors, retaining substantive source/content holds. No fake extraction item or Requirement is created.

The shared browser submits a guarded note to System1's existing source-issue route. Drafts remain local until submitted; blank notes fail explicitly. A saved report remains Pending until the original problem is addressed. System1 offers the normal original-view, corrected-link, authorized-original upload, keep-pending and explicit verification controls. Existing snapshots remain valid historical originals. Retrieval or upload was not performed in this checkpoint.

## Actual isolated exercise

The owning governance-database pilot at port 51069 displayed PA011's original metadata and `documentBody: 0 text characters`. A named development exercise saved the follow-up, showed a saved-but-unresolved receipt and retained the task in System1 Pending. The second guarded request was `44fe0f57-fc13-4550-a8c2-9cd0a26c48f5`; the single current operation was `SYS2-89f1a192-d933-4452-b1ba-d91a4a5d81ba`. Both reports are retained. The first intended blank-input check did not clear the browser field; DOM readback established that it submitted a nonempty prefilled note. A subsequent whitespace-input check was rejected before submission. Neither event is represented as an independent human reference judgment.

The original 87 source identities, all 70 stored version rows, all 126 prior operation rows and all 229 prior history rows were preserved. Only PA011's revision and human-action flag changed; one operation and three history rows were added. PA011 remains failed in A with zero published Requirements. Its original hash, snapshot and INCLUDE selection are unchanged.

System1 reached saved and synchronized revision 14. The frozen Excel has one current follow-up operation, retains the full note and passed OfficeCLI validation. SHA256: `35d82f7505181182b11de54b1d30c4f3bd7890b4a250bf792d8baf8f98cfac54`. Native visual inspection of this copy was not performed. The valid-note input-to-observed-receipt window was 52 seconds, including developer tool orchestration, with two direct actions (enter note, submit); it is not a human-time benchmark.

## Normal integration and checks

After draining requests and preserving five stopped-write database backups, both outputs, configuration, the migration companion and 73 original hashes, the normal service was reloaded on port 62742. All database table fingerprints and all original hashes matched. The actual normal browser displayed seven source follow-ups, PA011's bound original and the editable submission route. No normal business decision was submitted. The earlier missing pilot UI-file failure is already fixed and documented in System1's database rehearsal.

System2: 731 passed, one missing-fixture skip, one existing dependency warning. Workbench: 28 Python checks and 17 frontend checks passed. Five new failure-follow-up checks cover empty-unit routing, retry/replay/history, conservative recovery and inert HTML evidence. The tests exposed and corrected a duplicate `document_id` event payload before browser validation.

Local evidence: `workbench/runtime/source-followup-20260910/`, including pretest database copies, saved receipts, downstream Pending readback, source/history/Excel comparison, frozen workbook, OfficeCLI result and normal stopped-write recovery manifest. Regression logs are in the owning component's `runtime/source-followup-*` files.

## Remaining work

The seven complete originals remain business Pending. Existing current-source output is incomplete. Normal A/B sampling remains disabled and no provider or external action was enabled. Next verify the necessary scan/manual-transcription and cross-page repair alternatives and consolidate representative offline functional delivery. Broad accuracy, calibration and independent reference collection remain future improvements under the revised stage contract.
