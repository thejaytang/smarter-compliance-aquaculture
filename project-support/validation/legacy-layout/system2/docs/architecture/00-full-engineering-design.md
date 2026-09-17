# Complete PDF Parsing Engineering Design

## 1. Positioning

An **Evidence-Preserving Hierarchical Block Parser** for legislation, standards, regulatory documents and complex reports.

The objective is an auditable, reconstructable **Canonical JSON document model** for downstream software/AI processing, beyond PDF-to-Markdown conversion. Markdown, HTML, XML, RAG chunks, Regulatory IR and ontology are derived views, not independent truth sources.

The system must:

1. Recover section hierarchy and local reading order.
2. Represent text, tables, figures, code and other content as independent logical blocks.
3. Preserve each logical unit's source page, coordinates and image evidence through physical segments.
4. Retain native, OCR and optional model-review text without overwriting original evidence.
5. Reconstruct page-spanning paragraphs/tables, repeated headers and split rows at document level.
6. Express text-to-figure/table/code relationships through `has_linked_content` and `content_links`.
7. Explicitly detect conflicts in high-risk numbers, units, dates, negation, modality and comparison symbols.
8. Record operations, model versions, confidence and source locations for every automatic correction.

Mapping printed labels to physical pages is outside the current core problem. Preserve `page_index` as the zero-based physical PDF page index actually used by the parser. A future independent `page_label` may support display without changing existing structure.

---

## 1.1 Implementation phases and document relationships

This document defines the authoritative complete architecture and final data model. Implementation has three cumulative phases:

1. [Phase one: core functional pipeline](01-core-parsing-workflow.md)  
   Establish the minimum complete flow from PDF to Canonical JSON, Markdown and quality reports.
2. [Phase two: capability and accuracy completion](02-capabilities-and-accuracy.md)  
   Extend phase one with cross-page structure, difficult tables, omission checks, detailed conflicts and abstention.
3. [Phase three: complete product](03-complete-product-implementation.md)  
   Add all block types, downstream Regulatory IR/ontology, review interfaces and production capabilities.

All phases share IDs, coordinates, block/segment conventions and the Canonical model. Later phases add fields, processors and quality requirements without overturning earlier outputs. Completing phase three implements this design in full.

---

## 2. Overall architecture

```text
PDF file
  ↓
Safety preflight + whole-document native-object extraction
  ↓
Document Profile Learning
  ├── Header/footer and odd/even-page templates
  ├── Repeated layout and key-table templates
  ├── Numbering, indentation and list-marker patterns
  └── Sentence-ending, cross-page and column statistics
  ↓
Per-page text-evidence routing
  ├── native
  ├── native_with_visual_fallback
  └── OCR
  ↓
On-demand rendering + layout detection and initial block segmentation
  ↓
Align native text, fonts and coordinates with visual blocks
  ↓
Template-Guided Repair
  ↓
Dispatch type-specific block parsers
  ├── heading / paragraph / list / footnote
  ├── table
  ├── figure
  ├── code
  ├── equation
  └── unknown
  ↓
Within-page structural correction and local ordering
  ↓
Document-level assembly
  ├── Section-tree reconstruction
  ├── Cross-page text merging
  ├── Cross-page table merging
  ├── Repeated-header deduplication
  ├── Split-row joining
  ├── Index/note binding
  └── Content-link construction
  ↓
Native/OCR conflict detection
  ↓
Optional precision review
  ↓
Resolved-content decisions
  ↓
Canonical JSON
  ↓
Derived Markdown / HTML / XML / RAG / Regulatory IR / ontology outputs
```

Two evidence channels are selected through intake assessment:

- **Native channel**: characters, fonts, coordinates, paths, bitmaps, bookmarks and other PDF objects.
- **Visual channel**: layout from renders; OCR, table reconstruction and image interpretation for scanned/abnormal pages and independent visual regions.

Route per page, allowing block-level upgrades. Reliable born-digital pages avoid full-page OCR; scans use visual OCR; mixed pages retain native body text with targeted visual evidence. Align/compare channels at block level without presenting native text as OCR evidence.

---

## 3. Default technology stack

| Module | Default component | Main output | Alternatives if quality is insufficient |
|---|---|---|---|
| PDF object extraction | `docling-parse` | Characters, words, lines, bboxes, paths, bitmaps, outline | `PyMuPDF` or PDFium-based extractor |
| Rendering | `pypdfium2` | Pages and high-resolution region crops | `docling-parse` or `PyMuPDF` renderer |
| Layout | `PP-DocLayoutV3` | Block types, bboxes and confidence | Docling layout; MinerU layout |
| General OCR | `PP-OCRv6` | Text, character/word boxes and confidence | PaddleOCR-VL-1.6; language-specific OCR |
| Tables | `PP-TableMagic` | Structure, HTML and cell content | `gmft` / Table Transformer; `img2table` for ruled tables |
| Difficult-block review | `PaddleOCR-VL-1.6` | Visually contextualised block results | OvisOCR2; MinerU2.5-Pro; hosted OCR/VLM permitted by data policy |
| Rules and structure | Python rules | Merge, deduplication, links, conflicts and decisions | Precision review for low-confidence samples |
| Validation | `Pydantic` + JSON Schema | Structure and field constraints | `jsonschema` |
| Downstream ontology | RDFLib + `pySHACL` | RDF mapping and SHACL checks | Compatible triple store or SHACL engine |

Maintain one default engineering pipeline. Compare alternatives only when their module misses internal acceptance thresholds.

---

## 4. Core data model

### 4.1 Ordered document hierarchy

Represent structure as an ordered tree:

```text
Document
├── Section
│   ├── Heading
│   ├── Paragraph
│   ├── Table
│   ├── Paragraph
│   └── Figure
└── Section
```

`parent_id` and parent `children` express containment. `children` and `order_in_parent` express local order. Do not maintain another permanent complex reading-order graph.

Initial page parsing still identifies columns, spanning headings, sidebars and footnotes; retain stable local order and auditable ordering operations in the final model.

### 4.2 Separate logical blocks from physical segments

A block is a complete semantic unit; a segment is its physical region on one page. A block may have one or several segments:

```text
Logical Block
├── Segment on page 12
└── Segment on page 13
```

Do not encode cross-page state with a single `0 / 1 / 2` category:

- One segment denotes one continuous physical region.
- Multiple segments represent page, column or region spans.
- Segment order defines internal assembly order.
- Every segment retains its own page, coordinates, text range and image reference.

### 4.3 Block types

Supported `block.type` values:

```text
document
section
heading
paragraph
list
list_item
table
figure
code
equation
footnote
header
footer
unknown
```

Type roles:

- `heading`, `paragraph`, `list`, `list_item` and `footnote` are text blocks.
- `table`, `figure`, `code`, `equation` and `unknown` are composite blocks.
- `header` and `footer` preserve marginal evidence and are excluded from body exports by default.
- `unknown` preserves objects the taxonomy cannot reliably classify.

### 4.4 Canonical document root

```json
{
  "schema_version": "1.0",
  "document_id": "sha256:...",
  "source": {
    "file_name": "regulation.pdf",
    "file_hash": "...",
    "page_count": 48,
    "parser_page_index_origin": 0
  },
  "processing": {
    "started_at": "2026-08-24T10:00:00Z",
    "pipeline_version": "...",
    "config_hash": "...",
    "models": []
  },
  "pages": [],
  "root_block_ids": [],
  "blocks": {},
  "conflicts": [],
  "review_queue": [],
  "quality": {},
  "artifacts": {}
}
```

Store `blocks` in a table keyed by `block_id` to avoid duplicating objects within a deep tree. Build hierarchy through `parent_id` and `children` for references, modification and validation.

### 4.5 Common block structure

```json
{
  "id": "paragraph_027",
  "type": "paragraph",
  "parent_id": "section_004",
  "children": [],
  "order_in_parent": 6,
  "segments": [
    {
      "id": "segment_027_01",
      "page_index": 12,
      "bbox": [72.0, 680.0, 520.0, 790.0],
      "coord_origin": "top_left",
      "text_range": [0, 83],
      "crop_ref": "crops/paragraph_027_01.png",
      "native_object_refs": ["glyph_183", "glyph_184"]
    },
    {
      "id": "segment_027_02",
      "page_index": 13,
      "bbox": [72.0, 80.0, 520.0, 146.0],
      "coord_origin": "top_left",
      "text_range": [83, 151],
      "crop_ref": "crops/paragraph_027_02.png",
      "native_object_refs": ["glyph_185", "glyph_186"]
    }
  ],
  "content": {
    "native_text": "...",
    "ocr_text": "...",
    "review_text": null,
    "resolved_text": "...",
    "resolution": {
      "selected_source": "native",
      "reason": "native_ocr_agree",
      "confidence": 0.998
    }
  },
  "has_linked_content": true,
  "content_links": [
    {
      "target_id": "table_003",
      "anchor_text": "Table 3",
      "link_type": "explicit",
      "relation": "references",
      "confidence": 1.0,
      "evidence_segment_ids": ["segment_027_01"]
    }
  ],
  "quality": {
    "layout_confidence": 0.97,
    "native_text_confidence": 0.99,
    "ocr_confidence": 0.96,
    "structure_confidence": 0.95,
    "requires_review": false
  },
  "operations": []
}
```

`has_linked_content` and `content_links` are a fixed pair:

- `has_linked_content` explicitly indicates linked figures, tables, code, formulas or other content.
- `content_links` records targets, anchors, relationships, confidence and evidence locations.
- Enforce `has_linked_content == (len(content_links) > 0)` in schema validation.

### 4.6 Text-evidence fields

Every readable block/cell uses four content layers:

```text
native_text   Evidence from internal PDF text objects
ocr_text      Evidence from visual page recognition
review_text   Optional precision-review output
resolved_text Text selected by the system
```

Only explicit resolution policy may generate `resolved_text`; it cannot overwrite other evidence layers. Model corrections belong in `review_text` and `operations`.

---

## 5. Processing workflow

### 5.1 Preflight and document profiling

First compute the file hash and record:

- PDF version, page count, size and encryption.
- Page dimensions, rotation, extreme sizes and blank pages.
- Per-page native-text/image coverage and character encoding quality.
- Availability of fonts, `ToUnicode`, outline and tag tree.
- Attachments, JavaScript and external links.
- Born-digital, scanned or mixed classification.

Preflight produces per-page `page_profile`. Learn a document profile from all native objects to identify repeated margins, odd/even variants, chapter changes, key tables, numbering, indentation, list markers, sentence endings and cross-page columns. It supplies constraints/candidates/anomalies only, never absent text.

Default routes:

```text
Normal native-text coverage, reliable encoding and valid bboxes
→ native; use native text without full-page OCR

Reliable native text with embedded bitmaps or separate visual regions
→ native_with_visual_fallback; native body plus targeted visual recognition

Missing, corrupt, displaced or abnormally sparse native text
→ full visual OCR, retaining abnormal native evidence

Rotated, distorted or low-resolution pages
→ preprocess before the visual channel
```

Route per page, not once per file. One PDF may mix born-digital, scanned and mixed pages. Local evidence conflicts may still trigger block OCR or review.

### 5.2 Rendering and native-object extraction

`docling-parse` extracts:

- Characters, words and lines.
- Bboxes, fonts, sizes, weights and character mappings.
- Paths, vectors and bitmaps.
- Outline and available PDF structure.

`pypdfium2` provides:

- Standard page renders.
- High-resolution crops from block bboxes.
- Common visual inputs for tables, figures and precision review.

Convert every coordinate to:

```json
{
  "bbox": [x0, y0, x1, y1],
  "coord_origin": "top_left",
  "page_width": 595.0,
  "page_height": 842.0
}
```

Preserve render DPI, colour space and renderer version for reproducibility.

### 5.3 Layout and initial segmentation

Use `PP-DocLayoutV3` by default, producing:

```json
{
  "label": "paragraph",
  "bbox": [72, 181, 516, 234],
  "confidence": 0.97
}
```

Layout establishes initial structure, not final hierarchy. Reassess using content, numbering, fonts, adjacent blocks and cross-page context.

Steps:

```text
Visual page detection
→ bbox deduplication and overlap resolution
→ native-object spatial alignment
→ block-type mapping
→ initial within-page order
→ content recognition
→ hierarchy and order correction
```

Detect columns before ordering within them; spanning headings precede their columns. Retain ordering in `order_in_parent` and assembly-operation records only.

### 5.4 Aligning native text with blocks

Assign native characters/words using:

1. Bbox intersection ratios and character centres.
2. Prefer smaller, semantically specific bboxes for objects matching multiple blocks.
3. Record `unassigned_native_objects`; never discard them silently.
4. Recover internal order from coordinates, text direction and column structure.
5. Preserve original object IDs so `native_text` traces to glyphs/words.

Substantial mismatch between native objects and visual locations lowers `native_text_confidence` and prioritises OCR for that block.

### 5.5 Text-block parsing

`heading`, `paragraph`, `list`, `list_item` and `footnote` support both `native_text` and `ocr_text`, subject to the evidence-routing policy above.

Text processing includes:

- Unicode normalisation with original strings preserved.
- Visual line-break recovery.
- Cross-line hyphen joining with recorded operations.
- List-marker, clause-number and indentation recognition.
- Initial heading levels and document-level correction.
- Repeated-header/footer detection and type labels.

Body text does not absorb tables, figures, code or their index/note. They remain independent blocks connected through `content_links`.

### 5.6 Table parsing

Use `PP-TableMagic` by default to reconstruct a full cell graph rather than merely a Markdown table:

```json
{
  "id": "table_003",
  "type": "table",
  "index": "Table 3. Applicable limits",
  "note": "Values are measured at standard temperature.",
  "segments": [],
  "table": {
    "row_count": 5,
    "column_count": 4,
    "cells": [
      {
        "id": "table_003_cell_000",
        "row": 0,
        "column": 0,
        "row_span": 2,
        "column_span": 1,
        "bbox": [74, 211, 180, 254],
        "content": {
          "native_text": "Category",
          "ocr_text": "Category",
          "review_text": null,
          "resolved_text": "Category"
        },
        "is_header": true
      }
    ]
  },
  "assembly": null,
  "quality": {}
}
```

External table titles are `index`. Explanations, source notes and supplementary text below a table are `note`, without separate caption/source_note categories in the current model.

Preserve for each cell where possible:

- `row`、`column`、`row_span`、`column_span`.
- Cell bbox and owning segment.
- Native/OCR/review/resolved text layers.
- Header status and structural confidence.

When the default parser is insufficient, route by issue type:

```text
Complex merged cells or unclear borders
→ gmft / Table Transformer

Conventional regular tables with clear borders
→ img2table

Correct structure but conflicting text recognition
→ retain structure; upgrade cell OCR or precision review only
```

### 5.7 Cross-page table assembly

A dedicated `table_assembler` merges adjacent-page fragments using:

- Previous fragment near page bottom and next fragment near page top.
- Matching index/number, or absence of a new index on the next page.
- Consistent column count, centres, width ratios and total width.
- Repeated header text.
- Continuation of the last row into the next page's first row.
- Consistent fonts, borders, backgrounds and cell structure.

After identifying one logical table:

```text
Preserve every original fragment
→ remove repeated headers from Canonical table content
→ join page-split rows or cells
→ merge cell graphs
→ create one logical table
→ record every assembly operation
```

```json
{
  "assembly": {
    "source_fragment_ids": ["table_fragment_12_01", "table_fragment_13_01"],
    "removed_repeated_headers": [
      {
        "fragment_id": "table_fragment_13_01",
        "row_index": 0
      }
    ],
    "joined_rows": [
      {
        "left_fragment_row": 8,
        "right_fragment_row": 1,
        "result_row": 8
      }
    ],
    "column_alignment_score": 0.98,
    "confidence": 0.96
  }
}
```

Remove repeated headers only from merged Canonical content. Retain original fragments/crops. Merging restores complete content; segments and assembly records preserve page provenance and joining history.

### 5.8 Figure parsing

Preserve figures as independent `figure` blocks:

```json
{
  "id": "figure_004",
  "type": "figure",
  "index": "Figure 4. Risk assessment process",
  "note": "Dashed arrows represent optional steps.",
  "segments": [],
  "image_ref": "figures/figure_004.png",
  "derived": {
    "embedded_text": null,
    "visual_description": null,
    "entities": [],
    "relations": []
  }
}
```

Required processing:

```text
Detect figure bbox
→ generate high-resolution original-image crop
→ bind external title to index
→ bind explanatory text below to note
→ add an independent block to the document tree
```

Optional processing:

- `figure_ocr`: store image text in `derived.embedded_text`.
- `visual_understanding`: generate descriptions, entities and relationships.

Visual-model results belong only to `derived`; do not modify original images or present inference as source evidence.

### 5.9 Code and formulas

Independent `code` blocks preserve:

- Native monospaced-font and indentation evidence.
- Native and OCR text.
- Line numbers, whitespace and line breaks.
- Optional code-language/configuration-format inference.

Recover lines/indentation from native character coordinates, then check characters with `PP-OCRv6`. Character, indentation or special-symbol conflicts trigger full-crop `PaddleOCR-VL-1.6` review.

Equation blocks retain original image, location and surrounding context. Optional LaTeX/structured transcription belongs in `derived`; the image remains source evidence.

### 5.10 Index and note binding

External titles of tables, figures, code and equations are `index`; explanatory text below is `note`.

Binding sequence:

1. Find index/note candidates from layout labels and spatial proximity.
2. Confirm identity using numbering such as `Table 3`, `Figure 4` or `Fig. 2`.
3. Resolve conflicts using fonts, alignment, spacing and column spans.
4. Remove bound index/note from ordinary body flow while preserving original segments and operation history.
5. Keep uncertain candidates as independent blocks in the review queue.

### 5.11 Text and composite-content links

Physical distance does not determine ownership. Layout may separate a figure/table from its reference; `content_links` expresses the relationship.

Prefer rule-based explicit links:

```text
Table 3
Figure 2
Fig. 4
the table below
the following figure
see the code example
```

```json
{
  "target_id": "table_003",
  "anchor_text": "Table 3",
  "link_type": "explicit",
  "relation": "references",
  "confidence": 1.0
}
```

Where numbering is absent but the semantic relationship is clear, allow inferred links:

```json
{
  "target_id": "figure_004",
  "anchor_text": null,
  "link_type": "inferred",
  "relation": "explains",
  "confidence": 0.78
}
```

Inferred links enter Canonical only above the configured threshold; otherwise they remain review candidates. Exporters must never present `link_type = inferred` as an explicit source reference.

### 5.12 Cross-page text and hierarchy

Use `physical segments → logical block` for cross-page text:

```text
Paragraph segment at page bottom
+ continuation segment at next page top
→ one logical paragraph
```

Signals include:

- Missing sentence-ending punctuation/completion on the preceding page.
- Lowercase starts, continuation punctuation or continuous syntax on the next page.
- Consistent fonts, sizes, indentation, columns and line width.
- New headings, numbers or list levels on the next page.
- Language-model assistance only when rule signals conflict.

Rebuild hierarchy in two passes:

1. Initial heading hierarchy from layout, fonts, numbering and indentation.
2. Document-wide checks/correction of numbering, parent-child levels and cross-page context.

Record every merge and hierarchy change in `operations`, for example:

```json
{
  "operation": "merge_cross_page_paragraph",
  "inputs": ["block_12_19", "block_13_01"],
  "output": "paragraph_027",
  "method": "deterministic_rules",
  "confidence": 0.97
}
```

---

## 6. Conflicts and final text decisions

### 6.1 deterministic conflict detector

Compare native/OCR text per block/cell. Apply only meaning-preserving normalisation before comparison, such as Unicode, whitespace and visual line-break normalisation.

Classify conflicts by risk:

```text
critical_numeric_conflict
unit_conflict
date_conflict
section_reference_conflict
negation_conflict
modality_conflict
comparison_operator_conflict
general_text_conflict
missing_content_conflict
```

Prioritise:

- Numbers, decimal marks, thousands separators and percentages.
- Dates, deadlines, versions and clause numbers.
- Units, currencies, chemical and engineering symbols.
- Negations/exceptions such as `not`, `unless` and `except`.
- Modality such as `shall`, `must` and `may`.
- `<`, `≤`, `>`, `≥`, `=` and minus signs.

```json
{
  "id": "conflict_001",
  "block_id": "table_003_cell_042",
  "native_value": "0.01 mg/L",
  "ocr_value": "0.1 mg/L",
  "conflict_type": "critical_numeric_conflict",
  "severity": "critical",
  "status": "review_required",
  "evidence_segment_ids": ["segment_003_02"]
}
```

### 6.2 precision review

Configure precision review as an optional module:

```yaml
precision_review:
  enabled: true
  mode: conflicts_only
```

Supported modes:

```text
off
conflicts_only
high_risk
all
```

Default to `conflicts_only`. Model inputs must include:

- Original block crop.
- `native_text`.
- `ocr_text`.
- Conflict locations and categories.
- Bounded context from adjacent blocks.
- A schema-constrained prompt requiring character-level visual judgement without rewriting.

Model output:

```json
{
  "review_text": "0.01 mg/L",
  "decision": "native",
  "confidence": 0.99,
  "evidence": {
    "visible_token": "0.01",
    "segment_id": "segment_003_02"
  }
}
```

### 6.3 resolution policy

Resolve text in this order:

```text
Native and OCR agree
→ use the agreed result

Only nonsemantic formatting differs
→ use normalised text and record a normalisation operation

Ordinary conflict with substantially stronger evidence on one side
→ select stronger evidence while retaining the conflict

High-risk conflict
→ precision review

Review remains low-confidence or all three disagree
→ require human review rather than silently choosing
```

Every unresolved `critical` conflict blocks the final document quality gate.

---

## 7. Canonical JSON validation

Before output, check structure and consistency:

1. Unique block, segment and conflict IDs.
2. Resolvable parent, child, target and evidence references.
3. An acyclic tree with one structural parent per non-root block.
4. Continuous, nonduplicated `order_in_parent` within each parent.
5. Valid segment page indices and bboxes.
6. Agreement between `has_linked_content` and link count.
7. An explicit `resolution.selected_source` for every resolved text.
8. Valid table coordinates, spans and row/column bounds.
9. All source-fragment references retained after cross-page merging.
10. All unresolved high-risk conflicts in review.
11. Model name, version, configuration hash and runtime for every model output.
12. At least one source-page segment for every exported body block.

On validation failure, preserve intermediate artifacts and produce a failure report without a successful final-document status.

---

## 8. Derived outputs

### 8.1 Markdown / HTML

Render Markdown and HTML from Canonical:

- Emit headings, paragraphs and lists in tree order.
- Render tables from cell graphs, not new guesses from OCR text.
- Use figure `image_ref` with index/note.
- Allow hidden headers/footers and parser metadata.

### 8.2 RAG chunks

Chunk on the Canonical model:

- Use sections and logical blocks as units.
- Do not split tables or page-spanning logical blocks.
- Preserve heading paths, block IDs, page indices and bboxes in chunk metadata.
- Attach content-linked figures/tables as related objects rather than copying them into prose.

### 8.3 Regulatory IR and ontology

When regulatory semantics are enabled, use this fixed chain:

```text
Canonical JSON
→ Regulatory IR
→ schema-constrained fact extraction
→ predefined T-box mapping
→ deterministic RDF generation
→ SHACL validation
→ source-grounded review UI
```

Regulatory facts retain at least:

```json
{
  "regulated_entity": "...",
  "modality": "obligation",
  "action": "...",
  "object": "...",
  "condition": "...",
  "exception": "...",
  "threshold": {
    "value": 10,
    "unit": "mg/L",
    "operator": "<="
  },
  "effective_date": "2026-01-01",
  "cross_references": ["section_005_002"],
  "source_block_ids": ["paragraph_027"],
  "source_segment_ids": ["segment_027_01"]
}
```

Ontology references Canonical blocks/segments; it must not generate unprovenanced facts directly from PDF images.

---

## 9. Run configuration

```yaml
pipeline:
  page_index_origin: 0
  render_dpi: 200
  high_resolution_crop_dpi: 300

native_extraction:
  backend: docling-parse
  preserve_glyph_refs: true
  preserve_paths: true
  preserve_bitmaps: true

layout:
  model: PP-DocLayoutV3
  detect_reading_order: true
  second_pass_hierarchy_rebuild: true

ocr:
  model: PP-OCRv6
  run_on_text_blocks: true
  run_on_table_cells: true
  preserve_word_boxes: true

tables:
  parser: PP-TableMagic
  cross_page_assembly: true
  deduplicate_repeated_headers: true
  join_split_rows: true

figures:
  preserve_original_crop: true
  figure_ocr: false
  visual_understanding: false

content_linking:
  explicit_rules: true
  inferred_links: true
  inferred_link_threshold: 0.85

conflict_detection:
  enabled: true
  critical_tokens: true
  block_unresolved_critical_conflicts: true

precision_review:
  enabled: true
  mode: conflicts_only
  model: PaddleOCR-VL-1.6
  min_confidence: 0.90

outputs:
  canonical_json: true
  markdown: true
  html: false
  rag_chunks: false
  regulatory_ir: false
  ontology: false
```

Options control derived capabilities, not competing architectures. Canonical, original evidence and provenance structure remain consistent across settings.

---

## 10. Engineering structure and module boundaries

```text
pdf-extraction-product/
├── pyproject.toml
├── config/
│   ├── default.yaml
│   └── schemas/
│       ├── canonical-document.schema.json
│       └── regulatory-ir.schema.json
├── src/
│   └── pdf_extraction/
│       ├── ingest/
│       │   ├── preflight.py
│       │   ├── native_extractor.py
│       │   └── renderer.py
│       ├── layout/
│       │   ├── detector.py
│       │   ├── aligner.py
│       │   └── reading_order.py
│       ├── parsers/
│       │   ├── text.py
│       │   ├── table.py
│       │   ├── figure.py
│       │   ├── code.py
│       │   ├── equation.py
│       │   └── unknown.py
│       ├── assemble/
│       │   ├── document_assembler.py
│       │   ├── hierarchy.py
│       │   ├── paragraph_assembler.py
│       │   ├── table_assembler.py
│       │   └── content_linker.py
│       ├── reconcile/
│       │   ├── conflict_detector.py
│       │   ├── precision_review.py
│       │   └── resolver.py
│       ├── models/
│       │   ├── document.py
│       │   ├── block.py
│       │   ├── segment.py
│       │   ├── table.py
│       │   └── conflict.py
│       ├── validate/
│       │   ├── schema_validator.py
│       │   └── quality_gate.py
│       ├── export/
│       │   ├── markdown.py
│       │   ├── html.py
│       │   ├── rag.py
│       │   └── regulatory_ir.py
│       └── pipeline.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
├── evaluation/
│   ├── gold/
│   ├── metrics/
│   └── reports/
└── outputs/
    └── <document_id>/
        ├── canonical.json
        ├── document.md
        ├── pages/
        ├── crops/
        ├── figures/
        ├── raw/
        └── quality-report.json
```

Canonical Pydantic models define interfaces. Integrate external models/parsers through adapters; assemblers/exporters must not depend directly on private model-output formats.

---

## 11. Evaluation and acceptance gates

### 11.1 Internal Gold Set

Choose models/parsers using internal Gold representing actual target documents. Split by template and source; do not randomly divide similar pages from one template between training and testing.

Cover:

- Born-digital, scanned and mixed text layers.
- Single/multiple columns, spanning headings and sidebars.
- Ruled, borderless, merged-cell and page-spanning tables.
- Multilevel clauses, footnotes, annexes and references.
- Low-resolution, rotated, skewed, compressed and obscured pages.
- Multiple languages, special symbols, units and formulas.

### 11.2 Metrics

| Level | Metrics |
|---|---|
| Text | CER, WER, normalised edit distance |
| High-risk characters | Exact match for numbers, units, dates, clause numbers, negations and comparisons |
| Layout | block IoU、mAP、block-type F1 |
| Local order | Kendall tau, reading-order edit distance |
| Tables | TEDS, cell exact match, row/column span F1 |
| Document structure | Heading-hierarchy F1, cross-page merge F1 |
| Relationships | Explicit-link F1, inferred-link precision/recall |
| Provenance | Valid block-to-segment anchor coverage |
| Conflicts | Critical-conflict recall, unresolved-conflict rate |
| Reliability | Calibration, risk-coverage curve, human-review rate |
| Engineering | Pages/minute, peak memory, GPU memory, cost per thousand pages |

### 11.3 Final quality gate

Mark a document `accepted` only if all conditions hold:

1. Complete page coverage without silent omissions or duplicates.
2. All Canonical schema/reference checks pass.
3. Every body block/table cell traces to a page segment.
4. Every critical conflict is resolved or human-confirmed.
5. No out-of-range cells, invalid spans or unexplained column misalignment.
6. Cross-page merges preserve fragments and assembly operations.
7. All link targets exist and explicit anchors are locatable in source text.
8. Unassigned objects, unknown blocks and low-confidence blocks appear in the quality report.

Weight business errors by risk:

```text
Negation, exception, obligation and permission errors × 10
Number, date, unit and clause-number errors × 5
Table-structure and cross-page merge errors × 3
Ordinary spelling errors × 1
```

Replace models when a document/error category misses internal thresholds, not when public benchmark rankings change.

---

## 12. Execution order

Implement by dependency while retaining one final architecture:

1. Pydantic models, JSON Schema, IDs and coordinates.
2. `docling-parse` / `pypdfium2` for pages, objects and crops.
3. `PP-DocLayoutV3` for blocks, alignment and local ordering.
4. `PP-OCRv6` for native/OCR evidence.
5. Text blocks, heading hierarchy and cross-page paragraphs.
6. `PP-TableMagic`, cell graphs and cross-page tables.
7. Figures, code, equations, index and note.
8. Explicit/inferred `content_links`.
9. Deterministic conflict detection, precision review and resolution policy.
10. Schema validation, quality gates and review queues.
11. Markdown, RAG, Regulatory IR and other exporters.
12. Internal Gold, regression and model-replacement triggers.

Every step writes the same Canonical model, without incompatible intermediate versions.

---

## 13. Final definition

The system is defined by the combination, rather than any single OCR/VLM:

> **Native PDF evidence + visual page evidence + logical blocks/physical segments + type-specific parsers + document-level cross-page reconstruction + explicit content links + high-risk conflict detection + optional precision review + end-to-end provenance.**

The resulting Canonical document answers:

- Which section and logical block owns this content?
- Which source page, coordinates and native objects produced it?
- What do native text, OCR and model review each say?
- Why was this `resolved_text` selected?
- Does the table span pages, which headers were removed and which rows were joined?
- Which figure/table does the body reference, explicitly or by inference?
- Which content still has conflicts, low confidence or human-review needs?

Only structured answers to these questions establish a reliable machine/AI-readable reconstruction of the PDF.

---

## 14. Official component references

- [Docling Parse](https://github.com/docling-project/docling-parse)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PP-DocLayoutV3](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/module_usage/layout_analysis.en.md)
- [PP-OCRv6](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md)
- [PP-TableMagic](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/table_recognition_v2.html)
- [PaddleOCR-VL-1.6](https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.html)
- [gmft](https://github.com/conjuncts/gmft)
