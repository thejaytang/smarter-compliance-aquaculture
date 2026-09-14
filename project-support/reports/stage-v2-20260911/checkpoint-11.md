# Checkpoint 11: located context proposals and preserved A/B boundary

Decision: **CONTINUE with the narrow rules retained; overall goal incomplete.** Candidate 07 recognizes complete bibliographic citations and questions-only support contacts. It does not turn all passages without normative keywords into negatives.

## Hypothesis and bounded change

Two of the nine remaining abstentions in the frozen complete-original B diagnostic have explicit document genres: a complete author/year/journal/volume/page/URL citation, and an invitation to contact support with questions. The new `context_signals.py` returns the full matched original, category and exact offsets. Normative wording, applicability evidence and other operative context retain priority. Incomplete citations, damaged URLs, extra actions and mixed instructions remain outside the rule. Confidence stays unknown, and no acceptance threshold changes.

Classifier `literal-requirements/5` changes exactly B030 and B039 from undetermined to context. [Same-sample results](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-diagnostic/candidate-method5-final.json): TP 41, FP 0, FN 0; advisory recall 11/11; initial decisive judgments **53/60, 88.33%, FAIL** against 90%. The separately frozen negative supplement remains correct, giving combined 54/61. All seven remaining initial abstentions are negatives. This is exposed Agent-checked development diagnosis, not independent acceptance.

The [previous classifier-4 metrics](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-context-discriminator-v1/prior-metrics-classifier4.json) remain unchanged. Current metric statuses remain 21 PASS, 11 FAIL and six UNMEASURED. Parser-04, verifier-6 and prior performance evidence retain their explicit scopes; A/B/end-to-end safe automatic release remains zero.

## Actual runtime and material boundary

The [current isolated runtime](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-context-runtime-v1/result.json) reads the actual parser-04 Canonical with 109 units. The complete support-contact unit on physical page 116 proposes context. The real shared UI displays this proposal, matched original wording and classifier version 5, alongside unknown confidence and two pending A checks. [UI inspection record](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/b-context-runtime-v1/ui-readback.json). No decision or draft was submitted.

The bibliography on physical page 20 remains **undetermined** in this actual unaccepted A result: the URL contains the inserted line-wrap space `mari ne`. The original complete-text B diagnostic has the intact URL and is a different input. The initial runtime assertion expecting both proposals to be context exposed this distinction; the implementation was not relaxed to hide A damage, and the reference was not changed. Correct end-to-end behavior still requires A repair/review. Saved/exported events remain 1/1, history zero and published Requirements zero. The already verified parser-04 Excel snapshot remains applicable; no new acceptance or Excel quality claim is added.

## Tests, version and preservation

Eighteen added cases cover four complete context genres, four normative-priority controls, nine abstention controls including the observed damaged URL, and operative shared-context priority. Final full System2 suite: **907 passed, one existing fixture skip**, 18.21 seconds. [JUnit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/full-system2-context-final.xml). Frontend: 25 passed after the matched-context display change. Workbench Python: prior 30 checks retain unchanged-code applicability. These are engineering checks, not source-quality qualification.

Candidate `requirement-stage-v2-candidate-07` contains 386 program/test/declaration files. Archive SHA-256: `5a52b7a9a7b0bd74f51896f97f57ab8aeb9fd94d045478110cb9e7f3948f2a23`. The [manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v7/manifest.json) binds code, configuration, reference and output hashes. All 91 frozen sample files match; candidates 01–06 are preserved. [Recovery verification](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v7/recovery-verification.json) checks actual temporary extraction and current/restored hashes without replacing business state.

The [read-only preservation audit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity-context-v1/normal-preservation.json) confirms five business stores, managed originals and Gold are unchanged; only browser session rows differ. No protected normal start, source expansion, business acceptance, external model, scheduler, reset or Git operation occurred.

## Presentation and next checkpoint

The same 25-page Canva design now has classifier-5 figures on draft pages 10 and 21. Both full native page renders were visually inspected at 1080px display width: no accidental overlap, clipping or wrong connectors. Earlier checks remain applicable to the other four draft pages and nineteen saved pages. [Current receipt](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/presentation/canva-context-final-receipt.json) links the replay chain. The six-page save approval remains pending; no saved final design is claimed.

Next checkpoint freezes reporting, checks version/evidence consistency and completes the prepared normal-start, native Office and Canva actions if their pending inputs arrive. Preserve the original deadline and final-three-hour reserve. Do not pursue a third easy negative solely to cross 90%, restart the stopped cross-page/raster routes, or equate regression success with quality acceptance.

## Final bounded source-annotation probe

A [read-only probe of all eight pages](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/annotation-url-discriminator-v1/result.json) finds three URI annotation groups and exactly one cross-line candidate on physical page 20. Its two original word fragments, selected by the original annotation rectangles, concatenate exactly to the embedded URI. This supplies a concrete independent metadata constraint for a later assembly repair. The probe does not change candidate 07 or quality metrics. Before integration, discriminate conflicting targets, visible labels, partial rectangles, encoded spaces, OCR and coordinate transforms; a hyperlink destination alone must not overwrite visible original wording. The frozen parser still retains this error.
