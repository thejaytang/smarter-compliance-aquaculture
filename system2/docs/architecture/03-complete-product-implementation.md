# Phase Three: Complete Engineering Implementation

## 1. Objective

After all requirements of [phase one](01-core-parsing-workflow.md) and [phase two](02-capabilities-and-accuracy.md) are met, implement the complete product defined in the [full engineering design](00-full-engineering-design.md).

Final system coverage:

```text
Complete PDF parsing
+ all block types
+ multiple derived outputs
+ Regulatory IR / ontology
+ source-grounded review UI
+ reproducible deployment
+ runtime monitoring and version governance
+ security, performance and regression evaluation
```

## 2. Complete block capabilities

Support:

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

Extend the first two phases with:

### 2.1 code parser

- Recover lines, indentation and monospaced formatting from native character positions.
- Use OCR to check special characters, commands and configuration symbols.
- Review conflicts using both full-block and local-span crops.
- Optionally infer the code language without changing source text.

### 2.2 equation parser

- Preserve the original image, bbox and adjacent text.
- Optionally generate LaTeX or structured expressions.
- Store formula transcription in `derived`; it must not replace original visual evidence.
- Apply high-risk checks to comparison symbols, subscripts/superscripts and units.

### 2.3 Footnotes and cross-references

- Link body footnote markers to footnote blocks.
- Parse clause, section, annex, table and figure cross-references.
- Preserve explicit reference anchors and source spans.
- Support cross-document reference candidates without inventing resolution when the target document is unavailable.

### 2.4 figure visual understanding

Optional outputs:

```json
{
  "embedded_text": [],
  "visual_description": "...",
  "entities": [],
  "relations": []
}
```

Visual interpretation remains in `derived`. Inferred relationships in charts, flowcharts and engineering drawings require model attribution and confidence.

### 2.5 page label

Add:

- Physical `page_index`.
- PDF page label。
- Recognised printed-page-number candidates.
- Mapping confidence and human-correction records.

The physical index remains the stable primary key; display page numbers are additional attributes only.

## 3. Complete derived outputs

Generate every output from the Canonical model:

### 3.1 Document outputs

- Markdown。
- HTML。
- XML。
- JSONL block stream。
- Visual overlays and quality reports.

### 3.2 RAG chunks

- Use sections and logical blocks as boundaries.
- Do not split tables or logical blocks spanning pages.
- Preserve heading paths, block IDs, page indices and bboxes.
- Link figures, tables, code and formulas through `content_links`.
- Allow retrieval-specific chunk sizes without changing the Canonical model.

### 3.3 Regulatory IR

Extract from Canonical blocks:

```text
regulated_entity
modality
action
object
condition
exception
threshold
jurisdiction
effective_date
cross_references
source_block_ids
source_segment_ids
```

Use schema-constrained extraction. Every fact must retain its source block and segment.

### 3.4 ontology

Fixed processing chain:

```text
Canonical JSON
→ Regulatory IR
→ predefined T-box
→ deterministic RDF mapping
→ SHACL validation
→ review queue
```

Use RDFLib and `pySHACL` by default. LLMs must not directly generate final Turtle or bypass Regulatory IR and SHACL.

## 4. source-grounded review UI

Implement the minimum review interface:

- Show PDF pages and bbox highlights on the left.
- Show blocks, segments and native/OCR/review/resolved content on the right.
- Display conflicting spans, table cells, cross-page assembly and content links.
- Support acceptance, editing, rejection and unreadable decisions.
- Record every human modification as an immutable audit event.
- Allow filtering to critical, ambiguous, unknown and low-confidence content.

After human edits, rerun schema validation and downstream derivation. Do not edit exported Markdown or RDF directly.

## 5. Operations and deployment

### 5.1 Service interfaces

Provide:

```text
CLI
Python API
REST API
background job worker
```

Core interfaces:

```text
submit document
get processing status
get canonical document
get quality report
get review queue
submit review decision
export derived artifact
```

### 5.2 Job states

```text
queued
preflight
parsing
assembling
reconciling
validating
review_required
accepted
failed
```

On failure, preserve completed intermediate artifacts and identify the failed pages and modules.

### 5.3 Reproducibility

Record for every run:

- Pipeline commit or version.
- Configuration hash.
- Model names, weight versions and model-file hashes.
- Runtime environment and hardware.
- Renderer version and DPI.
- Start/end times and per-module duration.
- Random seeds and deterministic settings.

### 5.4 Performance

Implement:

- Page-level parallelism, with document assembly after page results are complete.
- Model batching and GPU/CPU routing.
- Caching for crops, renders and model results.
- Resumable jobs and failure retries.
- Streaming large documents without holding the entire document in memory.

## 6. Security and data governance

Handle:

- Encrypted or malformed PDFs.
- Extremely large pages, embedded attachments, JavaScript and external links.
- Parsing timeouts, memory limits and file-size limits.
- Document prompt injection: all PDF content is data, never model system instructions.
- Data-routing policy for local and hosted models.
- Controls for source text, personal data and sensitive content in logs.
- Output-directory permissions and temporary-file cleanup.

Externally hosted OCR/VLM is disabled by default and may be enabled only when run configuration and data policy permit it.

## 7. Complete quality framework

### 7.1 Evaluation levels

```text
Text
High-risk spans
layout
Reading order
Tables
Cross-page structure
content links
figure / code / equation
provenance
Regulatory IR
ontology / SHACL
Performance and human-review rate
```

### 7.2 Regression suite

Every model, dependency or rule change requires:

- unit tests。
- schema compatibility tests。
- Fixed-PDF integration tests.
- gold set regression。
- worst-case documents。
- Performance and memory baselines.
- Downstream Regulatory IR and SHACL validation.

### 7.3 Release gates

Release candidates must satisfy:

1. No silently omitted pages.
2. All schema and reference checks pass.
3. No critical conflict is silently accepted.
4. Accepted-result precision is at least the established baseline.
5. Changes in automatic coverage are explained.
6. No unacceptable decline in table, cross-page or hierarchy metrics.
7. Provenance-anchor coverage meets its target.
8. Performance, memory and human-review rate remain within budget.

## 8. Complete engineering structure

```text
pdf-extraction-product/
├── config/
├── schemas/
├── src/pdf_extraction/
│   ├── ingest/
│   ├── layout/
│   ├── parsers/
│   ├── assemble/
│   ├── reconcile/
│   ├── models/
│   ├── validate/
│   ├── export/
│   ├── regulatory_ir/
│   ├── ontology/
│   ├── review/
│   ├── api/
│   └── pipeline.py
├── ui/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
├── evaluation/
├── deployments/
└── outputs/
```

## 9. Completion criteria

All criteria must hold:

1. All phase-one and phase-two acceptance criteria continue to pass.
2. Every defined block type has a runnable parser or explicit `unknown` route.
3. Canonical JSON can generate Markdown, HTML, RAG chunks and Regulatory IR.
4. Regulatory IR maps deterministically to RDF and either passes SHACL or enters review.
5. The review interface locates, edits and records block/span/cell issues.
6. CLI, Python API and REST API use the same pipeline.
7. Runs are recoverable, observable and reproducible.
8. Security preflight, resource limits and data-routing policies are enforced.
9. Gold evaluation, regression tests and release gates run automatically.
10. Every accepted critical fact traces to the original PDF bbox and source evidence.

Completion establishes a full product for PDF parsing, quality control, human review and ontology-ready output.
