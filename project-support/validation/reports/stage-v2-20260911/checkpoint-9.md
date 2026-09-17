# Checkpoint 9: persisted classification-score binding

Decision: **CONTINUE handoff validation; restricted candidate, overall incomplete.** This checkpoint fixes a safety defect reproduced in an isolated scored fixture. It does not establish a real calibrated score or improve the frozen source-quality measurements.

## Hypothesis and observed failure

Initial rule activation already checked method, original, proposal, source and calibration scope. Subsequent workflow recomputation could nevertheless reuse its persisted score parts after a classifier method change. The [before-fix counterexample](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/score-binding-before.txt) incorrectly returned `machine_accepted`. Normal frozen examples have no qualified scores; no actual business release through this defect was observed.

The required boundary is that a score can validate only its exact current proposal. An existing named human judgment must survive a method change, while its obsolete machine score must no longer be represented as applicable confidence.

## Change and durable evidence

`requirement-score-binding/1` binds scores to the classification method, immutable original digest and exact proposal digest. Validated local-rule activation writes that binding. Recalculation and the browser confidence projection derive an unmeasured view for missing/stale bindings, without overwriting recorded score parts. Existing source-version eligibility checks continue to apply separately. No threshold or production calibration configuration changed.

Reconciliation refreshes accepted results when the method/binding version changes. It suspends unsupported machine delivery, preserves named human classification and history, emits one method-change event and is idempotent on an unchanged repeat.

The [durable runtime fixture](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/score-binding-runtime-v1/result.json) uses separate owning SQLite stores, real enqueue/install/decision APIs, store reopening, ordinary reconciliation, feed readback and the browser projection:

| Synthetic engineering case | Before | After current method loads | Preserved |
| --- | --- | --- | --- |
| Machine decision with old bound scores | One delivery, confidence 0.96 | Zero delivery; Pending; confidence unknown in all three B dimensions | Original facts, raw old scores and history |
| Named human decision with old bound scores | One delivery, confidence 0.96 | One human delivery; confidence unknown in all three B dimensions | Original facts, human decisions, raw old scores and history |

Each repeated reconciliation adds zero events. These synthetic scores demonstrate state behavior only; they are not independent labels, real calibration, automatic-quality observations or normal-instance loading evidence.

## Candidate and preservation

Candidate `requirement-stage-v2-candidate-05` contains 382 program/test/declaration files. [Manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v5/manifest.json): archive SHA-256 `a56fcfb38a53dd60a13fc2387404da29465c4545c2f5f56163e2fa908c8de456`. [Recovery readback](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v5/recovery-verification.json) verifies ZIP integrity and all restored/current hashes. Prior frozen archives remain unchanged.

System2: **880 passed, one existing fixture skip**, 17.186 seconds; [JUnit record](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/full-system2-score-binding-final.xml). Five new checks cover stale/missing binding, machine withdrawal, human preservation and validated-rule binding. Existing synthetic score fixtures explicitly bind their evidence to their proposal. No quality reference was changed. Frontend 25 and workbench Python 30 previous passes remain applicable because their code is unchanged in this checkpoint.

All 91 frozen sample files remain unchanged. The [new normal-preservation audit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity-score-binding-v1/normal-preservation.json) finds the five business stores and managed/Gold files unchanged; browser-session rows are the only difference. No business restore or normal decision was performed.

## Remaining limits and next checkpoint

Classifier 4 quality remains TP/FP/FN 41/0/0 with 51/60 decisive; A quality, natural verifier failures and zero safe automatic releases are unchanged. Normal startup, native Office visual acceptance and final Canva commit retain their pending input boundaries. The one authorized reset remains unused. No API, formal schedule or source expansion was enabled.

Next, finish current-candidate handoff consistency and select only a new, bounded source-quality hypothesis supported by the frozen errors. Do not repeat stopped raster or column/caption-only inference routes. The original clock and final three-hour reporting reserve remain in force.
