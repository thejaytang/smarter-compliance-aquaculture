# System2 | PDF Extraction Product

## Human-led material interface

The current material route is described in the [Workbench daily guide](../workbench/USER_GUIDE.md#human-led-material-workspace) and [technical interface guide](docs/contracts/human-material-workbench.md). Read those before the retained parser/legacy A/B instructions below. These guides describe implementation and usage; [PROJECT_STATE.md](PROJECT_STATE.md) owns dated System2 runtime and verification facts.

Use one saved source material at a time. **Extract** explicitly requests a structural candidate; a separate human Keep/Adopt/Edit-and-merge action decides how it enters the editable layer. **Save material** persists partial work. **Confirm content review** is a separate named confirmation requiring all original ranges, omissions, issues and dependencies to be checked. The middle pane includes full content and manual text/table/image supplementation, without filtering to likely Requirements.

This route uses existing local HTML/OOXML parsers and positioned PDF/native ruled-table helpers. It does not invoke the legacy domain-producing pipeline, classification, OCR or external models. PDF scan/native-visibility limits, stripped HTML assets and Excel caches/hidden-content limitations remain explicit. **Process** stays unavailable; the final nested Requirement structure, forms and semantic processor are deferred.

The material PDF reader defaults to saved-page images with Previous/Next/Go, full page count, zoom and within-page scrolling. Images contain no selectable text; a separate disclosure provides unverified native text for selection/copy when present. The optional browser PDF plugin is loaded only on request and may be blank or unavailable. Its rendering is not an accepted default-path capability.

Legacy Canonical artifacts, effective human corrections and decisions remain recoverable. Importing earlier content produces an explicit candidate and does not relabel an old acceptance as current whole-material confirmation. The following dated repair, A/B and standalone CLI descriptions retain their compatibility scope.


## Daily repairs, source follow-up and history

A source with missing or unreadable body content has a source follow-up item even when parsing produced no reviewable units. Open its retained original/observations, enter what must be supplied or checked, and submit the follow-up to System1. Use System1's normal file/link and issue-verification controls. A report or URL correction does not retrieve a complete original or finish the source.

**Source context and references** beside the extracted result shows linked original passages and pages. Open a linked source unit to inspect or repair it. A linked-content change reopens affected downstream checks. In **Review history**, expand the relevant decision and choose **Open current result to review**. The current saved human classification is displayed; record a new decision to correct it. New B history shows classification before/after, time and source version. Missing fields in older test history are labelled explicitly.

For scanned text, inspect the full original page even where no extraction exists. Use the located missing-content correction, type or paste the exact source wording and save. Then confirm the corrected range and classify it in B. Unknown machine scores remain unknown and do not override an explicit complete human check.

## Original-page comparison | 2026-09-10

In System2 Content proofreading, choose Inspect original PDF pages, open a page and select Check this original page. The saved comparison includes original-region highlights, correction drafts and explicit unverified scope. Recheck after modifying content. A saved correction is not A/B acceptance. Excel synchronization status shows the database and snapshot versions separately. See [the comparison workflow and limits](docs/contracts/original-verification.md). [Stage-specific weekly sampling](docs/contracts/weekly-original-sampling.md) is integrated with normal A/B activation disabled pending explicit authorization.

## PDF reference samples | 2026-09-10

Use **System2 → Pending review → Content proofreading → PDF reference samples** to collect a development reference directly from an original. Choose the primary PDF page and optional supporting pages, then start a blank reference. Locate a region on the original or enter its coordinates, select its role and transcribe the exact text. For tables, record the grid and each cell, including spans. Link notes, captions and related pages to the appropriate regions. The original can be magnified within its left pane.

**Add / update region** stages the form's region; **Save reference draft** saves unfinished work. Record prior exposure, assistance and unresolved questions. Confirm only after inspecting the whole primary page, including areas without extracted items, and completing all reference regions and relationships. Incomplete tables or unresolved checks remain drafts. **Reference saved · assessment pending** is a source-reference candidate, not an extraction decision or independent quality result. A saved candidate needs a reasoned new revision before editing; its history remains available. Reference collection does not rewrite the Requirement Excel register.

This first implementation creates unqualified development samples. Independent reviewer qualification remains unfinished. From a saved reference, choose **Assess extraction and verifier findings**: inspect every original region and output record, record errors, then freeze the inventory to reveal findings. Classify each finding and its location before confirming the diagnostic assessment. Reopen the inventory with a reason to revise errors; exposure and previous reports remain recorded. Changed reference/output/report evidence makes earlier assessments historical. See [checkpoint 46](docs/reports/46-bound-source-assessment-workbench.md). The [reference contract](docs/contracts/pdf-source-reference.md) and [checkpoint evidence](docs/reports/45-source-reference-workbench.md) describe the verified scope. An already-running workbench needs its normal restart to load the new server routes; this checkpoint did not restart the normal service.

## Legacy two-stage workflow | 2026-09-09

Open the shared launcher and select a named reviewer. System2 → Pending review shows real jobs; choose an INCLUDE source and click Start processing. Confirm full-text coverage and content/structure before classifying Requirements, context and exclusions. Use source evidence, corrections, split/merge or missing-content supplementation where needed. Save draft is not acceptance. Include reviewed content to reopen an earlier result. Pause is checkpoint-based; Request reprocessing preserves the old generation and invalidates its deliveries.

Confidence settings owns all thresholds, initially 95%. Uncalibrated results require manual review regardless of threshold. Raising thresholds reopens affected machine results; human decisions/drafts remain protected. Optional assistance is disabled without explicit configuration. System1 Machine assessments shows evidence-supported five-dimension proposals and preserves named human decisions.

In each System2 task, expand **Scores and evidence by dimension** to inspect A text accuracy, original coverage, structure/relationships and reading order, and B classification, original association and parent/subitem correctness. Missing or unsupported dimensions remain unknown. A human confirmation does not create a machine score; the lowest supported required dimension controls automatic routing.

System2 Weekly checks separates A original-side scopes from B positive/negative judgments, with explicit shortfalls, Pending and Review history. Problems use the ordinary repair task and require a separate follow-up before closure; failed submissions and unresolved findings are not complete. Earlier machine-only batches remain in history. System3 Incoming requirements displays incremental deliveries and source completeness; semantic processing is not connected. Original HTML is a script-free text view, PDF opens its registered full original, and XLSX supports paged cells, formulas/caches, hidden state and merged-region metadata.

See the [current workflow contract](docs/contracts/two-stage-review.md) for authority, operations and compatibility. Older dated integration/demo descriptions below are historical; they do not replace this workflow.


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

## Legacy parser CLI

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

## Historical pre-integration priority

This paragraph records the earlier pre-integration scope; consult PROJECT_STATE.md for the current pause and implemented PDF repairs. At that earlier checkpoint, PDF accuracy was deferred while HTML/Excel and workbench integration were prioritised. Workbench owns the human interface; System2 supplies queues, source evidence, decisions and receipts. Production queues/decisions are not connected yet.

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


## Excel requirement register

Open [System2_Requirement_Register.xlsx](System2_Requirement_Register.xlsx), or use **Download Excel register** in System2's browser review page. Each source document has its own worksheet, with a clickable source index. Review states, current delivery status, original text and source positions remain visible. Sources not yet explicitly started have an empty, clearly labeled sheet. Filter **Delivery status = Available** for currently accepted Requirements.

The running workbench keeps the local register synchronized. Close and reopen Excel after processing or review changes; downloaded copies are snapshots. Apply corrections in the browser. Editing Excel does not submit a decision and the next refresh replaces those edits. See the [register contract](docs/contracts/requirement-workbook.md) for columns, versioning, long content and synchronization.

### Repairing PDF table row items in the browser

Open a complete table under **Content proofreading**. Use **Repair table rows, columns and merged ranges** for cell text boundaries, coordinates and spans. Use **Repair missing or duplicate row items** when the grid is present but its independent review items are missing or duplicated.

Choose an original row to create its missing item from the retained cells. A title or explanatory row can remain within complete-table review; this does not classify or accept its content. For duplicates, inspect the proposed duplicate and retained item before submitting. They must cover the same original cells; resolve text/relationship conflicts first. Save a draft or apply the named repair, then read its receipt. Changed content returns to review, and historical replaced items remain traceable. **Restore values before an earlier repair** restores supported overlays when later work does not conflict.

**Remove an extracted row absent from the original** requires explicit comparison and preserves its old cells/history. Repair shared cells or incoming relationships first when the operation reports a conflict. **Clear cell text** removes erroneous characters from an original empty cell. See [the current row-removal evidence](docs/reports/39-erroneous-table-row.md).

Use **Enlarge original region** when a shared cell makes the inline original crop too small. For a paragraph without saved line breaks, **Start of next original part** can locate a unique exact phrase; advanced region choices keep each split part bound to its own source area. Table-wide notes are inherited by its rows and must be changed at the complete table. **Evidence copy** choices and **Evidence only** Excel rows are retained support material, not independent deliverables.

### Combining PDF table fragments across pages

From a complete PDF table, open **Combine a table continuing on another page**. Select the printed column-heading row, find a clause on the later page, and compare the continuation's original table. Confirm that columns match in the same order and supply the source evidence before **Apply table combination**. Saving a draft does not apply or accept the combination.

**Open combined table** displays the effective grid, one original preview per fragment, and source column labels. **Open table fragment** returns to the ordinary text/grid and local-note editors. Changes there update the combined view. **Undo table combination** preserves the fragments and prior history; conflicting later edits require resolution first. The combined view is related context, while the original rows retain their separate Requirement judgments.

All physical rows remain visible, including repeated headers. Use the separate row-removal repair for extraction artifacts. This combination does not automatically remap columns or join a single row split across pages.

For one numbered item continuing across pages, a verified manual alternative is available: from the original page coverage choose **Add missing content**, enter the complete original number/title/text and its first location, then attach both physical row fragments as **Context** under **Repair source content and relationships**. Check the relevant original ranges. In B, classify the physical fragments and table containers as related context, and classify the complete parent once. Do not publish both representations. Linked source text, pages and versions accompany the parent in Excel. After a dependent correction, compare and update the complete parent again before A/B release. See [the complete-parent example](docs/reports/40-complete-parent-and-history.md); this is a manual alternative, not automatic row reconstruction.

## Provisional requirement subitems

After A content and dependencies pass, select **Create / replace requirement subitems** in Requirement judgment. Select original wording or paste an exact unique quotation, then add it as a subitem. Review all unassigned text and explain why it contains no additional requirement. Keep original subitem numbers empty when the source has none; generated labels are separate. Choose the temporary parent/subitem counting rule and submit the complete-range decision. Use **Browse all original content** to reopen an accepted item and explicitly replace or remove its subitems. Previous versions remain in Review history. The [subdivision contract](docs/contracts/requirement-subdivision.md) describes evidence scope, draft behavior and pending peer confirmation.
