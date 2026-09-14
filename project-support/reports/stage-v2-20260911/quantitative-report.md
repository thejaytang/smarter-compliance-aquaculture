# Stage v2 quantitative quality and operational report

Latest evidence: [checkpoint 11](checkpoint-11.md). Complete citation and support-contact evidence raise B decisiveness to 53/60, still below target. Parser-04 cell text remains 123/125, with no previously correct region regressed. Unsupported relation/raster prototypes remain excluded. [Stage applicability](stage-applicability.md) separates measured stage failures from future/optional qualification.

**Restricted candidate; overall goal incomplete.** Quantitative evidence below is development diagnosis checked by the Agent against original material. It is not independent human acceptance or held-out accuracy. The normal service is now available after the user-approved [checkpoint 15](checkpoint-15.md), with 16/16 scoped functional scenarios passing. Business Pending is preserved; quality measurements below are unchanged.

## Latest candidate-08 performance retest

[Checkpoint 13](checkpoint-13.md) repeats the complete 38-document workload under the frozen candidate-08 program: 20 list reads p95 0.3101 s; 20 cached evidence reads p95 0.7630 s; ten persistent saves p95 0.6578 s; ordinary exports 13.3785 / 13.8043 s and unlock recovery 15.4200 s. All six budgets pass. Exact replay, stale/conflicting guards, original/history preservation and event-81 Excel readback also pass. These are engineering timings, not reviewer effort.

The Q29–Q34 rows in the frozen 38-metric table below retain their earlier snapshot values. The [current-program performance supplement](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/performance-current08/metrics.json) supplies the latest version-bound observations without rewriting candidate 08's frozen report hash. Quality and safe-automation metrics are unchanged.

## Version, scope and reference qualification

Machine candidate: `candidate-rerun-04`; verifier `original-page-comparison/6`; classifier `literal-requirements/5`; current Excel renderer `21` and preview `original-preview/7` (original full-load performance used renderer `20` and preview `original-preview/6`). The parser candidate is separate from retained normal outputs and later manual-correction fixtures. All eight frozen physical PDF pages (19, 20, 116–120, 128), 275 source regions, 12,860 characters, 125 body cells and 61 B judgments were retained. All selected PDF pages were surveyed from the original, including regions without machine outputs. References were frozen before tuning and remain exposed development material.

Initial B cohort: 60 complete units, 41 positives (11 advisory) and 19 negatives; one negative HTML heading was frozen separately before tuning. Method 3 baseline: TP 39, FP 0, FN 2. Current method 5: TP 41, FP 0, FN 0; all seven abstentions in the initial cohort are negatives. Combined decisive count is 54/61, including the separate negative supplement. No unreviewed source was classified on the user’s behalf.

The [checkpoint 5](checkpoint-5.md) original-number correction adds actual Canonical binding for 55 spans and ten parents. All ten B submissions remain blocked by unaccepted A. Q18 therefore remains UNMEASURED; CP5 did not change raw parser/verifier/classifier metrics; the later classifier-only improvement is reported above.

## Results

| ID | Metric | Observation | Stage target | Result |
| --- | --- | --- | --- | --- |
| Q01 | All document states explained | 38/38 (100.00%) | 100% | PASS |
| Q02 | Readable supported materials parsed | 31/31 (100.00%) | >=95% | PASS |
| Q03 | Complete original regions including structure/relations | 64/275 (23.27%) | >=99% | FAIL |
| Q04 | CER | 17/12860 (0.13%) | <=1% | PASS |
| Q05 | WER | 18/2011 (0.90%) | report | PASS |
| Q06 | Critical token occurrences exact | 211/211 (100.00%) | 100% | PASS |
| Q07 | Body table cell text exact | 123/125 (98.40%) | >=98% | PASS |
| Q08 | Body table row/column/merge positions | 125/125 (100.00%) | >=98% | PASS |
| Q09 | Reading-order pairs | 20/20 (100.00%) | 100% | PASS |
| Q10 | Explicit title/footnote/continuation relations | 0/12 (0.00%) | 100% | FAIL |
| Q11 | Whole pages without substantive fidelity errors | 0/8 (0.00%) | report | FAIL |
| Q12 | Complete logical tables | 0/3 (0.00%) | report | FAIL |
| Q13 | B precision | 41/41 (100.00%) | >=95% | PASS |
| Q14 | B recall, including abstained positives | 41/41 (100.00%) | >=90% | PASS |
| Q15 | B advisory recall | 11/11 (100.00%) | >=90% | PASS |
| Q16 | B decisive judgments, initial cohort | 53/60 (88.33%) | >=90% | FAIL |
| Q17 | Provisional split exact spans and source bindings | 55/55 (100.00%) | all bindings; >=90% splits | PASS |
| Q18 | Production Canonical binding of subdivision diagnostic | Unmeasured | all | UNMEASURED |
| Q19 | Natural verifier error recall | 8/29 (27.59%) | >=90% | FAIL |
| Q20 | Natural critical errors found and located | 7/11 (63.64%) | all | FAIL |
| Q21 | Effective actionable finding precision | 8/33 (24.24%) | >=80% | FAIL |
| Q22 | Seeded errors detected and located | 12/12 (100.00%) | 12/12 | PASS |
| Q23 | Paired unmodified controls with false alarms | 0/12 (0.00%) | <=1 control | PASS |
| Q24 | A safe automatic release | 0/8 (0.00%) | >=10% | FAIL |
| Q25 | B safe automatic release | 0/61 (0.00%) | >=10% | FAIL |
| Q26 | end-to-end safe automatic release | 0/1 (0.00%) | >=10% | FAIL |
| Q27 | Matched duplicate finding instances removed | 42/42 (100.00%) | >=20% reduction | PASS |
| Q28 | Independent reviewer tasks, outcome and time | Unmeasured | measured | UNMEASURED |
| Q29 | list_read p95 | 0.304 s; n=20 | <=1s | PASS |
| Q30 | cached_evidence_read p95 | 0.728 s; n=20 | <=2s | PASS |
| Q31 | persistent_correction_save p95 | 0.632 s; n=10 | <=2s | PASS |
| Q32 | ordinary Excel convergence | 13.885 s; n=1 | <=60s | PASS |
| Q33 | ordinary Excel convergence | 13.489 s; n=1 | <=60s | PASS |
| Q34 | unlock_recovery Excel convergence | 15.555 s; n=1 | <=60s | PASS |
| Q35 | Independent held-out source acceptance | Unmeasured | qualified independent labels | UNMEASURED |
| Q36 | Real scan, mixed PDF and photograph quality | Unmeasured | representative real source evidence | UNMEASURED |
| Q37 | Live external enhancement comparison | Unmeasured | same frozen samples: quality, time, cost, burden | UNMEASURED |
| Q38 | Native Excel visual acceptance | Unmeasured | actual Office visual check | UNMEASURED |

## How to interpret the measurements

- Strict complete-region recovery is 64/275, not the 268/275 literal-only match count. Missing full-table relationships affect their declared source regions; partial content or unresolved structure cannot count as complete. Whole-page success is 0/8 and whole-logical-table success is 0/3.
- Baseline to candidate: CER 378/12,860 to 17/12,860; body-grid correctness 39/125 to 125/125; critical token correctness 208/211 to 211/211; order 10/20 to 20/20. These improvements do not repair the 12 absent machine relationships.
- Natural errors changed from 104 (33 detected) to 29 (8 detected). The remaining population became harder. Candidate natural critical detection is 7/11; the separate paired challenge is 12/12 with zero control false alarms. These denominators must never be combined.
- 25 candidate false/generic prompts remain: eight source-tokenization comparisons, two decorative underscore comparisons and 15 generic original-ink warnings. Unverified scope is retained explicitly; generic coverage alarms are not credited as specific errors found.
- Candidate safe automatic passes are zero in A, B and end-to-end evaluation. The release-qualified subset is zero; automatic-pass correctness is therefore unmeasured, not 100%. Existing confidence thresholds are unchanged.

## Human workload and actual operations

The frozen inventory has 15,120 addressable review items: 13,751 content, 1,365 coverage and four structure items. It includes 1,051 evidence-only items and overlapping original scopes. The [item/scope mapping](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/workload/item-scope-map.json) records each item and exact shared geometry; it deliberately leaves independent human task IDs unset. Normal reviewer outcomes and time are unmeasured because no normal A/B decisions were made. “Needs review” is a queue state; “confirmation only” and “actual correction” are outcomes after review. They cannot be added as separate population counts.

The Agent surveyed 275 original regions and adjudicated 29 remaining natural defects. Those engineering observations are separate from actual reviewer workload. The real footnote repair changed one affected row, staled its old source check and retained other unresolved findings. The synthetic scan fixture has one delivered Requirement after scoped correction and review; it is not a real-scan quality sample. Ten timed same-text corrections measure persistence without accepting normal content.

## Persistence, export and environment

Local macOS 26.6.2; Apple M4 / 16 GiB was observed in an earlier device record and could not be refreshed by the restricted hardware query. The full-load fixture copied 38 documents, 15,120 review items and its artifacts. Twenty lists, twenty cached previews and ten guarded database saves were measured. Two ordinary export cycles and one unlock recovery passed the 60-second suggested budget. A simulated lock preserved old Excel bytes while later decisions saved; exact request replay, stale guard rejection and conflicting request-ID rejection passed.

The real relation fixture reached coherent saved/exported event 85, with the note attached under `Notes / footnotes` and `related_content.role = notes`, while remaining Not delivered. The synthetic scan fixture reached event 64, one published Requirement and zero pending items. Native Excel visual acceptance is Pending by explicit user instruction. The earlier opening/unlock problem is resolved and four bounded native views were inspected; the remaining visual scope stays unverified. Open XML validity and cell/version readback do not replace it.

## Evidence and next discriminating steps

- [Machine-readable metrics](metrics.json) and [CSV](metrics.csv) bind every numerator, denominator, method, evidence path and next action. Evidence paths inside the JSON resolve from the retained stage run directory.
- [Functional matrix](functional-matrix.md), [checkpoint 1](checkpoint-1.md), [checkpoint 2](checkpoint-2.md), and [normal-runtime load review](runtime-load-review.md) separate functionality, loaded state and quality.
- Next quality experiment: establish original-side cross-page table/header/note graphs for the unchanged full Appendix VI window, compare specific verifier findings against all natural silent errors and controls, and inspect the remaining footer merges. Do not tune classifier decisiveness by treating every no-keyword passage as negative.
- Production release still needs disjoint independent reference ownership, calibration, held-out acceptance, real scans, peer subdivision decisions and actual reviewer-effort measurement. The optional model arm requires separate authorization and a matched frozen comparison.

Additional operational correction: [checkpoint 6](checkpoint-6.md) verifies prerequisite navigation and correct original-page scope. Its 20 one-document detail reads have p95 0.230 seconds. This supplementary benchmark does not replace Q29–Q34 or change quality denominators.

[Checkpoint 10](checkpoint-10.md) isolates native font-boundary spacing. Its same-configuration eight-page rerun changes exactly seven cell regions, retains all 268 other region texts and preserves 211/211 critical tokens. The prior parser-03 metrics are retained separately; existing full-load performance and manual fixtures keep their original runtime scope. New parsed output is displayed in a separate real workbench fixture and synchronized at event 1; no business acceptance is inferred.

[Checkpoint 11](checkpoint-11.md) changes exactly two complete-original B judgments, with 41/41 positives retained. Its actual unaccepted A bibliography has a line-wrap space inside a URL and remains undetermined, while the contact is context. This diagnostic/runtime distinction is preserved; no B relaxation masks A damage.
