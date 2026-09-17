# Phase One: Core Requirements and Functional Pipeline

## 1. Objective

Implement the first runnable, verifiable PDF parsing pipeline:

```text
PDF
→ preflight
→ page rendering and native text extraction
→ layout detection
→ OCR
→ basic block construction
→ Canonical JSON
→ structural validation
→ Markdown + quality report
```

The completed phase should process mostly born-digital regulatory, standard and report PDFs with conventional layouts, reliably converting text, single-page tables and figures into structured documents with page and coordinate evidence.

This phase does not aim to handle every complex PDF. Acceptance requires a complete main pipeline, correct data structures, traceable results and repeatable execution on representative PDFs.

## 2. Inputs and outputs

Inputs:

- Local PDF files.
- Per-document run configuration.

Required outputs:

```text
outputs/<document_id>/
├── canonical.json
├── document.md
├── quality-report.json
├── pages/
├── crops/
├── figures/
└── raw/
```

Output roles:

- `canonical.json` is the sole structured source of truth.
- `document.md` is a human-readable derivative of the Canonical model.
- `quality-report.json` records page/block counts, unassigned objects, low-confidence results and structural validation status.
- Preserve page renders, block crops and native objects as evidence.

## 3. Implementation scope

### 3.1 Document preflight

Implement:

- File hash, page count, PDF version and encryption status.
- Page dimensions, rotation and blank-page detection.
- Native-text and image coverage per page.
- Basic classification of born-digital, scanned and mixed pages.
- Reconciliation of input and completed page counts.

### 3.2 PDF object extraction and page rendering

Defaults:

- `docling-parse` extracts native characters, words, lines, bboxes, fonts, paths and bitmaps.
- `pypdfium2` generates page renders and block crops.

Common coordinate convention:

```json
{
  "bbox": [0, 0, 100, 50],
  "coord_origin": "top_left",
  "page_index": 0
}
```

### 3.3 Layout detection

Use `PP-DocLayoutV3` by default.

Supported block types:

```text
heading
paragraph
list
table
figure
header
footer
unknown
```

Deduplicate bboxes, align native objects and recover local page order. Complex multi-column hierarchy may receive low confidence, but its content must be retained.

### 3.4 Text recognition

Every text block preserves:

```json
{
  "native_text": "...",
  "ocr_text": "...",
  "review_text": null,
  "resolved_text": "..."
}
```

Use `PP-OCRv6` by default. This phase implements a basic resolution policy only:

```text
native and OCR agree
→ use the agreed result

native is usable; OCR is empty or clearly poor quality
→ use native and record evidence status

native is missing; OCR is usable
→ use OCR

a high-risk conflict exists between them
→ mark review_required; do not declare automatic acceptance
```

### 3.5 Basic hierarchy

Implement:

- An ordered `document → section → block` tree.
- `parent_id`、`children`、`order_in_parent`.
- Basic heading-level classification.
- Header/footer detection, excluded from Markdown body text by default.
- Within-page list and paragraph order recovery.

### 3.6 Single-page tables

Use `PP-TableMagic` by default.

Implement:

- Table bbox and crop.
- Basic rows, columns, cells, row spans and column spans.
- Cell text.
- Basic `index` and `note` binding for single-page tables.
- Markdown table rendering from the cell graph.

Do not automatically merge page-spanning tables in this phase. Suspected continuation from a page bottom to the next page top remains two fragments and is recorded in the quality report.

### 3.7 Figures

Implement:

- Preserve high-resolution original-image crops.
- Bind `index` and `note`.
- Add each figure as an independent `figure` block in the document tree.
- Create `content_links` for explicit body references such as `Figure 2` or `Fig. 2`.

Image semantic interpretation and intra-image relationship extraction remain disabled.

### 3.8 Canonical JSON

Implement stable Pydantic models and JSON Schema:

```text
Document
Page
Block
Segment
TextContent
Table
TableCell
ContentLink
Quality
ProcessingMetadata
```

Required information:

- `document_id`, file hash and pipeline metadata.
- `page_index`, bbox and crop reference.
- Separate `block` and `segment` representations.
- Native, OCR, review and resolved field layers.
- `has_linked_content` and `content_links`.
- Model name, model version and configuration hash.

### 3.9 Validation and basic quality reporting

Required checks:

1. Input page count equals processed page count.
2. All IDs are unique.
3. The document tree is acyclic.
4. Every referenced ID exists.
5. Bboxes and `page_index` values are valid.
6. `has_linked_content == bool(content_links)`.
7. Every exported block has at least one segment.
8. High-risk conflicts enter `review_required`.

## 4. Explicitly deferred capabilities

Later phases implement:

- Automatic page-spanning table merging and repeated-header deduplication.
- A complete cross-page paragraph classifier.
- Token/span text alignment.
- Visual page-completeness differences.
- `PaddleOCR-VL-1.6` precision review。
- Table-parser fallback routing.
- Inferred `content_links`.
- Image semantics and dedicated code/formula parsers.
- Regulatory IR, ontology, RAG chunks and review interfaces.

These boundaries do not prevent end-to-end execution. For unsupported pages or blocks, preserve evidence and return `unknown`, `review_required` or unmerged fragments.

## 5. Implementation modules

```text
src/pdf_extraction/
├── ingest/
│   ├── preflight.py
│   ├── native_extractor.py
│   └── renderer.py
├── layout/
│   ├── detector.py
│   ├── aligner.py
│   └── reading_order.py
├── parsers/
│   ├── text.py
│   ├── table.py
│   └── figure.py
├── models/
│   ├── document.py
│   ├── block.py
│   ├── segment.py
│   └── table.py
├── validate/
│   ├── schema_validator.py
│   └── quality_gate.py
├── export/
│   └── markdown.py
└── pipeline.py
```

## 6. Test materials

Prepare at least:

- Two born-digital regulatory PDFs with conventional layouts.
- One report containing single-page tables and figures.
- One scanned or mixed-text-layer PDF.
- One deliberately abnormal test PDF with unusual, blank or rotated pages.

Manually record:

- Page counts and expected block counts.
- Heading and paragraph order.
- Key numbers, units and dates.
- Table row/column counts and key cells.
- Figure counts and captions.

## 7. Completion criteria

All criteria must hold:

1. One command generates the complete output directory from a PDF.
2. Repeated runs produce structurally equivalent results.
3. Canonical JSON passes schema validation.
4. Pages, blocks and segments trace back to the original PDF.
5. Markdown is generated only from the Canonical model.
6. Test documents have no silently omitted pages.
7. High-risk native/OCR conflicts are not silently accepted.
8. Single-page tables and figures can be exported as independent blocks.
9. Automated tests cover core models, IDs, coordinates, references and export logic.

Completion establishes a runnable core parser. Real PDFs can then expose the error distribution and provide the phase-two baseline.
