# Rich PDFium evidence in the unchanged material path

**Decision: do not promote naive word replacement.** The isolated adapter ran successfully on the two frozen DEV windows, preserving all original line evidence and adding finer native words/characters. It produced **no gain** on the unchanged engineering source/critical-text/marker diagnostics. Interpretation's candidate is identical. Two Farm table payloads changed and became more fragmented across an already incorrect fine grid. No product code, backend policy, dependency, model or Gold was changed.

## Scope and implementation

Farm pp 28–29 (zero-based 27,28) and Interpretation pp 19–21 (18,19,20) use the exact original native-comparison freeze. The previous source, annotation, relation and denominator hashes remain unchanged. These are active DEV engineering annotations, not independent holdout or business-expert Gold.

`rich_native.py` subclasses the installed project's `NativeExtractor` in this isolated process only. It invokes the existing explicit PDFium path, retains its `text_lines` objects without alteration, and partitions each existing line into native-character-backed words and separators. Characters, generated/mapping flags, font names/sizes and source-index mappings are preserved in extra evidence artifacts. Word `font_key` remains `None`; no resource key was invented and native spacing repair was not implicitly enabled.

`material_experiment.py` is an isolated copy with version `material-structural-parser/4+dev-pdfium-granularity`, an explicit granularity policy, and native-generator version/hash in the evidence. Actual backend stays `pypdfium2`; Docling is not imported. The production parser and native extractor files are untouched. Import readiness and parsing have separate 300/60-second operational guards; both conditions completed without reaching a guard.

## Fixed diagnostic results

All figures below are unchanged before → after. Each denominator retains its original definition; rows overlap and must not be pooled into a coverage score.

| Diagnostic | Farm | Interpretation |
| --- | --- | --- |
| Complete page-bound source segments | 18/25 → 18/25 | 8/12 → 8/12 |
| Complete formal text on one bound page | 6/6 → 6/6 | 1/3 → 1/3 |
| Formal text in one candidate block | 6/6 → 6/6 | 1/3 → 1/3 |
| Clause text in one candidate block | 7/7 → 7/7 | 13/13 → 13/13 |
| Frozen labelled critical phrases | 9/9 → 9/9 | 7/7 → 7/7 |
| Frozen marker relation subset | 2/2 → 2/2 | 7/7 → 7/7 |
| Heading blocks | 0 → 0 | 0 → 0 |
| Candidate blocks | 44 → 44 | 115 → 115 |

The evaluator uses the same whitespace-only text containment, page association, critical phrases and marker matching as the original native comparison. Adaptation only selects baseline/rich artifact paths and reconstructs frozen baseline pre-grouping payloads from already retained group members. No text repair, threshold, annotation or denominator changed.

## Preservation and actual changes

Across five pages, all **8097 character records** and **1160 whitespace word partitions** retain their source mappings. Per-character text reconstructs each PDFium page text exactly. All original native page payloads before enrichment match the frozen baseline; line IDs/text/bboxes remain exact. Word+separator partitions preserve each raw line, and all original character indices are accounted for. Candidate block IDs, ordering, source references, status and scope fields remain unchanged. The existing candidate-shape validator passes both outputs.

Interpretation has **zero block payload differences**. Farm has exactly **two differences**, both table rows. All other Farm block payloads are unchanged. The existing fake grid splits a native heading band into 14 columns, and another into 3×18 cells. Finer word boxes are consumed by the current cell-center rule, so phrases that previously occupied one cell are distributed across incorrect columns. For example, the already problematic `Legal Compliance` header becomes interspersed with hidden-layer words (`Legal Legal`, then separate `Compliance` cells). This is a concrete readability/order defect, although it is outside the current complete source-segment annotation subset and does not change its score.

Native preservation is therefore not sufficient to establish candidate structural fidelity. The existing table geometry must be addressed before finer words can safely improve cell assignment.

## Concrete reuse gap and next decision

- `material_parser._pdf_blocks` selects `page.text_lines or page.words` for ordinary content and unconditionally creates `text` blocks. Because line evidence was deliberately preserved, adding characters/fonts cannot improve paragraph or heading output in this path.
- `material_parser._pdf_tables` is the active consumer of `page.words`; it assigns words to cells by bbox center after `detect_table_boxes` and `_grid_positions`. Better word geometry cannot correct the wrong table/header grid. In this experiment it exposes that wrong grid more clearly.
- Legacy layout and hierarchy consumers also use `page.words`, and a shared extractor change could alter them even when current material text is unchanged. This experiment does not authorize broad replacement or prove a legacy benefit.

Stop this adapter path at evidence. The next useful independent diagnosis is general false-table/grid rejection or boundary validation on already exposed DEV cases, preserving complete native line text when a detected grid lacks trustworthy cell structure. Do not add sample-specific heading labels or treat font-size increases as correct visible headings. Covered Criterion text remains unverified.

Source coverage, broader structure, word accuracy and visibility acceptance remain **UNMEASURED** beyond these fixed active-DEV diagnostics; this run does not meet the overall extraction-quality gate. No full System2 regression was repeated because product code did not change.

Evidence: [final status/preservation](outputs/final-status.json), [fixed assessment](outputs/assessment.json), [complete block/geometry comparison](outputs/comparison.json), [original freeze](outputs/freeze.json), [experiment fingerprints](outputs/experiment-freeze.json), [runner](run.py), [native adapter](rich_native.py), and [assessment adapter](assess.py). Every enriched page also includes its complete pre-enrichment payload, raw character evidence and line-to-word/character mapping.
