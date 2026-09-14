# Indexed human review contract

Version: `system2-tasks/2`, storage version 2. This extends [two-stage review](two-stage-review.md), preserves compatibility readers, and governs the normal browser.

## Queues and scope

Pending review contains Content proofreading and Requirement judgment. A unit with unaccepted content belongs to the first queue. A unit with accepted content, satisfied dependencies and an unaccepted Requirement decision belongs to the second. Accepted content with blocked dependencies is waiting, not duplicated in actionable counts. Coverage/structure findings are subtypes; original problems are linked System1 source tasks. History retains applied decisions independently of the queue.

Complete source-position groups preserve every member's original ID, fields and references. Table grouping retains rows without treating individual cells as human tasks. Numbered source clauses remain intact. Human-touched identities are never widened by migration. Uncertain relations must stay unresolved. Canonical remains the original fact source; review text/position corrections are versioned overlays.

## Reads

| Route / query | Response |
| --- | --- |
| `/api/system2/state?view=summary` | Source versions, state, actionable/waiting/published counts; no units |
| `view=tasks&document_id=...&stage=content` | First-stage summaries, 50/page, source-wide stage counts |
| `view=tasks&document_id=...&stage=requirement` | Second-stage summaries; content/dependency gate enforced |
| `view=unit&document_id=...&unit_id=...` | One unit, required evidence, machine explanation, coverage summary and guard |
| `view=history_page&document_id=...` | Applied history, 50/page |
| `/api/system2/preview?document_id=...&unit_id=...` | Hash-bound isolated original region; `full=true` expands context |
| `/api/system2/export-status` | Last export version and background status |
| `/api/system2/workbook?cached=true` | Last generated Excel snapshot, without synchronous regeneration |

Task filters: `offset`, `query`, `chapter`, `task_type`, `include_reviewed`, `stage`. Normal lists exclude waiting and accepted items. Technical details, full body and screenshots are not list payloads. Compatibility `view=browser`, `view=history` and the unqualified bridge state remain available but are not the frontend loading path.

## Writes and recovery

A review request binds named server actor, canonical UUID, document/unit IDs, source hash, policy revision and a guard over source generation, Canonical set, unit and dependency fingerprints. Different independent units can be edited concurrently; the old document-revision guard remains for legacy clients. Identical replay returns the original receipt. Decisions and delivery events are in one SQLite transaction. Successful application returns a fresh guard.

Drafts persist locally and in System2. First edit claims a protected server draft; uncertain requests retain their UUID. A stale draft needs explicit comparison, and stale writes are rejected. Resolving a subset of findings leaves the remaining findings pending. Text correction, structure correction and source-region correction are separate operations. A region correction changes a reviewed reference overlay and requires rechecking; it never modifies original text or files. Split/merge preserve source boundaries, not minimal obligations.

`POST /api/system2/source-issue` creates an idempotent, named System1 task bound to the exact source version. System2 mirrors its unresolved status and suspends related delivery. It does not repeat source admission. Policy reduction cannot erase unresolved human reports, drafts or structure failures. Valid same-version human acceptance survives threshold changes.

## Effective PDF repair extension | 2026-09-10

Unit detail includes `effective`, `table_owner_fingerprint` and `repair_history`. `review/effective.py` resolves original facts plus versioned overlays for browser, Requirement classification, Excel and delivery. Source/Canonical files remain immutable. A table owner stores `cell_edits` once; row views derive their selected cells. Delivery includes related source content and `table_scope` (`whole_table` or `selected_cells`).

The existing guarded decision endpoint accepts these additional actions:

| Action | Additional request fields | Effect |
| --- | --- | --- |
| `relation` | `target_unit_id`, `target_fingerprint`, `role` (notes/context/reference), `mode` (attach/detach) | Effective relation and dependency; reject cycles/stale targets |
| `table_cell` | `table_owner_id`, `target_fingerprint`, `cell_id`, `text` | Shared cell text correction; reopen affected views |
| `use_table_values` | `table_owner_id`, `target_fingerprint` | Explicitly discard conflicting old row text overrides in favor of shared corrected cells |
| `supplement` | `fields`, `locator`; optional `insert_after_id`, `anchor_fingerprint` | New human-provenance content in source order with structured PDF page/bounds |
| `restore` | `restore_request_id` | New revision restoring supported pre-repair overlay values, rejecting later conflicts |

All require the existing named actor/request/version guard; structured repairs require original-evidence reasons. They invalidate affected acceptance and suspend existing dependent delivery in the same transaction. A receipt returns a fresh guard and `unit_fingerprint`. Repair history stores before/after overlays and affected IDs; supplementation records `created_units`. Original machine confidence is not rewritten.

Generic whole-row text correction cannot bypass shared table cells. Unresolved old row overrides create `human_table_text_conflict`, which a generic resolved confirmation cannot clear. The initial repair extension covered cell text; later geometry and boundary extensions below add structural correction. Legacy dependency edges can still be broader than required. Evidence and limits are in [the pilot report](../reports/22-pdf-repair-pilot.md).

## Storage and deployment details

### PDF original-page discovery and scope

`view=pages&document_id=...&offset=...` returns up to 50 original-page summaries, including unprocessed/empty pages. `view=page&document_id=...&page_index=...&offset=...` returns up to 50 mapped unit summaries with region geometry, current fingerprints and a page-completeness task. `page_index` is zero-based and range checked. These reads include accepted content independently of queue filters. Counts are mapped units, not source accuracy. `preview` accepts a bound document plus `page_index` without a unit; full-page render returns physical width/height for the shared image/overlay coordinate surface.

`pdf-pages/1` coverage edges use effective page positions and bounded parser ranges; multi-page/shared-content dependencies survive. Unknown scopes and human findings cannot disappear through localization. Original broad completeness records remain part of overall source completion. `review/migrate_pdf_scope.py` supports preview and explicit backed-up application at a stopped-write checkpoint, preserving originals/history and invalidating changed acceptance. Position repair and supplementation refresh page dependencies and reopen affected completeness checks. The [page-discovery report](../reports/23-pdf-page-discovery.md) records production cutover and current limits.

### PDF source hierarchy and order

Documents with `hierarchy_version=canonical-hierarchy/1` expose `view=outline&document_id=...&parent_id=...&offset=...`. Omitting `parent_id` selects the source root. Responses contain up to 50 child summaries, child counts and a parent trail. Source containers reference immutable Canonical blocks; their page labels are not semantic chapter verification. Coverage objects cannot be source-content parents.

`hierarchy` decisions accept a `hierarchy` object containing `type`, `heading_level` (1–6 or null) and/or `parent_id` (current content ID or null). A selected parent requires its current `target_fingerprint`. `reading_order` decisions require `target_unit_id`, `target_fingerprint` and `mode=before|after`; moving a parent moves its effective descendants. Both require an evidence note and the existing named request/source/Canonical/dependency/policy guard. They preserve raw facts, reopen affected acceptance and suspend affected delivery atomically. `hierarchy_parent_after_child` cannot be dismissed by generic issue resolution.

Effective details and delivery include hierarchy, ancestor summaries and an exact rational-string `reading_order_key`. The source order and Canonical tree remain distinguishable from `hierarchy_edit` and human order patches. Supported history restoration restores these overlays without overwriting later conflicting repairs. General boundary replacement and reparse conflict merging are not covered by this extension. `review/migrate_hierarchy.py` performs a backed-up projection migration at a stopped-write checkpoint. See [real-source validation](../reports/24-pdf-hierarchy-repair.md).

### Source-boundary merge extension

For hierarchy-projected PDF documents, `merge` accepts ordered `merge_ids`, `merge_fingerprints` for every non-primary target and an explicit `hierarchy` (`type`, nullable `heading_level`). It requires the existing guarded actor/request/evidence note but not prior content acceptance. Only adjacent current non-table text under one source parent can be merged; metadata conflicts remain explicit errors. The primary identity survives. `boundary_sources` and `boundary_request_id` record provenance, `edits`/`reviewed_references` express the effective content, and other originals receive `superseded_by` pointing to the survivor. Current navigation and completion calculations exclude replaced fragments while history and Excel preserve them as superseded.

Incoming parent/reference/dependency edges are redirected and affected acceptance/delivery invalidated in the same transaction. Restoration uses before/after patch states and rejects later conflicting edits or new incoming relationships. [Real-source merge validation and limits](../reports/25-pdf-boundary-merge.md).

### PDF source-preserving split

For hierarchy-enabled text, `action=split` uses `split_spec`, not the legacy `split_parts` path. `parts` contains at least two objects with `text`, `type`, optional `heading_level`, and nonempty `reference_indices` into the current effective references. Concatenated text must equal the current body exactly. `fields` maps each nonempty non-body source field to part indices; `identifier` has one destination. `outgoing` maps typed-link indices to destinations. `incoming` maps related unit IDs to their current `fingerprint`, a single `parent` destination when applicable, and `links` keyed by original relation index. Unit detail supplies the required choices in `split_context`.

Results receive stable request-derived identities and version-bound character ranges within retained original evidence; original source units become superseded records. Their children and references follow explicit assignments. Untyped dependencies preserve the original range. No part becomes accepted by splitting. The same transaction retains history and invalidates affected delivery. Restoring from either child preserves history and rejects conflicting later edits or new incoming relationships. Table geometry is deliberately outside this action. [Split validation and remaining gates](../reports/26-pdf-boundary-split.md).

### Existing PDF table geometry

Complete table details include `table_context` with the effective grid, owner fingerprint and existing row items/fingerprints. `action=table_geometry` requires `table_owner_id`, `target_fingerprint` and `table_geometry={row_count,column_count,cells,row_bindings}`. Every current cell ID must occur exactly once with zero-based `row`, `column`, positive `row_span`, `column_span` and boolean `is_header`. The grid must have no overlaps or out-of-range cells. Uncovered positions fail unless `allow_incomplete=true`; then `human_table_grid_gaps` blocks acceptance until the missing positions are repaired. Every existing row item requires an explicit `{row,fingerprint}` binding; duplicate row bindings and implicit row creation/retirement are rejected.

The operation preserves original cell text and evidence, updates effective row references/order, invalidates related review/delivery and records reversible patch states in one transaction. Effective HTML and structural projections are regenerated from the corrected grid. Existing text corrections that conflict with table-derived fields remain explicit blockers. Missing-cell and cross-page boundary operations are not implemented by this endpoint. [Geometry checkpoint and remaining work](../reports/27-pdf-table-geometry.md).

### Persistence

System2 SQLite owns document metadata, indexed `review_units`, dependency edges, applied history, request receipts and the delivery/event stream. Original/Canonical/screenshot artifacts stay in file storage. Compatibility document objects are hydrated only when required by legacy calls, broad graph operations or export. Changed row fingerprints avoid whole-source rewrites. Browsing never starts parsing or export.

Migration requires a stopped-write checkpoint, worker/export locks, an exact SQLite backup and a validated production copy. Preserve member maps and historical target/evidence versions. Only one normalized current state is authoritative after cutover; backups are rollback evidence. Do not delete original inputs, Canonical or historical decisions.


### PDF table-cell boundary extension

`action=table_cells` requires the complete owner guard, `table_owner_id`, `target_fingerprint`, a complete `table_geometry` and `cell_change`. Current derived rows retain explicit fingerprinted bindings.

- `mode=split`: one current `cell_ids` entry and `parts=[{text,reference_indices},...]`. At least two parts concatenate exactly to current text. Every part selects retained original regions; provenance stores Unicode code-point character ranges.
- `mode=merge`: at least two ordered unique current `cell_ids` and `separator` equal to an empty string, space or newline. The result preserves selected text and regions.
- `mode=supplement`: empty `cell_ids`, `text` and a bound PDF `locator` of the form `page N: x0,y0,x1,y1`. Blank original cells may be represented explicitly.

The proposed geometry retains unaffected cell IDs and uses `new:0`, `new:1`, etc. for newly created cells. Server-assigned identities are stable for the request. `reviewed_cells` is the effective overlay; `table_cell_history` retains replaced cells. Original Canonical cells remain immutable. Validation, history, row refresh and affected-delivery invalidation share the decision transaction. Generic issue resolution cannot clear `human_table_grid_gaps`.

`GET /api/system2/preview` optionally accepts `cell_id`, the current unit `guard` and zero-based `region_index`. The server resolves the evidence from the current effective table; stale guards, retired cells and invalid region indices fail. Client-supplied arbitrary regions are not used by this preview. Browser preview, effective output and history distinguish original regions from corrected text. Existing row identities are preserved; row creation/retirement and separate-table joins require subsequent explicit operations. [Validation](../reports/28-pdf-cell-boundaries.md).


### Explicit table row identities

`action=table_rows` requires a complete table owner, existing named request/guard, `table_owner_id`, `target_fingerprint`, evidence note and `row_change`:

- `{mode:"create",row:N}` creates one missing item from current cells covering zero-based row N. Existing items cannot be silently replaced. Request-derived `table-row:` identities retain source provenance and inherit `evidence_only`.
- `{mode:"table_only",row:N}` assigns a row without an independent item to whole-table review. It does not accept or classify the row. `table_row_dispositions` records the evidence reason and request identity; unresolved row scopes create `human_table_row_gaps`.
- `{mode:"retire_duplicate",unit_id,fingerprint,replacement_id,replacement_fingerprint}` requires two current same-owner, same-cell, same-row items with matching effective text and typed relationships. Drafts/staleness/conflicts fail atomically. Incoming edges are redirected; originals remain superseded history; affected acceptance and deliveries reopen.

Row creation/retirement is included in repair patch history and guarded restoration. Created items are returned in `created_units` and retain stable `created_ids`. Table detail includes `table_context.row_dispositions`; effective views expose `table_row_dispositions`. Cell geometry edits still require a valid whole grid and current row bindings. Remaining row gaps cannot be resolved through a generic acceptance request. Separate-owner tables and arbitrary cell deletion require additional source-boundary operations. [Validation and remaining gates](../reports/29-pdf-row-item-repair.md).


### Shared table-row values and relationships

A selected row exposes `table.selected_row` (zero-based), source cells with original coordinates/spans, and a one-row HTML view. Row fields follow column order even when a cell begins in an earlier row. Whole-table HTML retains the full source grid.

Explicit complete-table `content_relations` are inherited by row effective views and delivery, deduplicated against direct links and marked `inherited_from_table`. Related content follows effective source order. Table-wide notes enter row `fields.notes`; their source records, versions and references remain in `related_content`. Correcting the target reopens affected acceptance through the existing dependency graph. A row cannot silently detach an inherited relationship; edit it at the complete table.

Task summaries include the scalar `evidence_only` flag without embedding full source data. It labels window evidence copies in target choices. Excel render version 10 shows them as `Evidence only`, never Available. This presentation is not primary/halo reconciliation or acceptance. [Real shared-table validation](../reports/30-pdf-shared-cells-and-notes.md).

## Cross-page PDF table overlay

The guarded `table_assembly` action accepts an ordered `table_assembly.fragments` list of `{unit_id, fingerprint}`, `header_source_id`, and explicit `header_cell_ids`, plus the ordinary actor/source/policy/request guards and an evidence note. It currently requires primary PDF tables on nonoverlapping pages with equal column counts and human-confirmed matching column order. All physical rows are retained; it does not suppress repeated headers or combine partial rows.

A created `source_table_assembly` is context-only. Its effective `table_scope` is `cross_page_table`; cells carry fragment-scoped IDs plus `source_table_id`, `source_cell_id` and `source_row`. The physical originals remain authoritative. Existing row views and delivery records include assembly identity/version, fragment versions/ranges and source-backed `column_headers`. Local footnotes retain fragment scope. Assembly dependencies gate the member rows without reversing edges into their original owners. Later row creation preserves the gate.

The normal fragment editors apply text/grid repairs. The combined view resolves those overlays at read time and displays bound original evidence per fragment. Invalidated columns/header bindings or unavailable fragments block acceptance; they cannot be dismissed through issue resolution. Guarded restore may undo the correspondence when it does not conflict with later edits or relationships. Human reopen/resolve remains explicit and separate from structural repair.
