# Checkpoint 44: source-error assessment and denominator protection

Decision: **ADJUST** the immediate sequence. Fix misleading measurement assumptions before collecting labels through a new screen, then continue the shared-workbench reference pass. The PDF quality goal remains active.

## Failure found

The legacy generic evaluator excludes header/footer text, compares unordered cell text and span collections, and computes cross-page merge precision/recall from merge counts. On an output-derived control from the already exposed CS004 page-19 development table, reversing every column index leaves `cell_exact_match` and `row_column_span_f1` at 1.0. Its empty cross-page-merge denominator also returns 1.0. These are not evidence of correct columns, relationships or independent source accuracy.

The [before/after experiment](../../outputs/runs/pdf-verifier-reliability-20260910/cp44/legacy-metric-blindspot.json) is explicitly an output-derived diagnostic, not an independent reference. No real source labels were invented or overwritten. The old feature metrics remain useful for their original regression scope and now carry explicit limitations in generated reports/CLI output.

## Implemented assessment entry

The [reference/assessment contract](../contracts/pdf-source-reference.md) defines a source-first collection sequence and the implemented offline evaluator. Exact source, reference, effective-record and verifier-report digests are required. A single frozen page check is assessed, with supporting page regions allowed for context. Context-only errors cannot enter that page's denominator. Old report changes, source changes, missing IDs and repeated primary credit fail validation.

The error inventory includes omissions that have no extraction item or machine alarm. Every output record, reference region and finding must be accounted for before diagnostic metrics are emitted. Incomplete source survey, dimensions, findings or drafts stay unknown. The evaluator separates relevance precision, useful finding precision, unique error recall, localization recall, false alarms, duplicates, scope burden, per-category recall and critical misses. Unverified scope never automatically counts as detection. Empty categories/denominators stay null.

The first counting check exposed an ambiguity in duplicate handling: a duplicate alarm can supply a useful correct location even when the primary location is wrong. Localization now credits that supported location once while detection and useful-issue counts remain unchanged. This was a productive refinement within the first implementation round.

The file-only evaluator does **not** authenticate independent human review, frozen sample qualification or release authority. Its independent metrics always remain null, including when a file claims a reviewer/receipt. No CER/WER, automatic handling proportion, human time, representative confidence interval or final quality conclusion is inferred from this error-event inventory. The shared-workbench reference collection/receipt gate is the next unfinished implementation, not a delivered capability.

## Validation

- 32 targeted tests passed, including 18 new assessment controls and the existing generic evaluation/processing integration coverage. These check original-only misses, duplicate accounting, localization, empty denominators, partial-review refusal, exact bindings, context scope, attempted file authority claims, and exclusive CLI output. No full-source parse or new external dependency was used.
- A known synthetic counting control has 2 errors, 3 findings, 1 duplicate and 1 false alarm. Diagnostic detection recall is 1/2; relevance precision 2/3; actionable precision 1/3; localized recall 1/2. The critical omitted error remains explicitly listed. These are hand-constructed engineering quantities, not PDF-quality estimates.
- The standalone CLI ran against the governed CS004 original and the frozen checkpoint-43 column-reversal output/report. The [partial assessment](../../outputs/runs/pdf-verifier-reliability-20260910/cp44/partial-assessment-report.json) correctly returns null metrics and seven incomplete conditions. Its single engineered reversal label does not adjudicate the eight unresolved natural candidates or the complete original page. The engineering reference file is not a ready human reference or authoring template.
- Normal database tables, managed source files and retained Gold were compared again against checkpoint 41. The [preservation result](../../outputs/runs/pdf-verifier-reliability-20260910/cp44/preservation.json) and [artifact manifest](../../outputs/runs/pdf-verifier-reliability-20260910/cp44/artifact-manifest.json) bind the final evidence. No normal source decision, human acceptance, Gold annotation, threshold, scheduler or provider configuration was changed.

## Next checkpoint and missing inputs

Implement a bounded source-first reference task in the existing workbench, with persisted drafts, source-bound confirmation/version history, explicit coverage and prior-exposure records. Test it on an isolated development copy with an unmistakable engineering actor; do not populate real human reference answers from extracted content. Follow with extraction-error and verifier-finding adjudication using the same frozen assessment interface.

The independent reference owner remains unassigned, and a qualifying real scan, distinct calibration/held-out source-family support and user release thresholds remain open inputs. Continue implementation while preserving those acceptance gates. Existing functional delivery remains completed in its separate scope; this checkpoint does not establish PDF extraction or verifier accuracy.
