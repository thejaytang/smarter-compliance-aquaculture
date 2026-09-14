# Frozen-window verification result

Measured on 2026-09-12 using `material-structural-parser/2`. The matching policy and evaluator were hashed before the first parser run. Source hashes and every artifact in the source-annotation freeze were checked before processing. Both original inputs, annotation freeze, parser file and classifier file remained unchanged through completion. `run-start.json`, `measurement-freeze.json`, `summary.json` and the retained candidates provide the exact binding.

Only PA057 PDF pages 5-6 and CS010 PDF pages 3-4 were processed. Output is an isolated engineering candidate, not an adopted material or a business INCLUDE decision. The transport's synthetic QS identities did not write to a business store. Both candidate statuses are `partial` because the requested page windows leave other document pages unprocessed. Each processed scope has usable output and an empty `unresolved` list; generic parser warnings mention native-text, heading, order and table limitations.

## Full source text and fragments

| Frozen scope | Exact full text containment | Whitespace-only full containment | All source-line fragments present |
| --- | ---: | ---: | ---: |
| PA057 pp5-6, all content units | 17/33 | 29/33 | 30/33 |
| PA057 native-assisted stratum | 17/31 | 29/31 | 30/31 |
| PA057 visual-only stratum | 0/2 | 0/2 | 0/2 |
| CS010 pp3-4, all content units | 9/45 | 19/45 | 22/45 |
| CS010 native-assisted stratum | 7/37 | 17/37 | 20/37 |
| CS010 visual-only stratum | 2/8 | 2/8 | 2/8 |

These are distinct diagnostics, never interchangeable scores. “Exact” does not join output block line breaks; the whitespace-only measure joins whitespace but changes no punctuation, spelling or order. A paragraph can retain every source line yet fail complete ordered containment. Fragment evidence is not complete-unit recall. All 78 frozen units remain accounted for; the visual-only units are not removed because OCR is disabled. Page images can preserve their visual source without producing extracted editable text, which does not satisfy the text-containment test.

Neither window reaches the target of 95% complete source-unit retention under the frozen whitespace-only ordered-containment diagnostic. This is evidence of an unmet engineering gate, not a universal estimate of document extraction recall. Native-assisted and visual-only strata remain separate in the detailed JSON.

## Structure

| Scope and relation | PASS | FAIL | UNMEASURED |
| --- | ---: | ---: | ---: |
| PA057 table cell positions | 8 | 0 | 0 |
| PA057 column header-to-cell positions | 6 | 0 | 0 |
| PA057 complete-text order | 20 | 3 | 2 |
| PA057 under-heading relations | 0 | 17 | 0 |
| PA057 attached definition note | 0 | 1 | 0 |
| CS010 heading parent relations | 0 | 4 | 0 |
| CS010 list membership | 0 | 4 | 0 |
| CS010 complete-text order | 3 | 22 | 2 |
| CS010 under-heading relations | 0 | 20 | 0 |

Ambiguous repeated or missing complete matches are retained, never awarded PASS. Order evidence does not prove heading hierarchy. The column-header checks establish matching cells at their expected coordinates in one product table; they do not independently verify visual header styling. The 90% structural gate is not achieved by these diagnostics.

## Critical content

PA057 preserves all 18 frozen critical substrings after whitespace-only normalization on the expected source page. CS010 preserves 46/54. These checks establish page-bound text occurrence, not semantic association accuracy, which remains UNMEASURED.

The eight CS010 critical substrings not intact in same-page ordered output are:

- Page 3: `If wild-caught brood stock is used`.
- Page 3 graphic footer: `55` and `50672`.
- Page 4: `no less than seven hours on-site`.
- Page 4: `no product handling`.
- Page 4: `less than five workers`.
- Page 4: `more than seven hours on-site audit time`.
- Page 4: `also exclude the duration of the GRASP assessment or any other add-on CB audit`.

Failure here does not by itself distinguish omission, ordering, fragmentation or transcription distortion. It means the complete frozen phrase was not preserved by this exact test. The product's `unresolved` list did not identify these locations; its generic warnings are not per-clause detection evidence. The detailed measurement now flags each failed phrase and retains its source page and annotation identity.

## Existing classifier: separate source-oracle diagnostic

No product extraction output was used in this test. The classifier received the frozen source-evaluation units, source-derived heading kind and original refs; expected labels were not used as classifier input.

| Source reference class | Predicted requirement | Predicted context | Predicted undetermined |
| --- | ---: | ---: | ---: |
| PA057 context, n=33 | 3 | 2 | 28 |
| CS010 Requirement, n=13 | 9 | 0 | 4 |
| CS010 context, n=27 | 1 | 9 | 17 |
| CS010 undetermined reference, n=1 | 0 | 0 | 1 |

PA057 has no reference positives: recall is undefined. CS010's uncertain declarative certificate-field unit remains a separate stratum, with no relabeling. This table diagnoses the classifier under correct source-unit boundaries; it does not validate actual material unit assembly or end-to-end precision/recall, and cannot establish the 90%/90% delivery gate.

## Trust, boundaries and next use

The annotations were visually reviewed and prediction-blind for this round before measurement, but both documents were historically exposed. CS010 transcription assistance used PDFium after the independent Poppler bbox failure; engine independence is therefore limited. See `../verification-annotations/TRUST_AND_SCOPE.md`. This is engineering source evidence, not business-expert Gold or an all-history independent test.

No product debugging or code changes were performed after observing these outputs. Any future use of these specific failures for development must explicitly mark these windows as exposed to that development and use a different independent check where feasible. Retain this measurement unchanged as the pre-fix evidence. The immediate delivery conclusion is an unmet local source/structure gate, with specific critical-content and classifier gaps preserved for a separate development cycle.
