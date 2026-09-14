# Grid rejection with exact positioned-line fallback

**Isolated guard behavior passed on the fixed DEV windows; overall extraction quality is not accepted.** The predeclared **>=25% crossing-line ratio at 1 pt** rejected the six diagnosed wrong fine grids. It restored **14 exact original positioned lines**, retained all eight real table regions unchanged, and left the known 1×1 figure false table unchanged. All seven bounded document runs and existing candidate-shape validation succeeded.

Open [the six visibly unresolved source ranges](unresolved-ranges.html) to compare the retained page image with fallback native text. This is a standalone evidence preview, **not a loaded workbench change or browser acceptance result**.

## Frozen scope and provenance

This experiment restores the exact parser `/4` source SHA `3696f3aab5aff829e7247418bd0b22cec1b5f3008c6419ac842f67ff7c38bce2` from its preserved experiment and verifies byte identity before adding the isolated guard. It does not import or overwrite the concurrent product `/5` HTML numbering changes. The experimental version is `material-structural-parser/4+dev-grid-consistency`; the actual native backend remains unchanged PDFium. No richer-word substitution, font-based heading rule, Docling, model or external service is used.

The seven previously exposed DEV documents cover the same 15 accepted grids: Farm pp28–29, Interpretation pp19–21, Audit pp1–3, Salmon/Cod p18, and the existing multicolumn, cross-page and borderless/figure synthetic windows. Original source and annotation hashes, positioned configuration and old candidates remain unchanged. All thresholds/denominators were recorded before this parser-copy run; no rule was adjusted after results.

## Behavior and preservation

| Case | Before → after | Result |
| --- | --- | --- |
| Farm | 44 → 50 blocks; four false grids → zero accepted tables | Ten original positioned lines restored; four located unresolved ranges |
| Interpretation | 115 → 117 blocks; two false grids → zero accepted tables | Four original positioned lines restored; two located unresolved ranges |
| Audit | 14 blocks, three tables | Every candidate block payload unchanged |
| Salmon/Cod | 16 blocks, two tables | Every candidate block payload unchanged |
| Multicolumn synthetic | 9 blocks, one table | Every candidate block payload unchanged |
| Cross-page synthetic | 7 blocks, two tables | Every candidate block payload unchanged |
| Borderless/figure synthetic | 16 blocks, one false table | Unchanged known failure |

Every original nonrejected primitive retains its exact text, fields, source refs and relative order after expanding stored paragraph groups. All 14 new fallback primitives appear once with exact native text, bbox and original-page/native-ID references. All native page evidence is identical to `/4`. The rejection evidence retains the full rejected table, native lines, merged-cell rectangles, crossing counts and decision settings. A per-region `unresolved` item contains a readable message, source bbox/reference, rejected-candidate ID and evidence file; that same message is visible in the candidate warnings. Raw source is not rewritten and no main version is adopted.

The guard re-evaluates original line bboxes against **actual merged cells**, excluding internal edges hidden by a merge. It rejects the entire proposed grid only when the predeclared fraction is reached. This removes false cell structure; it does not reconstruct a correct table or certify that native fallback text is visibly printed.

## Existing engineering checks

These complete-text diagnostics are unchanged before → after:

| Source | Complete page-bound segments | Formal text on one bound page | Clause text in one block | Critical labelled phrases |
| --- | --- | --- | --- | --- |
| Farm | 18/25 | 6/6 | 7/7 | 9/9 located phrases matched |
| Interpretation | 8/12 | 1/3 | 13/13 | 7/7 located phrases matched |
| Audit | 48/79 | 6/12 | 7/16 | 42 located phrases matched; **22 labels not located in existing segment evidence remain UNMEASURED** |
| Salmon/Cod | 20/21 | 4/4 | 4/4 | No labelled phrase denominator, **UNMEASURED** |

The eight positive/one negative existing marker-relation subset is unchanged. Synthetic cell-string multiset diagnostics are also unchanged: multicolumn **6/6**, cross-page **12/12**, borderless/figure **0/10**. The latter remains a failure. The synthetic count is exact whitespace-normalized intersection of annotated cell occurrences with extracted nonempty table cells; it is not an independent real-document fidelity measure. Existing real engineering labels and mechanism Gold were not edited.

There is **no measured content-coverage gain**. This result supports safer rejection of inconsistent structure, preserved manual repair inputs and explicit recovery state on calibrated DEV cases. It must not be presented as meeting the 95% coverage, 90% structure or Requirement precision/recall targets, or as improving the already exposed reserved `/4` FAIL.

## Decision and remaining checks

The isolated experiment is evidence for considering a small product guard, not automatic promotion. A real product change would need review of the general rule and failure behavior, targeted merge/boundary regression, relevant source/quality regression, integration of visible unresolved ranges and a fresh candidate/full System2 regression. Product `/5` is separately an HTML numbering change; its 49 targeted parser/reader tests do not retroactively bind the historical `/4` full regression to `/5`.

The 1×1 false table, missed borderless structure, partially incorrect Audit merges/rows, hidden Criterion text and general PDF heading/multicolumn issues remain. This ratio was calibrated on these exposed DEV cases, so independent acceptance remains **UNMEASURED**. No reserved samples were inspected or reused for tuning.

Evidence: [final status and preservation](outputs/final-status.json), [primitive/ref/order verification](outputs/verification.json), [fixed annotation assessment](outputs/assessment.json), [pre-run freeze](outputs/freeze.json), [source/script hashes](outputs/experiment-freeze.json), [guard](grid_guard.py), [copied parser](material_experiment.py), and [runner](run.py). Per-sample receipts and complete raw grid/native/rejection evidence remain under `outputs/`.
