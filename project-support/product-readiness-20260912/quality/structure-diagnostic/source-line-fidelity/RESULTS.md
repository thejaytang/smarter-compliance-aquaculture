# Source-row preservation checkpoint and accuracy-work stop

The user redirected the active goal on 2026-09-13 while the already-started product regression was finishing. **No further accuracy optimization is planned.** The current acceptance contract is [the human-led goal](../../../../../docs/design/human-led-workbench-goal.md). This checkpoint retains the completed change and its evidence; it does not claim automatic quality acceptance.

## Implemented and verified

`material-structural-parser/7` reassembles adjacent same-row native fragments only when original text and geometry prove the join. Numeric/list markers, nonadjacent native positions, missing intervening words, different pages/rows, overlapping layers, columns and table/image barriers prevent joining. The original source interval supplies whitespace rather than an invented joiner. Every primitive payload and reference is retained in reversible evidence. A failed complete-order read leaves positioned text available and creates a located unresolved issue; no successful review is inferred.

The new helper belongs to `system2/src/pdf_extraction/assemble/material_rows.py`; the material parser only coordinates it. The new `pdf-source-row-groups.json` records source SHA, parser configuration, original page/text, whitespace-normalized interval coordinates, union boxes and complete members. These intervals are not PDF glyph indices. Original/Canonical and human revisions were not modified.

**189/189 material-module tests PASS**, zero failures/errors/skips, including nine new source-row/integration cases. [JUnit](product-v7/junit.xml), [test command](product-v7/test-command.json), [test log](product-v7/tests.log) and [summary](product-v7/summary.json) bind the run. All 37 frozen source, annotation, code, test and evaluator files remained unchanged. This is not a full System2/Workbench or browser regression.

Nine bounded DEV/mechanism PDF inputs reproduce the isolated-copy experiment exactly. All accepted tables, native pages and recursively reconstructed primitive payloads are identical to /6; no previously matched DEV source segment or critical phrase is lost. CS010 has 23 joined rows from 67 fragments; Farm has one row from two fragments; the other seven outputs have no row joins. Scan-only output remains empty with a visible unresolved source scope.

## Historical automatic diagnostics, not an active completion gate

CS010 pages 3–4 were explicitly promoted to DEV before diagnosis ([scope](scope.json)); they cannot establish independent verification. Under the unchanged frozen evaluator, complete units increase from 24/45 to 30/45, ordered structural relations from 7/55 to 17/55, and critical substrings from 46/54 to 52/54. All six affected body condition/duration phrases are restored. Two graphical footer values remain unmatched; heading/list hierarchy still fails. The former overall automatic-quality target remains a historical FAIL, now deferred by the user. No new holdout was selected, no Gold was edited, and Requirement identification was neither connected nor measured here.

[Experiment comparison](trial2/experiment-summary.json), [product measurement](product-v7/cs010-measurement.json) and [product freeze](product-v7/freeze.json) retain the full denominators and limitations. Existing four ASC source-segment denominators remain 25, 12, 79 and 21; detailed unchanged before/after results are in the product summary. Engineering annotations are not business-expert Gold.

## Loading, recovery and retained failed attempts

The code is implemented and loaded by isolated direct System2 parser invocations. No business extraction, adoption, confirmation or normal-service restart was performed. Future material-worker processes read source code, so they can load /7 even when the Workbench parent was not restarted; no normal business invocation was verified in this checkpoint. Browser loading of /7 is not claimed.

The exact previous /6 parser and its SHA are in [pre-change](pre-change/manifest.json). A reviewed rollback can restore those bytes without touching originals, candidate artifacts, review stores or history. Preserve the helper, tests and evidence as appropriate until rollback is verified.

The initial pure test failed because its idempotence fixture incorrectly expected a native ID on a derived union reference; the corrected test passes original native lines. The first copied-parser experiment failed at the copy-relative configuration path after its baseline run; the retry binds configuration lookup to the real System2 path. Both failures/logs remain. They were harness corrections, not concealed product or quality successes.
