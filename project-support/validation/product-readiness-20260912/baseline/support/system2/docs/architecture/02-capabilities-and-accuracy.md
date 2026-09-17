# Phase Two: Capability Completion and Accuracy Improvement

## 1. Objective

Build on [phase one](01-core-parsing-workflow.md), advancing from runnable parsing to evidence of which results are reliable and explicit interception of unreliable content.

Core additions:

```text
Page completeness detection
+ token/span evidence alignment
+ cross-page text and table assembly
+ table fallback routing
+ high-risk conflict detection
+ precision review
+ abstention / review queue
+ internal Gold Set and accuracy evaluation
```

## 2. Inherited foundation

Retain all phase-one contracts:

- Directory structure, ID rules and coordinate system.
- The `block` / `segment` data model.
- Native, OCR, review and resolved content layers.
- `has_linked_content` and `content_links`.
- The default `docling-parse`, `pypdfium2`, `PP-DocLayoutV3`, `PP-OCRv6` and `PP-TableMagic` pipeline.
- Canonical JSON, Markdown and quality reports.

Extend model fields and processors without introducing incompatible data formats.

## 3. Accuracy modules

### 3.1 Page completeness gate

Add `PageCompletenessReport`:

```json
{
  "page_index": 12,
  "native_object_count": 842,
  "assigned_native_object_count": 835,
  "unassigned_native_object_count": 7,
  "detected_block_count": 18,
  "unexplained_visual_regions": [],
  "duplicate_regions": [],
  "status": "review_required"
}
```

Check:

- Coverage of native glyphs, images and vectors by blocks.
- Visual content regions missing from the Canonical model.
- Duplicate bboxes, repeated text or overlapping extraction.
- Unexplained differences between page rendering and structured reconstruction.
- Agreement among input, rendered, parsed and exported page counts.

The completeness gate must detect content missed by both native extraction and OCR.

### 3.2 Token/span evidence

Add:

```json
{
  "span_id": "span_027_014",
  "block_id": "paragraph_027",
  "native_text": "0.01",
  "ocr_text": "0.1",
  "review_text": "0.01",
  "resolved_text": "0.01",
  "bbox": [120, 240, 154, 256],
  "criticality": "numeric",
  "resolution_status": "resolved",
  "confidence": 0.99
}
```

Align native and OCR tokens spatially, by character and by sequence. Every number, date, unit, clause number, negation and comparison symbol requires span-level evidence.

### 3.3 Complete conflict detection

Add conflict types:

```text
critical_numeric_conflict
unit_conflict
date_conflict
section_reference_conflict
negation_conflict
modality_conflict
comparison_operator_conflict
missing_content_conflict
general_text_conflict
```

Every conflict result includes:

- Conflicting spans and bboxes.
- Separate native, OCR and review values.
- Severity.
- Current decision status.
- Triggered rules and model versions.

### 3.4 Abstention and review queue

Explicitly allow:

```json
{
  "resolved_text": null,
  "resolution_status": "ambiguous",
  "requires_human_review": true
}
```

Fixed statuses:

```text
resolved
ambiguous
unreadable
human_confirmed
```

If a high-risk conflict has not met the automatic decision threshold, do not force a `resolved_text` value.

### 3.5 precision review

Use `PaddleOCR-VL-1.6` by default in `conflicts_only` mode.

Inputs:

- Original block or cell crop.
- Enlarged crop of the conflicting span.
- `native_text` and `ocr_text`.
- Bounded preceding and following context.
- Structured prompts that prohibit polishing, inference and invented completion.

The output is a third evidence source only. Persistent disagreement or below-threshold model confidence requires human review.

## 4. Document-level structure completion

### 4.1 Cross-page text

Implement `paragraph_assembler` using:

- Page-bottom and page-top positions.
- Syntactic completion.
- Font, font size, indentation and column position.
- Changes in headings, lists and clause numbering.
- Hyphenation, punctuation and case continuity.

Use two thresholds:

```text
Above auto_merge_threshold
→ merge automatically

Between review_threshold and auto_merge_threshold
→ create a candidate and route it to the review queue

Below review_threshold
→ retain separate blocks
```

### 4.2 Cross-page tables

Implement `table_assembler`:

- Determine whether adjacent fragments belong to one logical table.
- Compare column count, centres, widths and total table width.
- Detect repeated headers on the next page and deduplicate the Canonical table.
- Determine whether the next page's first row continues the previous page's last row.
- Merge cell graphs while preserving every original fragment.
- Record `removed_repeated_headers`, `joined_rows` and confidence.

Do not merge automatically when:

- A new table has its own number or index.
- Column structure changes substantially.
- A new heading separates the fragments.
- Units, fields or semantic structure change materially.

### 4.3 Table fallback routing

Retain `PP-TableMagic` as the default:

```text
Complex merged cells or unclear borders
→ gmft / Table Transformer

Regular structure with clear borders
→ img2table

Correct structure but conflicting text
→ upgrade OCR for the affected cells only
```

Map every parser's result to the common `Table` and `TableCell` models.

## 5. Links and object completion

### 5.1 content links

Improve:

- Explicit numbered references.
- Deictic references such as `the table below` and `the following figure`.
- One body block referencing multiple objects.
- Multiple body blocks referencing one object.
- Review routing for low-confidence inferred links.

### 5.2 Index and note

Retain the top-level fields:

```text
index
note
```

Do not restore a separate `source` field. Inferred roles may be stored in `note_spans` for downstream use without changing the user-approved simplified data model.

### 5.3 figure OCR

Add optional `figure_ocr`, storing image text only in `derived.embedded_text`. Visual inferences must not enter body text or `resolved_text` in this phase.

## 6. Internal Gold Set and evaluation

Build a Gold Set representing actual target documents:

- Born-digital, scanned and mixed text layers.
- Single-column, multi-column and spanning headings.
- Single-page, borderless, merged-cell and page-spanning tables.
- Multilevel clauses, footnotes, annexes and cross-references.
- Numbers, units, dates, negations and comparison symbols.

Core metrics:

```text
CER / WER
High-risk span exact match
block omission rate
block-type F1
heading hierarchy F1
cross-page merge precision / recall
cell exact match
row/column span F1
critical conflict recall
accepted-result precision
automatic coverage
```

Model changes must respond to error categories in the internal Gold Set, not a single public benchmark ranking.

## 7. Additional modules

```text
src/pdf_extraction/
├── assemble/
│   ├── document_assembler.py
│   ├── hierarchy.py
│   ├── paragraph_assembler.py
│   ├── table_assembler.py
│   └── content_linker.py
├── reconcile/
│   ├── span_aligner.py
│   ├── conflict_detector.py
│   ├── precision_review.py
│   └── resolver.py
├── validate/
│   ├── completeness_gate.py
│   ├── schema_validator.py
│   └── quality_gate.py
└── models/
    ├── evidence_span.py
    ├── conflict.py
    └── review.py
```

## 8. Completion criteria

1. Page completeness reports detect unassigned content and suspected omissions.
2. High-risk characters retain span-level bboxes and three evidence channels.
3. Unresolved content permits `resolved_text = null`.
4. Cross-page paragraphs and tables use two-threshold decisions.
5. Header deduplication and split-row joining preserve reversible operation records.
6. Table fallbacks map to the common cell graph.
7. Every critical conflict is resolved, confirmed by a human or blocks document acceptance.
8. Gold evaluation reports break results down by document and error type.
9. Regression tests prevent deterioration in critical fields, tables and cross-page accuracy.

Completion establishes a high-accuracy target-domain parser that can abstain and supports audit.
