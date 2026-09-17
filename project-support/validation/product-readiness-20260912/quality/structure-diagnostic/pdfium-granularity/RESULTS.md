# PDFium character and font evidence feasibility

**FEASIBLE on one frozen development page, without Docling.** The existing installed PDFium backend exposes character boxes, font names and font sizes that the current adapter already partly reads but then discards. A single native evidence dump of Farm original page 28 (zero-based 27; derivative page 0 of the frozen run-2 window) completed in **0.0785 seconds**, including the package import. No product code was modified and no document outside this fixed page was analyzed.

## Measured evidence and reconstruction

| Dimension | Existing frozen PDFium adapter | Character-evidence experiment |
| --- | ---: | ---: |
| `text_lines` | 30 | Same 30 texts and bounding boxes exactly |
| Records labelled `word` | 30 whole-line fragments | 173 non-whitespace partitions with source-character indices |
| Character records | 0 | 1269, including 53 PDFium-generated records |
| Non-whitespace characters with geometry | Not retained independently | 1070/1070 |
| Non-whitespace characters with font name | Not retained | 1070/1070 |
| Non-whitespace characters with positive font size | Not retained | 1070/1070 |
| Unicode map errors reported by PDFium | Not retained | 0/1269 |

Every raw character index is retained and accounted for by line members, newline indices or the existing adapter's discarded/whitespace cases. Concatenating per-character text exactly reproduces `get_text_range()` for this page. Reconstructed line text **and bbox** match the frozen production evidence exactly. Each line's words and separators concatenate to its unchanged raw text; all non-whitespace text is preserved. These invariants prove preservation within PDFium's own evidence on this page, not independent source recall or language-aware word accuracy.

## Local interfaces verified

Installed `pypdfium2` version and exact local helper/raw-binding hashes are in [freeze.json](freeze.json). No web lookup, dependency installation or full Docling import was required.

| Interface | Use and limitation |
| --- | --- |
| `PdfTextPage.count_chars()`, `get_charbox(i)` | Existing helper, real glyph box in PDF left/bottom/right/top coordinates; convert using actual page height to current top-origin model |
| `get_text_range(i, 1)` | Retains the adapter's current text interpretation; helper documentation warns about UCS-2 and inserted/excluded characters |
| `FPDFText_GetUnicode`, `FPDFText_GetTextIndexFromCharIndex` | Preserve raw codepoint and character-to-text index mapping separately; do not assume one character index always equals one returned string character |
| `FPDFText_IsGenerated`, `FPDFText_HasUnicodeMapError` | Preserve generated-character and mapping-error flags; generated layout separators are not independent printed glyphs |
| `FPDFText_GetFontSize`, `FPDFText_GetFontInfo`, `FPDFText_GetFontWeight` | Verified local raw bindings return typography; the font-info buffer is sized by its first return value, with raw bytes and returned lengths retained |
| `FPDFText_GetTextObject`, `FPDFTextObj_GetTextRenderMode` | Available native rendering mode; not a reliable test for text occluded later by images or shapes |

The existing adapter's `_extract_pdfium_positioned` already iterates over every character and reads `get_charbox`, then reduces them to line fragments and duplicates those fragments into `NativePage.words`. It discards character records and leaves fonts empty. This is a granularity loss in the adapter, rather than a missing installed backend capability.

## Smallest useful reuse proposal

1. Retain `NativePage.text_lines` text, geometry and order exactly, adding genuine per-character evidence in `NativePage.characters`. Existing `NativeObject` already has `font_name`; no new business schema is needed for that evidence. Keep raw character-index mappings/generated flags and font size in the native evidence artifact until their durable contract is explicitly defined. `NativeObject` currently has no `font_size` field.
2. Create source-preserving word partitions within each existing line, with stable source-character ranges and retained whitespace, and use those narrower boxes where code actually needs words. The present `_pdf_tables` assigns `page.words` by cell-center geometry, so whole-line pseudo-words can put multiple cells' content into a single cell. This is the first concrete consumer worth a bounded adapter experiment. It does **not** fix table-boundary/grid detection by itself.
3. Preserve the current material text path (`page.text_lines or page.words`) while evaluating the new word evidence separately. The legacy `native_analysis_page` and Requirement hierarchy profiler also consume `page.words`; changing the shared adapter is therefore not risk-free. Require fixed-DEV text/ordering/table and relevant legacy regression checks before enabling it broadly. Do not activate `native_spacing.coalesce` by inventing a font-resource key from a display font name.

No product edit or downstream table/heading experiment was performed. General heading, table, order and word-accuracy gains remain **UNMEASURED**. The next useful check is a separately authorized isolated adapter that supplies the preserved characters/word geometry to the existing table consumer and compares fixed DEV outputs before any production promotion.

## Visibility and generalization limits

The known covered Criterion line still carries a plausible bold font, positive font size and ordinary native text-render mode. See [occluded-text-caution.json](occluded-text-caution.json). These values must not promote it to a verified heading. Native character geometry/font data is additional evidence from the same engine, not an independent visual source check.

Whitespace partitioning is a conservative feasibility mechanism. It is not a general tokenizer for CJK, ligatures, writing direction, rotated text, superscripts, inserted/excluded characters or mixed scripts. This page's exact reconstruction does not validate those cases. No existing Gold, denominator or reserved sample was modified or used for tuning.

Evidence: [summary.json](summary.json), [complete character evidence](character-evidence.json), [line/word partitions and invariants](line-word-partition.json), [reproducible probe](probe.py), and [freeze and fingerprints](freeze.json). All frozen input, source/config and dependency-file hashes checked after the run remained unchanged.
