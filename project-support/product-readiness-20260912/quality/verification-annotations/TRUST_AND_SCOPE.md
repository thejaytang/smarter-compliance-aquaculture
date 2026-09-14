# Source-only verification annotations

These engineering annotations cover only PA057 PDF pages 5-6 (printed pages 3-4) and CS010 PDF pages 3-4, as frozen in `../manifest.json`. Source hashes were checked before rendering and annotation. No original, Canonical or existing Gold was changed.

## Evidence and independence

All four complete page images were rendered with Poppler at 150 DPI and visually inspected. Paragraph, definition, table-cell, note, list and heading boundaries were assigned from those images. Original-source text assistance supplied transcription and enclosing geometry, not the product's predicted content. This annotation task did not inspect product parser predictions, modified `material_parser`, or development diagnostics.

These documents were withheld from this round's modifications and prediction comparison until this source annotation was frozen. Both had historical exposure, recorded in the source manifest. They are **not all-history independent holdouts**, and these annotations are **not business-expert Gold**.

PA057 text/geometry assistance used Poppler `pdftotext -bbox-layout`. CS010's Poppler bbox call aborted with `SIGABRT` / `std::out_of_range: basic_string`; the source still rendered correctly. The project pypdf environment could not decode its AES stream because its optional cryptography dependency is absent. No dependency was installed. CS010 therefore uses direct PDFium source text and character boxes, checked against the rendered page. This can share a text engine with the product, so it is not independent engine verification. The annotation grouping and labels remain source-only and prediction-blind.

Publisher marks and CS010's graphic footer text absent from source text assistance were transcribed from the image. Their manually enclosing boxes have approximately +/- 3 PDF-point precision. Nontext logo ornament and blank space are not textual units; the complete visible wordmark is retained.

## Fixed denominators

| Scope | Content units | Structural relationships | Critical spans | Requirement evaluation units |
| --- | ---: | ---: | ---: | ---: |
| PA057 pp5-6 | 33 | 57 | 18 | 33 context, 0 positive |
| CS010 pp3-4 | 45 | 55 | 54 | 13 positive, 27 context, 1 undetermined |

Every source-assistance line belongs to exactly one content unit; the visual pass added 2 PA057 publisher marks and 8 CS010 publisher/footer units. The complete content denominator includes all 78 units, including the uncertain classification and document furniture. Report native-text and visual-only strata separately; do not silently remove difficult or graphic units. These are complete inventories of the four specified visible pages, not complete documents or business-representative Gold.

Content units are visible headings, paragraphs, individual list items, table cells, notes, footer fields, margin fields or publisher marks. Wrapped lines within a paragraph remain one unit. Boxes use PDF points from the top-left corner. Unit text preserves source spelling and punctuation with wrapped whitespace joined by a single space. Rendering is the authority for visible text, and both raw assistance and images are retained.

Requirement evaluation uses the separate `requirement_evaluation_units` array. It partitions every content unit once. CS010's product-category lead-in and its four list items are a single complete applicability clause for identification, while remaining five distinct source-content units. All other units retain their source boundaries. A context label means “not a standalone Requirement”, not permission to delete the text. PA057 is a deliberately useful all-context window; its zero positive denominator makes recall undefined, never 100 percent.

The CS010 paragraph beginning “The scope of certification clearly defines the scientific name” remains **undetermined** because it may prescribe a certificate field despite declarative wording. Keep it in the content and classification inventory. Report uncertain classification separately; do not silently relabel or exclude it to obtain a pass. The visible rule boundaries and clear modal/applicability examples support engineering diagnostics, but formal precision/recall acceptance remains UNMEASURED until predictions, matching rules and this uncertainty are properly adjudicated.

Critical spans retain exact substrings and offsets. They include numeric identifiers/dates and manually selected duration, scope, prohibition, condition and exception phrases. Overlapping annotations are intentional: for example an Option number also participates in its complete applicability phrase. The denominator is the frozen listed spans, not all conceivable semantic interpretations.

## Files and checks

- `pa057-reserved-source-annotation.json` and `cs010-reserved-source-annotation.json`: source inventories, relationships, critical spans and candidate-evaluation units.
- `source-render-inventory.json`: source/image/page references and assistance limitations.
- `annotation-freeze.json`: source and annotation artifact hashes at the prediction-blind freeze.
- `build_source_annotations.py`: reproducible source transcription/grouping with assertions for complete, nonoverlapping assistance-line coverage and complete candidate-evaluation coverage. It never imports a product parser or classifier.
- The four PNGs and original-source assistance files retain the visual/transcription evidence. The partially written CS010 `.xhtml` file is failed-assistance evidence and was not used.

No product extraction or Requirement metric has been computed by this task. These artifacts provide frozen source references for a subsequent measurement; they do not establish a PASS.
