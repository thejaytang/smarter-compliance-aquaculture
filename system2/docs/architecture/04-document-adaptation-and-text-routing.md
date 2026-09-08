# Document Adaptation and Text Routing

## Objective

Before formal parsing, build a `DocumentProfile` from lightweight statistics across the complete PDF, then choose the primary text source for each page. Stable layouts in regulations, standards and general rules become parsing constraints, while reliable native text avoids redundant, costly OCR that could introduce errors.

## Fixed workflow

```text
Native-object extraction across the complete PDF
  ↓
Whole-document Document Profile Learning
  ↓
Per-page Text Layer Assessment
  ├── native
  ├── native_with_visual_fallback
  └── ocr
  ↓
Layout Detection
  ↓
Template-Guided Repair
  ↓
Type-specific parsing, cross-page assembly and quality gates
```

## Lightweight whole-document learning

This is not large-model training and does not modify recognition-model parameters. Extract interpretable, reproducible document statistics:

- Header/footer positions, repetition, odd/even-page differences and chapter changes.
- Column positions, headings and geometry of repeated key tables such as `Indicator / Requirement`.
- Clause numbering, list markers, indentation hierarchy and adjacent-number continuity.
- Sentence-ending punctuation, page-break text continuity and cross-page table column counts/centres.

Use these features for repair candidates and anomaly detection. Missing numbers, missing full stops or changing column counts trigger inspection only; patterns must never invent source content.

## Per-page text routing

Inspect native word/character counts, abnormal-character ratios, bbox validity and embedded bitmap counts:

- `native`: complete, reliable native text. Proceed directly to layout and structure parsing; leave `ocr_text` empty.
- `native_with_visual_fallback`: reliable native body text with photos, flowcharts or other visual regions. Apply OCR or image parsing only to relevant crops.
- `ocr`: missing/corrupt native text or invalid positioning evidence. Use full-page OCR and retain abnormal native evidence for audit.

Allow block-level upgrades so individual figures, formulas or abnormal tables on native pages can receive visual parsing. Record decisions/reasons in `raw/text-routing.json` and the actual OCR backend in `raw/ocr-manifest.json`.

## Quality boundaries

- Routing chooses evidence sources, not final structure.
- Never copy native text into `ocr_text` as purported independent visual evidence.
- Templates may correct types or boundaries supported by existing text and geometry; they must not generate missing content.
- When templates conflict with local evidence, use provenance-complete local evidence and require review.
- Inconsistent cross-page table columns, abnormal clause numbering and critical sentence-ending anomalies must not pass silently.

## Historical ASC pages 6–28 validation

- All 511 pages contributed to Document Profile Learning.
- Of 23 target pages, 20 used `native`, three used `native_with_visual_fallback`, and none required full-page OCR.
- The three mixed pages were covers or contained flowcharts; flowchart crops received separate Tesseract block OCR.
- Learning found 294 `Indicator / Requirement` instances; `1.2.1` was restored as one table.
- Automatic coverage and provenance-anchor coverage were both 1.0, with no validation errors, completeness failures or critical reviews.
- Seven warnings were retained for human verification; unsupported automatic merges were not performed.
