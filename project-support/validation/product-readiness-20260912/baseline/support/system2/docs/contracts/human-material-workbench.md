# Human material workspace: implementation interfaces

This is an implementation and operating guide for the [human-led material goal](../../../docs/design/human-led-workbench-goal.md). It is not an acceptance report or a claim that a running instance has loaded these modules. Consult the [workstream state](../../../PROJECT_STATE.md) and [System2 state](../../PROJECT_STATE.md) for dated runtime and verification evidence. The [Workbench user guide](../../../workbench/USER_GUIDE.md#human-led-material-workspace) owns the normal human workflow.

## 1. Ownership and action boundaries

System1 remains the authority for source identity, eligibility, snapshot versions and source follow-up. The browser sends a registered source or material identity; it cannot choose a filesystem path or submit its own reviewer identity. Workbench supplies the named session actor and enforces the existing loopback Host, Origin, CSRF and request-field guards.

The new route is separate from legacy content/classification recomputation:

```text
Registered System1 snapshot
  → Open material: pin verified original and establish required reading scope
  → Extract: persist one explicit candidate request
  → Material worker: pure structural parser and immutable candidate evidence
  → Human Keep / Adopt / Edit and merge
  → Save material: durable partial content and review progress
  → Confirm content review: separate named whole-material confirmation
  → Process: unavailable; final Requirement schema and processor deferred
```

Opening, reading, scrolling, saving and confirming never enqueue conversion. The background material worker consumes only already-requested Extract candidates. A worker restart can resume a pending request; it cannot create a new extraction request merely because a material was viewed. The legacy parser and its retained review/derivation history are a separate compatibility path.

Implementation owners:

| Module | Responsibility |
| --- | --- |
| [material_service.py](../../src/pdf_extraction/orchestration/material_service.py) | Governed source handoff, original pinning, material commands and the single-worker lock |
| [materials.py](../../src/pdf_extraction/review/materials.py) | Additive material tables in the owning Workflow database, guarded revisions, requests, candidates and human confirmation |
| [material_reader.py](../../src/pdf_extraction/evidence/material_reader.py) | Hash-bound whole-original scope and read-only PDF/HTML/Excel reading data |
| [material_parser.py](../../src/pdf_extraction/orchestration/material_parser.py) | Explicit structural extraction into a fresh candidate directory |
| [material_legacy.py](../../src/pdf_extraction/orchestration/material_legacy.py) | Import retained effective content as an explicit candidate without reinterpreting old decisions as new confirmations |
| [material_processor.py](../../src/pdf_extraction/review/material_processor.py) | Dormant, versioned future Requirement-processing boundary |

Material originals and parser attempts live below the owning workflow root in `material-originals/` and `material-artifacts/`. They are source-bound retained artifacts, not disposable caches. Candidate attempts, previous human revisions, legacy corrections and original System1 history remain distinct.

## 2. Original-reader contract

### Round-two read and client compatibility

Material HTTP mutations require `X-Material-API-Version: 2`. Missing/older versions receive HTTP426 before any material mutation, with `material_client_upgrade_required`; reload the page and recover its local journal before retrying. The source-governance and dormant processor contracts are unchanged. Current material bodies still use the existing identity/revision/block schema; the HTTP transport now distinguishes summaries from details.

`GET /api/materials?offset=0&limit=50&query=...` returns source choices, paged material summaries, total/offset/limit/has_more and aggregate counts. Filtering searches all indexed materials, not just the visible page. `GET /api/material/history?id=...&offset=0&limit=20` returns revision summaries; fetch `/api/material?id=...&revision=...` for the selected immutable body. Candidate/conflict summaries omit their full bodies; `/api/material/candidate?id=...&candidate_id=...` and `/api/material/conflict?id=...&conflict_id=...` return bound details. Cross-material detail IDs are rejected. Internal full store reads remain available for existing callers.

Read indexes and triggers are additive/rebuildable projections of authoritative JSON. Rebuilding them never rewrites historical decisions. Reader caches verify source hash, reader version, options and cached-content checksum; only derived reading data is replaceable. Originals, parser artifacts and version histories are not caches. Original delivery streams a validated pinned file without Base64 intermediary, and PDF ranges are sliced from that same verified descriptor.

Excel opening inventories every worksheet, including empty/hidden sheets, without traversing its cell body. `dimensions_pending` with null dimensions means they have not yet been measured, not an empty worksheet. Reading measures the selected original range and uses the bounded streaming reader. No formula execution, OCR or semantic classification is introduced.

`inspect_original(path, expected_hash)` returns `schema_version`, `source_sha256`, `kind`, `scope` and format metadata. `read_material(path, expected_hash, **options)` adds the selected reading view. Paths are internal, resolved from registered/pinned sources by the service. Each read verifies the exact source hash. A changed file produces an error rather than silently serving another version.

Required scope uses `{id, kind, label, location}` objects. PDF has one `page:N` scope per page, including blank and image-only pages. HTML has `html:document` for the complete saved document. Excel has `sheet:<name>` for every worksheet, including empty and hidden sheets. Scope is independent of the number of extracted blocks.

| Format | Options and payload | Deliberate limits |
| --- | --- | --- |
| PDF | One-based `page`; total `pages`, page image, `native_text`, `selectable_native`, dimensions and `page_warning` | The UI defaults to saved-page images with Previous/Next/Go, full page count, zoom and within-page scrolling. A bitmap contains no selectable text. Native text is separately selectable unverified assistance and may include invisible marks. The optional native PDF iframe is created only when its disclosure is opened; browser-plugin rendering may fail or remain blank and is not claimed as a passed capability. Viewing performs no OCR. |
| HTML | Complete sanitized `html` plus stable `{id, locator, label}` anchors | Source scripts, styles and remote assets are disabled. All static disclosure content is opened. This is an isolated reading view, not a claim of native website styling fidelity. |
| XLSX | `sheet`, one-based `row` and `column`, `row_count` up to 200, `column_count` up to 100; worksheet manifest, cells and merged ranges | The caller can navigate all rows and columns in bounded windows. Charts, drawings, comments, conditional presentation and native styling require original inspection or explicit supplementation. Formulas are not recalculated. |
| XLS | Explicit unsupported/compatibility notice, retained original and scope | A human-created XLSX parsing copy needs recorded original lineage. There is no silent legacy conversion. |

Excel cells retain `address`, `value`, `formula`, `cached`, `cache_status`, hidden-row/column flags and merge relationships. A merge crossing a window boundary still reports `merge_anchor`, `merge_range` and the anchor's saved value. `merged` entries use one-based `row`/`column` and `rowspan`/`colspan`. Formula text and saved values remain separate; a missing or old cache is not a newly calculated result.

PDF evidence references retain zero-based `page_index` alongside one-based user-facing `page`. Coordinates are original PDF points. HTML uses the existing `nth-of-type` locator syntax and stable `original-…` anchor IDs. Excel references retain worksheet part/cell locators and readable `sheet`/`cell_range` fields.

The HTTP layer serves HTML at `/api/material/html?id=…` under a restrictive CSP and opaque sandbox. This dedicated derived endpoint supports local fragment navigation without inheriting the outer application's URL. Untouched HTML remains download-only. No source scripts or external assets are fetched for reading.

## 3. Candidate-parser contract

`parse_material(source, source_root, output, *, page_indices=None)` accepts the existing governed `Snapshot` model or equivalent dictionary. `output` must be a fresh, non-existing directory outside `source_root`. The parser captures verified bytes before processing and writes an immutable pinned source copy plus parser evidence. A changed upstream file after that capture cannot relabel the result as a newer input.

The returned `material-structural-parser/1` envelope includes:

- `source_sha256`, `snapshot_id`, `parser_version` and `config_hash`.
- `blocks`, the complete required `scope`, `covered_scope`, `warnings` and `unresolved`.
- `canonical_artifacts`, with retained relative artifact names.
- `status`: `candidate_available` or `partial`; neither means reviewed or adopted.
- `review_policy: human_material_confirmation_required` and `requirement_status: not_connected`.

Blocks use stable IDs, `type` (`text`, `heading`, `table`, `image`), `text`, `level`, `parent_id`, `numbering`, `dependencies` and `source_refs`. Source numbering remains separate from generated block IDs. Tables use rectangular string `rows`, zero-based merge entries `{row, col, rowspan, colspan}` and linked `notes`. Images use an original `source_ref`, `attachment: null` and attribution; parser output does not invent evidence images. These are editable source-content structures, not the deferred Requirement domain schema.

### 3.1 Existing parser reuse

HTML calls the existing pure format parser for recognized profiles and retains its Canonical output. The material adapter additionally reads complete static body content, including outside profile roots, and reuses existing table-span assembly. An unknown profile yields an explicitly labelled generic static-DOM candidate for manual correction.

XLSX reuses the non-executing OOXML parser and retains the complete cell/structure Canonical document. Sparse content is presented as bounded table groups so a far-away cell does not allocate a million-row editable rectangle. Empty and hidden worksheets remain in required scope. Stored formulas remain text with saved-cache notes.

PDF reuses `NativeExtractor` with the existing positioned-native configuration in mapped windows of at most three pages. PDFium creates derivative window copies while the original bytes remain pinned; this also avoids requiring a separate optional pypdf AES package for originals already readable by PDFium. Native evidence records the original page mapping and backend/version. Existing local ruled-grid detection and merged-cell geometry produce table candidates. Each page image and embedded-image reference stays available for comparison.

The material route does not invoke the legacy `ExtractionPipeline`, Requirement assembly/classification, semantic processing, OCR or hosted models. Native lines, headings, reading order, unruled tables and complex layouts may require human correction. A scan without usable native text produces a visible limitation and a manual transcription/image path. Parser warnings and native evidence are assistance, not independent proof of fidelity.

### 3.2 Worker, conflict and adoption

`MaterialService.tick()` runs through the Workbench material thread in System2's existing environment. It takes the owning single-worker lock, processes a persisted candidate and retains each attempt under a new artifact directory. No standalone scheduler or third-stage service is required.

The owning store binds each request to material/source/input revisions. Repeated request IDs have durable receipts; stale writes must be reconciled rather than overwriting another saved version. Candidate completion preserves current human content. Results from an older captured input remain stale, and failed processing leaves saved human work available.

Keep, Adopt and Edit/merge are separate guarded human decisions. They require source comparison and do not imply content confirmation. Saving partial work remains possible when source checking is temporarily unavailable; content confirmation requires current source authority, cleared substantive issues, all original scopes checked, source associations/dependencies checked and an explicit named human confirmation.

## 4. HTTP and future processor boundary

### Server-owned review impact

Every changed body or issue invalidates final content confirmation. `review_impact` records the prior content revision, affected blocks/scopes, retained scopes and reason; `review_checks` maps each retained scope to its original actor/time/content revision/source hash. PDF pages, Excel worksheets and the complete HTML document remain the review units.

The server compares old/new blocks and follows dependency links; hierarchy or order changes also expand through affected parent/child associations. References on both removed and added content count. Missing associations, missing historical check provenance, source-version changes or whole-material issue changes require full review. A changed save cannot invent checks from a checklist submitted with its old draft. Explicit checks on an unchanged saved revision acquire provenance. Withdrawing a range or association check revokes a current confirmation even when body text is unchanged. Older immutable revisions and confirmations stay readable as history.

The browser may retain provisional checks while editing, but the saved server result determines which remain valid. No content edit, candidate adoption/merge or historical restore automatically confirms content. Unknown impact remains conservative rather than guessing semantic relationships.

Read routes are `/api/materials`, `/api/material`, `/api/material/history`, `/api/material/reader`, `/api/material/html` and `/api/material/original`. Mutations use `/api/material/open`, `/save`, `/confirm`, `/extract`, `/adopt`, `/import-legacy`, `/source-issue` and `/process`.

Except opening a registered source, mutations use `material_id`, `expected_revision` and `request_id`. Actors and source paths are server-owned. Browser retries reuse the same request identity. Conflict responses retain the local draft for explicit comparison/rebasing; they do not provide permission to discard newer work.

`material-processor/1` reports `connected: false`, no supported operations/schema versions and `state: unavailable`. A real Process request returns unavailable without changing structured content. The future input envelope captures confirmed content revision, selected scope and dependency closure, ordered blocks, evidence references, request identity and input hash. The output boundary distinguishes empty, partial, failed, unavailable and candidate states, binds the exact input, and requires separate human adoption. Final nested fields, forms and semantic algorithms remain deliberately unspecified.

Every output state, including unavailable, echoes `material_id`, `request_id`, `input_revision`, `input_hash`, selected `scope`, and the source's `source_id`, `snapshot_id` and `content_hash`. Validation rejects a mismatch in any of these bindings, even when another material happens to have the same revision number. The input hash covers material and source identity, revision, scope, ordered content and dependencies. Captured content/source values are copied so subsequent draft edits cannot mutate an existing envelope. Validation preserves arbitrary versioned `candidate_payload` fields; it neither adopts them nor creates human confirmation. The dormant boundary's synthetic contract tests do not represent an implemented Requirement processor.

## 5. Local engineering checks

Use the existing environments described in [ENVIRONMENT.md](../../../ENVIRONMENT.md#system2-development-and-local-parsing). No new dependencies or System3 environment are introduced by this material route. From the workstream root:

```sh
(
  cd system2
  PYTHONPATH=src .venv/bin/python -m pytest tests/test_material_reader_parser.py
)
(
  cd workbench
  node --test tests/materials-ui.test.mjs
)
```

The isolated browser fixture uses the actual Workbench application, HTTP handler and System1 adapter with separate engineering stores. It includes copied public HTML/PDF snapshots plus clearly labelled synthetic HTML, XLSX and native/scan/blank PDF sources. It does not apply real reviewer decisions. Build only when its fixed target directory does not exist:

```sh
system2/.venv/bin/python workbench/scripts/material_fixture.py
workbench/.venv/bin/python workbench/scripts/serve_material_fixture.py
```

The builder intentionally refuses an existing `workbench/runtime/human-led-acceptance/` directory. Do not delete prior evidence to repeat the command. An already-built fixture can be served without rebuilding. The fixture server prints its loopback URL and records it in that directory's `server.json`; no machine-specific port is part of the contract. Only its material worker runs. Stop it after isolated testing and keep its saved evidence separate from normal business review.

Tests and generated artifacts establish only their checked behavior. Runtime activation, browser coverage, source preservation, conflict/recovery verification and goal acceptance belong in dated state and acceptance records.

## Offline collaboration extension (2026-09-12)

The [offline human review contract](../../../docs/design/offline-human-review.md) adds named personal drafts and explicit main adoption. Workbench mutation requests now require `X-Material-Workbench: 3`; older UI writes are refused. This HTTP compatibility marker does not change the material document schema or manufacture historical acceptance.

| Interface | Result |
| --- | --- |
| `GET /api/collaboration/state` | Workspace mode, coordinator, selected-source catalog and submission inbox |
| `GET /api/collaboration/source?source_id=…` | Named person's source proposal and draft revision |
| `POST /api/collaboration/source-save` | Partial personal source save guarded by `expected_revision` |
| `POST /api/collaboration/work-export` | Work ZIP, coordinator only |
| `POST /api/collaboration/submission-export` | Immutable saved personal submission ZIP |
| `POST /api/collaboration/import` | Bounded raw ZIP validation and separate intake receipt |
| `POST /api/collaboration/prepare-own` | Coordinator's own saved personal proposal as merge preview |
| `POST /api/collaboration/preview` | Common-base/current/incoming comparison |
| `POST /api/collaboration/resolve` | Saved per-difference current/incoming/edit choices |
| `POST /api/collaboration/adopt` | Explicit source-first/main-material adoption with independent receipts |
| `POST /api/collaboration/confirm-master` | Explicit exact-version whole-content confirmation |
| `POST /api/collaboration/machine-preview` | Machine candidate compared to personal content |
| `POST /api/collaboration/machine-resolve` | Personal per-difference choice |
| `POST /api/collaboration/machine-apply` | Explicit personal candidate resolution, never main adoption |

`GET /api/material?id=…` uses the current named personal workspace. `view=master` selects the main or imported baseline explicitly. Corresponding reader/history/original paths preserve that view. Source-only review offers its bound original separately.

Comparison output includes `merge_id`, the input/master digest, `differences`, `unresolved`, proposed material/source values and provenance. Differences have stable IDs, JSON-pointer paths, common/current/incoming values and presence flags. Decisions are bound to the saved comparison and its input digest, not transferable merely because a path ID matches. Generic JSON comparison/provenance is available for future use; no third-pane Requirement business schema or Process execution is connected.

Adoption requests use canonical UUIDs. Changed payload reuse is rejected; a persisted exact request is replayed across response loss/restart. Source `saved_partial` is distinct from `applied`; the overall response is `adopted_partial` when a source proposal remains incomplete. Content adoption always leaves global content confirmation separate. Errors and version conflicts do not erase prior choices, submissions or main history.
