# 1. Parser /4 frozen-window verification

**Overall extraction gate: FAIL.** The final `material-structural-parser/4` improves some ordered source text and editable-unit grouping, but neither fixed PDF window reaches 95% complete content retention or 90% structural fidelity. CS010 still has eight unmatched critical substrings without location-specific product warnings. No parser code, annotation, denominator or matching rule was changed after observing these results.

The existing evaluator, matching policy and measurement-freeze were copied byte-for-byte from `../verification-after/`. `page_of()` already iterates all `source_refs` and deduplicates page numbers, so grouped references required no adaptation. Every source-annotation artifact hash was validated before and after measurement. The successful run completed at `2026-09-12T23:12:28.350160+00:00` in the declared System2 environment. A first wrapper omitted `PYTHONPATH` and failed before parser import/invocation; its initial run-start and receipt are retained. The environment-only retry succeeded in 0.913 seconds.

Only PA057 pages 5–6 (zero-based 4,5) and CS010 pages 3–4 (zero-based 2,3) were parsed into new isolated engineering candidates. Both return `partial` because the remaining document pages were deliberately outside scope. Both processed windows have usable content and empty `unresolved` lists. These candidate statuses do not certify fidelity or adoption; no business store was used.

## 1.1 Source units, by PDF difficulty and stratum

| Frozen sample/stratum | Denominator | /2 exact | /4 exact | /2 whitespace-only complete | /4 whitespace-only complete | /4 all frozen fragments present |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PA057 native PDF with ruled table, all units | 33 | 17 | 17 | 29 | 30 | 31 |
| PA057 native-assisted | 31 | 17 | 17 | 29 | 30 | 31 |
| PA057 visual-only marks | 2 | 0 | 0 | 0 | 0 | 0 |
| CS010 native PDF with fragmented list/graphic footer, all units | 45 | 9 | 9 | 19 | 24 | 27 |
| CS010 native-assisted | 37 | 7 | 7 | 17 | 22 | 25 |
| CS010 visual-only fields | 8 | 2 | 2 | 2 | 2 | 2 |

All 78 content units remain in the denominator, including visual-only footer and publisher marks. PA057 reaches 30/33 = 90.9%; CS010 reaches 24/45 = 53.3% under the frozen whitespace-only complete ordered-containment diagnostic. Neither reaches 95%. Exact containment, normalized containment and source-fragment presence are separate diagnostics and are not interchangeable recall estimates. HTML, XLSX, scanned PDFs and other formats are **UNMEASURED in this reserved-window run**.

No previously normalized-complete unit was lost: PA057 gained one and CS010 five. Units with complete text in a single editable block increased from 17 to 29 for PA057 and 9 to 17 for CS010, without changing the frozen acceptance measure. The comparison spans `/2` to `/4`, including `/3` ordering changes; it is not an isolated causal estimate of `/4` paragraph grouping alone.

## 1.2 Structure

| Sample / frozen relation | PASS | FAIL | UNMEASURED | Frozen denominator |
| --- | ---: | ---: | ---: | ---: |
| PA057 table cell positions | 8 | 0 | 0 | 8 |
| PA057 column header-to-cell coordinates | 6 | 0 | 0 | 6 |
| PA057 complete-text order | 21 | 2 | 2 | 25 |
| PA057 under-heading relations | 0 | 17 | 0 | 17 |
| PA057 definition-note attachment | 0 | 1 | 0 | 1 |
| CS010 heading parent | 0 | 4 | 0 | 4 |
| CS010 list membership | 0 | 4 | 0 | 4 |
| CS010 complete-text order | 7 | 18 | 2 | 27 |
| CS010 under-heading relations | 0 | 20 | 0 | 20 |

PA057 has 35 PASS / 57 frozen relations; CS010 has 7 PASS / 55. Ambiguity remains in the denominator and is not counted as PASS. Text-order checks do not prove hierarchy. Header-to-cell coordinate checks do not verify visual header styling. The 90% structure gate remains **FAIL** for both windows.

## 1.3 Critical text and traceability

PA057 retains all 18/18 frozen critical substrings on their expected page. CS010 retains 46/54; the failures are unchanged from `/2`:

- CS010 p.3: `If wild-caught brood stock is used`; graphic-footer `55`; graphic-footer `50672`.
- CS010 p.4: `no less than seven hours on-site`; `no product handling`; `less than five workers`; `more than seven hours on-site audit time`; `also exclude the duration of the GRASP assessment or any other add-on CB audit`.

These are failures of complete phrase presence in ordered output, not a diagnosis of whether the cause is omission, fragmentation, order or transcription. The detailed JSON retains every annotation identity, expected page, critical span and matching output reference. Matched phrases and preserved source refs do not prove correct condition/exception association; association accuracy remains **UNMEASURED**. Product warnings remain generic, so they do not satisfy the no-unreported-critical-loss gate for CS010.

## 1.4 Input and code binding

| Artifact | SHA256 |
| --- | --- |
| Parser `/4` | `3696f3aab5aff829e7247418bd0b22cec1b5f3008c6419ac842f67ff7c38bce2` |
| PA057 original PDF | `f9f6bd8531c2cd8a4cc7dd49e4035aaef6ff33cb2f7dbf93f0e340ca0b454778` |
| CS010 original PDF | `ce5c8950c69e3b5b60b85110f5abd2c6d8637c83291c6c00ac03f28b102dac54` |
| Frozen evaluator | `c9a0fa2f5fdc5c627f2eb21b339f4679fcc126fc4e32926b251c9dc22c8e0f52` |
| Frozen matching policy | `9897376faebfd73c856af3cc02f04decc2c95d30bfabc0029ac4cd0bd3a8f9ee` |

`run-start.json`, `evidence-checksums.json`, candidate `config_hash`, native backend evidence and unchanged annotation freeze bind the full run. The parser, classifier file, original PDFs and source annotations remained unchanged throughout. Old results are untouched.

## 1.5 Trust and separate classifier diagnostic

These are **current-round reserved source annotations, not an all-history unseen holdout**. Both source documents were historically exposed. CS010 transcription assistance shares PDFium with the native backend. The annotations were source-first and withheld from this development cycle; they are engineering evidence, not business-expert Gold. The parser implementation author executed the byte-identical evaluator, so this is a frozen automated replication, not independent human review. No business colleague or Windows machine participated.

The unchanged original runner also executes a literal source-oracle classifier diagnostic. It reproduces the prior matrices: PA057 33 context references yield 3 requirement, 2 context, 28 undetermined; CS010 13 requirement references yield 9 requirement and 4 undetermined; 27 context references yield 1 requirement, 9 context and 17 undetermined; one uncertain reference remains undetermined. This does not exercise the current product classifier adapter or material assembly and must not be substituted for end-to-end Requirement precision/recall. Those remain **UNMEASURED here**.

`comparison.json` and per-sample measurements retain all gains, failures and denominators. This evidence is now exposed to the measurement agent. It must not be used to tune product behavior while continuing to claim withheld validation; a future development cycle must record that exposure and select a new verification scope.
