# Stage v2 checkpoint 1: source-first baseline and bounded table repair

Date: 2026-09-11 Europe/Oslo. Decision: **ADJUST**. The complete goal remains **incomplete**. Source and reference bytes were retained. All results below are **development diagnostic / Agent checked**, not independent human or held-out acceptance. Production release thresholds are unchanged.

## Experiment and diagnosis

The eight frozen physical pages were rerun with the existing offline parser. The first current-code rerun reproduced the old errors, distinguishing current defects from stale stored results. Two coupled structural causes explained the major loss: the layout detector rejected genuine tables occupying more than 45% of a page; repeating-margin processing then cropped table evidence to text, losing outer rules. Blank native cells were also sent to OCR, which read borders as text. A further minimal image probe found pale grid boundaries missed by a fixed dark threshold and an unused row division inside a colored header.

The retained changes require explicit grid evidence for large tables, preserve table geometry during marginal annotation, skip OCR only for visually uniform blank interiors with no word evidence, recognize pale rules using local contrast, and compact only boundaries crossed by every real cell. No source text, reference label, release threshold or normal human decision was changed. Six discriminating controls and 35 related checks passed. A full cross-module regression is still required before the candidate freeze.

## Matched quantitative results

Evidence: `system2/outputs/runs/requirement-acceptance-20260911/stage-v2/diagnostics/baseline-adjudicated-v1/` and `candidate-adjudicated-v1/`. Candidate is `candidate-rerun-03`; both use the same frozen source reference, all eight pages and 275 source regions.

| Measure | Frozen baseline | Candidate rerun 03 | Stage result |
| --- | --- | --- | --- |
| Literal CER | 378 / 12,860 = 2.94% | 31 / 12,860 = 0.24% | PASS within this exposed source |
| Literal WER | 182 / 2,011 = 9.05% | 44 / 2,011 = 2.19% | Reported, no separate adopted WER limit |
| Critical occurrences retained correctly | 208 / 211 | 211 / 211 | PASS within sampled positions |
| Body-cell literal text exact | 63 / 125 | 116 / 125 = 92.8% | FAIL, target 98% |
| Body-cell row/column/span correct | 39 / 125 | 125 / 125 | PASS within selected body tables |
| Selected reading-order pairs | 10 / 20 | 20 / 20 | PASS |
| Bound footnote/title/cross-page relations | 0 / 12 | 0 / 12 | FAIL |
| Whole pages free of inventoried errors | 0 / 8 | 0 / 8 | FAIL |
| Complete logical tables | 0 / 3 | 0 / 3 | FAIL |
| Natural errors explicitly located | 33 / 104 = 31.7% | 2 / 36 = 5.6% | FAIL, target 90% |
| Observed critical natural errors located | 1 / 19 | 0 / 11 | FAIL |
| Actionable finding precision | 33 / 100 = 33.0% | 2 / 27 = 7.4% | FAIL, target 80% |
| Duplicate repair findings | 42 / 100 | 0 / 27 | Measured reduction; not overall workload acceptance |
| A / B / end-to-end safe automatic passes | 0 / 0 / 0 | 0 / 0 / 0 | FAIL; correctness has no sample |

The low candidate detector precision is expected from the measured error mix: table repair removed many detectable text artifacts, while the remaining semantic/structural relation errors are mostly silent. All 15 generic original-ink warnings remain visible but receive no true-error detection credit. Eight native-observation header tokenization artifacts and two underscore artifacts are false alarms, not extraction mistakes. Current findings total 27; a further 40 unverified-scope records are reported separately.

Literal text plus body-grid completeness is 261/275 regions, but this is **not full source fidelity**. Eight footer grids still merge the Date issued / Last reviewed label column, and two headings remain coalesced. When every source-bound inventoried structure/relation error is attributed to its affected regions, strict complete recovery is only **58/275**, versus **22/275** at baseline. This deliberately broad impact allocation includes entire related tables, and must not be replaced with the narrower 261/275 to claim the 99% gate. The full region/error mapping is retained.

## Separate B and verifier controls

The unchanged B classifier on source-complete diagnostic A inputs has initial TP 39, FP 1, FN 2 and 19 true negatives including abstentions. Precision 39/40 (97.5%), recall 39/41 (95.1%) and advisory recall 11/11 meet the stage target. Decisive judgments 40/60 (66.7%) fail the 90% target. One separately frozen negative supplement makes 61 total cases with 20 negatives; it does not change the initial cohort. This is a controlled classification test, not normal end-to-end release.

The 12 paired seeded challenges detect and locate 10/12 errors, with 0/12 clean controls producing findings. The missed cases are a wrong original footnote owner and reversed page reading-order keys. These remain FAIL, separate from the natural error denominator. The footnote control binds only a left-row cell; a future test refinement must retain this frozen version and disclose any broader owner evidence, not silently replace it.

## Attempt record and next checkpoint

| Attempt | Minimal evidence and result | Decision |
| --- | --- | --- |
| Current-code rerun 01 | Same eight pages; reproduced missing large tables, page-120 fallback and blank-cell artifacts | Diagnosed current parser defects; useful baseline |
| Rerun 02 | Large-grid retention, table geometry preservation, uniform-blank guard; restored four-column tables and removed all 28 blank-cell artifacts | Measured improvement; retain |
| Rerun 03 | Pale-rule recognition and unused-boundary compaction; body-grid correctness rose from 119/125 to 125/125 | Measured improvement; retain; do not expand PDF scope |

The previously paused verifier work and its failed attempts remain historical constraints. These new table experiments have independent image/grid evidence; no attempt counter was reset by a new session.

Next CP2: address at most a bounded verifier/classifier defect justified by frozen failure evidence, then verify current-version main paths and collect 20 read, 10 isolated save and three export/recovery observations. Complete the 16-scenario/runtime matrix, ten-parent provisional split diagnostic, preservation check and presentation content. The optional PDF-reference extension remains unavailable in the old normal service; the normal core entry is restored. No normal service restart, new schedule or external model call occurred.
