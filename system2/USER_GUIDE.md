# System2 | PDF Extraction Product

This directory owns System2 architecture and operations. Agent rules are in [AGENTS.md](../AGENTS.md), current facts/next experiments in [PROJECT_STATE.md](PROJECT_STATE.md), and shared boundaries in the [workspace overview](../README.md).

This evidence-preserving parser implements [phase one](docs/architecture/01-core-parsing-workflow.md), [phase two](docs/architecture/02-capabilities-and-accuracy.md) and [phase three](docs/architecture/03-complete-product-implementation.md). Main workflow:

```text
PDF → safety preflight + native objects → whole-document profile learning
    → per-page text routing (native / native+visual / OCR)
    → rendering + layout → template-guided repair → type-specific parsing
    → completeness gate → span alignment and conflicts
    → cross-page assembly → precision review / abstention → Canonical JSON
    → validation → exports → Regulatory IR → RDF/SHACL
    → source-grounded review → audit log → revalidation and derivation
```

The engineering model is a modular monolith with stable boundaries:

```text
contracts
├── preflight
├── evidence
├── extraction
├── canonical
├── verification
├── domains
└── delivery
       ▲
Orchestration owns composition and run state only
```

Machine **verification depth** is independent of human-review routing. Every machine-generated or machine-judged
atom requires confidence and provenance. At every depth, below-threshold fields,
evidence conflicts and incomplete provenance enter targeted human review.
See the full module responsibilities, dependency directions and directory guide:
[`05-module-boundaries-and-directory-layout.md`](docs/architecture/05-module-boundaries-and-directory-layout.md).

Default components:

- `docling-parse`: native characters, words, lines, fonts, bitmaps and vector/path evidence.
- `pypdfium2`: page renders and block crops.
- `PP-DocLayoutV3`: page layout.
- `PP-OCRv6`: OCR only for scans, abnormal native text and selected visual regions.
- `PP-TableMagic/SLANet_plus`: table-structure proposals; ruled tables also use OpenCV grids for structure and consistency decisions.
- `img2table`: clear-border structure fallback mapped to the common cell graph.
- `gmft/Table Transformer`: complex, borderless and merged-cell fallback, with gates for low confidence and omitted cell text.
- `PaddleOCR-VL-1.6`: lazy conflict-span review; retain third-channel evidence and abstain when thresholds are unmet.

## Environment setup

Follow the shared [environment guide](../ENVIRONMENT.md#system2-development-and-local-parsing). It defines locked setup, explicit optional extras, native tools and verification. System2 owns `.venv`, [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock). Use `PYTHONPATH=src` for source execution; do not install project dependencies into Conda base or another component's environment.

## Run

```bash
PYTHONPATH=src .venv/bin/python -m pdf_extraction \
  "data/inputs/ASC-INT-001-ASC-Farm-Standard-Interpretation-Manual-V1.0-May-2025.pdf" \
  --output outputs/runs/asc-int-001-p006-p028-native-routed \
  --config config/asc-sample-no-vl.yaml \
  --pages 6-28
```

`--pages` uses one-based human page numbers. Whole-document profiling still reads the full PDF, but formal parsing/exports cover selected pages only. Assess native text per page: use reliable text directly, full OCR for scans/abnormal pages, and targeted visual recognition for mixed pages.

Required outputs:

```text
outputs/runs/asc-int-001/
├── canonical.json
├── document.md
├── document.html
├── document.xml
├── blocks.jsonl
├── rag-chunks.json
├── regulatory-ir.json
├── security-report.json
├── performance-report.json
├── quality-report.json
├── verification-report.json
├── ontology/
│   ├── regulatory.ttl
│   ├── tbox.ttl
│   ├── shapes.ttl
│   └── shacl-report.json
├── overlays/
├── pages/
├── crops/
├── figures/
├── raw/
│   ├── native-manifest.json
│   ├── native-page-*.json
│   ├── document-profile.json
│   ├── text-routing.json
│   ├── analysis-text-page-*.json
│   ├── ocr-manifest.json
│   └── ocr-page-*.json
└── schemas/
    └── canonical-document.schema.json
```

`canonical.json` is the sole structured fact source. Markdown is derived only from it. Native objects, routing decisions, OCR lines, renders and crops provide traceable evidence. Native text stays in `native_text`; only actual visual recognition enters `ocr_text`.

`verification-report.json` records each evidence span's confidence, field threshold,
evidence path, review reason and disposition. `source`, `independent` and `strong` progressively
increase machine-evidence requirements; human-review triggers remain effective at every depth.

## Product interfaces

Python API, CLI, REST API and worker share `ExtractionPipeline`:

```python
from pdf_extraction.orchestration import ExtractionPipeline
```

The legacy `from pdf_extraction.pipeline import ExtractionPipeline` remains compatible during migration.

```bash
pdf-extract-api
pdf-extract-worker --database runtime/jobs.sqlite3
```

REST endpoints provide submission, job status, Canonical, quality, review queues/decisions, page labels and downloads. The standalone diagnostic review UI is at `http://127.0.0.1:8000/review/<job_id>`, with block/span/cell evidence and accept/modify/reject/unreadable actions. Human actions write Canonical `audit_events` and append-only `audit-events.jsonl`. The shared workbench remains the normal review entry.

SQLite persists job state, supporting retries, completed-result recovery, render/OCR/crop caches and intermediate preservation. `/health` checks liveness; `/metrics` reports job-state metrics.

## Regulatory IR and ontology

`regulatory-ir.json` derives deterministically from finalised Canonical blocks, retaining source block/segment IDs and page indices. RDF is mapped only through Regulatory IR. `pySHACL` violations enter review instead of bypassing validation into accepted facts.

## Deployment

Run locally or use [deployments/compose.yaml](deployments/compose.yaml) for the API and persistent worker:

```bash
docker compose -f deployments/compose.yaml up --build
```

Default binding is loopback only; hosted OCR/VLM is disabled. Run configuration enforces preflight, resource limits, data routing, owner-only output permissions and temporary-file governance.

## Tests

```bash
.venv/bin/pytest
```

Tests cover models, IDs, coordinates, references, critical text conflicts, reading order, hyphenation, table boundaries/spans, figure crops, Markdown export and three-page preflight on the local real PDF.

Phase-two regression:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_gold_fixtures.py
PYTHONPATH=src .venv/bin/python scripts/run_gold_set.py
PYTHONPATH=src .venv/bin/python -m pdf_extraction.evaluation.cli \
  --manifest gold/manifest.json \
  --output outputs/evaluation-report.json \
  --config config/default.yaml \
  --enforce
```

Reports include CER/WER, high-risk exact match, block omission, block-type/heading F1, cross-page precision/recall, cell exact match, span F1, critical-conflict recall, accepted-result precision and automatic coverage, stratified by document/error type.

Complete gates check parser routes, page completeness, provenance, Regulatory IR sources, SHACL, derivative coverage, review rate, performance, memory and security. Historical external benchmarks and old `outputs/ps3` artifacts are not current domain acceptance inputs.

## Domain acceptance

Evaluate regulations, general rules and standards using internal target-domain Gold, real-document regression, critical-field completeness, structural consistency, traceable evidence and review gates. Generic public benchmarks are not acceptance evidence.

## Current quality boundaries

Implemented capabilities include two-threshold cross-page paragraph/table merging, header deduplication, partial row joining, span conflicts, Figure OCR, code/equations, footnotes/references, three-channel review and ontology-ready outputs. Formula LaTeX and figure interpretation remain derived, never replacing original images. Unresolved cross-document targets stay candidates. Completeness gaps, unresolved critical spans, low-confidence table structure, omitted cell text and SHACL violations require review rather than silent acceptance.

## Workspace ownership

This is `05_Working area of requirements side/system2`, relocated from the desktop PDF Extraction Product with internal architecture and `.venv` preserved. See [shared boundaries](../README.md) and [System1](../system1/USER_GUIDE.md). Relocation alone does not establish automatic handoff. The old desktop path is absent; tools still bound to it must use this directory.


## Governed local snapshot intake

Read the [intake contract](docs/contracts/source-intake.md). Run from System2 using its environment:

```sh
PYTHONPATH=src .venv/bin/python -m pdf_extraction.orchestration.source_batch \
  --system1 "../system1" \
  --source-id PA001 --source-id PA002 \
  --output outputs/runs/html-example-01
```

The output directory must be new. This reads System1's governed effective selections/versions and explicit snapshots without downloading. In a worktree without System1, point to the saved project; `--system1-config` selects its configuration. Rejection/parsing failure returns nonzero and preserves evidence. For intake-read/output-creation failures, inspect process errors first. Review status concerns parsing, not repeated source eligibility review.

The offline `--registry "../system1/Requirement_Source_Registry.xlsx" --source-root "../system1/Data"` entry remains available with complete workbook caches; it cannot be combined with `--system1`.

PDF requires `--pdf-config config/pdf-intake-positioned.yaml --pdf-pages 0`, restricted to one to four zero-based page indices. This local positioned route uses locked docling-parse; rebuild with `uv sync --frozen --extra dev --extra table-fallbacks --extra docling`. The legacy pypdf configuration remains low-cost but loses clause/footnote structure on real samples and is not quality-equivalent. Preserve sources; Workbench belongs to its own component.

PDF indexes bind native Canonical schema, verification and hashes. Underlying failure or missing verification returns failed. Versioned human-review scope belongs to the [transaction contract](docs/contracts/review-transactions.md).


### HTML v2 outputs and checks

The HTML command auto-detects five supported families and generates Canonical/verification files. The result binds schema and both hashes; machine success remains review_required. Read the [HTML contract](docs/contracts/html-document-v2.md) and [completion report](docs/reports/09-html-parser-completion.md). Explicit `config/html-auto.json` is supported; legacy `config/html-template.json` retains v1 without migrating history.

Empty bodies, unknown templates, non-included sources, version changes and hash mismatches are explicit. System1 refreshes formula/chart caches on review saves; normal intake uses effective selections. Missing offline caches still reject, without editing manifests to bypass gates.

## Current non-PDF priority

PDF accuracy is deferred by user decision. Complete HTML/Excel first, then System2 integration with the existing workbench. Workbench owns the human interface; System2 supplies queues, source evidence, decisions and receipts. Production queues/decisions are not connected yet.

Use source_batch for eligible registered XLSX without PDF configuration. Results contain Canonical, verification and result indexes. Formulas are not calculated; missing caches stay flagged and hidden content is retained. HTML supports five static families. See the [Excel contract](docs/contracts/excel-document-v1.md). Legacy XLS remains unimplemented. GLOBALG.A.P. reference diagnostics exist, but eligible registered Excel production intake is unaccepted. Structural results do not establish Requirement semantics.

HTML/XLSX relationship checks now respect HTML row groups, actual shared-text references, shared formulas and merge conflicts. Success remains review_required. Current validation and remaining scope belong to [System2 state](PROJECT_STATE.md).

### Source clauses and field outputs

New batches also generate source-records, verification and result companions. GLOBALG.A.P. maps number, section, body, Criteria and Level; Lovdata maps number, title, body, notes and context. Default v2 adds ASC number/body/applicability, five-family paragraphs/headings/lists/notes and annex cells, with Canonical geometry/section/display references. Residual content remains located; audit answers never become standard requirements. See [v2](docs/contracts/source-records-v2.md).

Source-verified Canonical may be projected into a new directory:

```sh
PYTHONPATH=src .venv/bin/python -m pdf_extraction.orchestration.source_records \
  --canonical outputs/runs/html-example-01/PA001-001/canonical.json \
  --verification outputs/runs/html-example-01/PA001-001/verification.json \
  --output outputs/runs/html-example-records-01
```

Historical projections bind historical source versions without reconfirming current eligibility. Projection success is not human parsing acceptance or System3 enrichment.

Process current INCLUDE sources only. Non-INCLUDE gates do not create parsing tasks, and non-included Excel does not block completion. Diagnosed empty Lovdata bodies are directory snapshots requiring complete source acquisition by System1, preserving eligibility. See the [content report](docs/reports/14-nonpdf-content-completion.md).

For a legacy projection, add `--schema-version source-records/1`; retain v1 models, schema and historical artifacts.
