# Stage v2 checkpoint 8: applicability proposals and actual evidence display

2026-09-11. Decision: **CONTINUE with candidate 04; keep unresolved quality and release gates explicit.** Overall goal incomplete.

## B failure, intervention and boundary

Two unchanged source judgments were missed by the modal-word-only rule: B024 states a conditional exemption from Criterion 2.1 and B034 states that the requirements apply regardless of site depth. These are retained scope rules, not invented additional actions or duplicate obligations.

`literal-requirements/4` adds bounded English applicability/exemption signals. It retains the complete clause, exact matching span and original source references. Questions, hypothetical/example framing, reported/proposed rules and quoted text remain conservative rather than being forced into a positive or negative class. Signals never establish a concrete farm's applicability. Scores remain unknown and all existing A/B confidence, dependency and human gates are unchanged.

The [initial discriminator](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-applicability-discriminator-v1/result.json) separately records eight positive and twelve counterexample controls. Production boundary checks additionally cover multiline framing, earlier unrelated relative clauses, source offsets and table-assembly context. The first integrated attempt over-abstained because `which` in an earlier rationale sentence suppressed a later scope statement; the sentence/context distinction was corrected and measured again. Both attempt outputs remain retained.

## Matched frozen result

[Final method-4 measurement](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-diagnostic/candidate-method4-final.json) uses the unchanged initial 60 and separate one-unit supplement:

| Measure | Method 3 | Method 4 |
| --- | --- | --- |
| True positives / false positives / false negatives | 39 / 0 / 2 | 41 / 0 / 0 |
| Precision | 39/39 | 41/41 |
| Recall including abstained positives | 39/41 | 41/41 |
| Advisory recall | 11/11 | 11/11 |
| Decisive initial judgments | 49/60 | 51/60 |
| Decisive including separate supplement | 50/61 | 52/61 |

Only B024 and B034 change class. The nine remaining initial abstentions are retained negatives in the reference, not quietly counted as correctly rejected. Decisiveness **85%** remains below the adopted 90% target. This is exposed Agent-checked development evidence on source-complete controlled inputs, not independent accuracy or normal accepted-A delivery. A, B and end-to-end safe releases remain zero.

## Actual shared workbench verification

The [runtime receipt](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-applicability-runtime-v1/result.json) reads both real Canonical units through the isolated workbench on port 59739. Both return method 4 and an uncalibrated requirement proposal while A remains unresolved. Actual browser navigation opened the page-19 exemption text and the suggestion panel.

That check found a UI integration defect: the new proposal appeared beside `Matched original wording: No decisive wording`, because the UI displayed only modal matches. It now includes the located applicability evidence. The final browser view shows `are exempt from standards`, unknown confidence, the original page and two pending A prerequisites. No decision or draft was submitted. Saved and exported events remain **13/13**. A transient stale source-check indication returned to synchronized without restarting the service; it was not represented as durable export success while stale.

## Candidate, integrity and tests

Candidate `requirement-stage-v2-candidate-04` contains **380** program/test/declaration files. [Manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v4/manifest.json): archive SHA-256 `ac49e7d2f77c0044a26ef2ffb8c86b366207d6d3f80ec5edfd0867f81d57bc4d`.

[Recovery verification](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v4/recovery-verification.json) passes CRC, exact entry inventory and all restored/current hashes. Prior candidate 01/02/03 archives and all 91 frozen sample files remain unchanged. The [current preservation audit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity-applicability-v1/normal-preservation.json) finds no differences in the five business stores, managed originals or Gold; workbench browser-session rows are the only table change. This is per-store consistent readback, not a stopped-write restore.

Final System2 suite: **875 passed, one existing fixture skip**, no failures. Frontend: **25 passed**. Workbench Python's 30 previously passed checks remain applicable; no parent Python code changed here. Parser, verifier, renderer 21 and preview 7 are unchanged. Natural verifier measurements and full-load performance retain their explicit earlier versions and scope.

## Canva and remaining work

The earlier unsaved Canva transaction returned `INVALID_ARGUMENT` for both editing and reading. The saved design was verified as the same 25-page version 1. A new transaction restored pages 2/3/9 and updated page 10 with version 4, labeled method-3 baseline and current counts. All four affected native renders were visually rechecked; the other 21 retain their inspected saved version. Page-10 speaker notes retain the labeled method-3 baseline, while the visible page shows both versions. The new draft awaits the explicit save approval requested after previews; no commit is claimed.

The [Canva recovery receipt](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/presentation/canva-recovery-final-receipt.json) retains the transaction and replay operations. Vertical text resizing was rejected; supported width changes succeeded and affected pages were rechecked. No additional design or screenshot-only presentation was created.

Remaining hard findings are unchanged source/relationship/verifier/automation failures, normal-entry loading, native Office visual acceptance and the final Canva commit. Existing protected-start and Mac-unlock requests remain pending. No external model, formal scheduler, source-discovery expansion, business acceptance, Git commit/push or reset was performed. The last usage read is 42% used; the single authorized reset remains unused.

Next: verify the full handoff and runtime evidence against this frozen candidate, and complete outstanding external/UI steps only when their existing inputs arrive. Do not restart the stopped raster or column/caption inference routes without materially new evidence. The original execution clock remains active.
