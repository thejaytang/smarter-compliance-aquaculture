# Original occurrences and spatial ownership

Date: 2026-09-10. Decision: **CONTINUE**. [The PDF reliability goal](../goals/pdf-verification-reliability-20260910.txt) remains active and independently unaccepted. [Checkpoint 41](41-pdf-verifier-critical-differences.md) supplied the exposed CS004 page-19 development observations and preserved original; this checkpoint did not open new acceptance material.

## Failure and intervention

The original has three separately located `or,` lines in its requirement table. A constructed output kept only one occurrence while assigning it a box spanning all three locations. Method 2 produced no discrepancy because each original line independently reused the same output word. Existing general unverified-scope entries still prevented an automatic correctness claim, but did not identify this specific omission.

Method `original-page-comparison/3` now performs spatial capacity accounting for repeated tokens. Each output occurrence can satisfy one original occurrence per evidence engine. A maximum assignment allows valid alternative matches rather than making a greedy assignment that causes false omissions. Native and OCR observations are treated separately, not added into a duplicated reference count. Shortfalls retain required/matched counts, all affected original regions and candidate output identities. Where the exact omitted occurrence cannot be resolved, the report explicitly retains that ambiguity.

Several output records claiming the same separate parallel source text now create a localized `output_spatial_ownership_ambiguous` scope item. This is an abstention requiring location/column inspection, not a diagnosis of a proven table error. A single legitimate numbered paragraph is not inherently a conflict. Single aggregate table records, arbitrary row swaps, merged cells, note ownership and cross-page associations still require stronger structural evidence.

The first spatial heuristic added three unnecessary local scope prompts to the real development page: a criterion number with its title, a numbered paragraph and a near-boundary footer overlap. Diagnosis led to strict interior overlap and competing-record claims. The final result retains the existing eight natural candidates and five unverified entries. Their true/false labels remain unconfirmed; unchanged counts do not establish a zero false-alarm rate.

## Bounded observations

| Frozen challenge | Before | After |
| --- | --- | --- |
| Three real original occurrences represented by one output occurrence | No specific finding | One located shortfall, required 3 / matched 1 |
| All three occurrences retained in one output record | No finding | No finding or added localized abstention |
| Three separately positioned output occurrences | No finding | No finding or added localized abstention |
| Two outputs with competing broad boxes over the original table headings | General unverified scope only | One localized ownership abstention, with both content targets |

The prior eight seeded difference controls still detect 8/8 and the two prior unchanged controls remain unflagged. Neither population is independently labelled acceptance material. Real original/PDF/Gold fingerprints and development exposure remain unchanged. No real scan or new held-out source has become available through this experiment.

## Human interface and downstream protection

The existing shared `source-check.js` component now displays occurrence counts and the compared output, highlights each original region separately, and provides location/content buttons for scoped uncertainty. A browser check used an explicitly labelled, read-only diagnostic fixture with the actual shared component and original page image. It confirmed three distinct occurrence highlights, two distinct table-heading highlights, opening the one merged output and both competing output targets, and no browser warnings/errors. The fixture saved no business decisions and did not represent an independent reviewer or the normal workbench service. Its temporary browser tab and HTTP process were closed after checking; normal services were not stopped.

A focused owning-workflow test confirms that an ownership scope with zero ordinary findings still creates a persistent page blocker and suspends downstream B delivery. Classification cannot bypass the content gate. Existing isolated correction/history/export/replay/staleness tests also passed. This checkpoint does not claim an actual real-PDF repair and acceptance transaction in the normal browser; that end-to-end gate remains open.

## Validation and cost

- The assignment implementation matched an independently enumerated oracle on all 512 small bipartite graphs, plus constrained-capacity, reassignment and shared-engine controls.
- Full System2 regression: **757 passed, 1 existing skip, 1 existing warning**, 25.71 seconds. A subsequently added focused downstream-scope test also passed; it was not part of that full-run count.
- Workbench frontend: **19 passed**. Updated JavaScript syntax passed.
- Pure comparison on the frozen 57-line / 38-record page, 20 observations after warm-up: baseline median 0.00306 seconds, observed maximum 0.00349; current median 0.00721, observed maximum 0.03293. These measurements exclude original acquisition/OCR, database save, Excel and human effort; they are not production percentile guarantees or approved budgets.
- Preservation matched all 18 tables in the same two normal owning stores, all 73 managed source files and all 51 Gold files against checkpoint 41's validation baseline. No normal source selection, review decision, original, Canonical, threshold or scheduled action was submitted or changed.

The system remains locally runnable without an API. Independent references, calibrated confidence, real reviewer time and representative scanned/mixed material remain unverified. The Mac was locked, but the in-app browser component check worked; no native Office acceptance is claimed.

## Evidence and next checkpoint

Retained evidence is under `system2/outputs/runs/pdf-verifier-reliability-20260910/cp42/`: frozen spatial cases; comparator baseline; before/first-iteration/final results; explicit diagnostic evaluation; unchanged earlier challenge replay; natural-page candidate reports; timing observations; browser-component evidence and read-only fixture; and preservation report. Validation logs are `system2/runtime/pdf-verifier-cp42-regression.txt` and `workbench/runtime/pdf-verifier-cp42-frontend.txt`.

The challenge evaluator accepts both the earlier diagnostic schema and `verifier-spatial-challenges/1`. It reports detected discrepancies separately from localized abstentions and retains null independent precision/recall. Use a new output path for every replay. Historical baselines and challenge answers remain untouched.

Next inspect the actual table, footnote and cross-page relationship representations and the existing human-review records. Define the smallest source-bound reference and evaluation interface that can test relationship errors, and prepare the reference-review route in the shared workbench. Flat text/position checks cannot establish those relationships. Continue engineering while independent reviewer and suitable additional material remain unresolved; do not manufacture labels or redefine the goal around the passed controls.
