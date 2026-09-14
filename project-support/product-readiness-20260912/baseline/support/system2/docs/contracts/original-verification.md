# Original-page verification contract

Status: implemented bounded local mechanism; not independently calibrated source acceptance. The [aligned target](../../../docs/design/requirement-workstream-target.md) owns the broader verifier requirement. [Checkpoint evidence](../reports/32-original-page-verifier.md) identifies the tested scope.

## Standalone interface

From the System2 directory, using its existing environment:

```sh
PYTHONPATH=src .venv/bin/python -m pdf_extraction.verification.original_cli \
  --original /path/to/registered-original.pdf \
  --records /path/to/located-effective-records.json \
  --page 19 --language eng --output /path/to/comparison.json
```

`--page` is one-based; internal `page_index` is zero-based. `--parser-engine` may be repeated to disclose shared extraction engines. Without supplied lineage, the report explicitly retains `extraction_lineage_unknown`. An output record is a JSON object containing `id`, `unit_id`, `text`, and `references`; each reference binds `page_index` and `bbox`, with optional `coord_origin`. PDF point boxes use top-left origin by default; supported normalized and bottom-left boxes are converted for comparison. The CLI reads the original and supplied records; it does not load the workflow, edit Canonical or accept a source.

The reusable `compare(original_page, records)` function accepts located original-side lines plus raster regions and emits located differences, source snippets, severity, source/output unit associations, unverified scope, and a null confidence. Poppler TSV acquires native words. A raster of the entire page is locally OCR-probed, including areas without an extraction record, followed by residual-ink detection. Original images or table bounding boxes never exempt a whole scanned page. Photos/diagrams are not transcribed into effective results; unclassified raster evidence asks a human to inspect its role. No API is required.

A positioned token comparison detects missing words and critical missing numbers/negations. Method `original-page-comparison/2` retains numeric separators, component order and signs, and adds output-to-original comparison for extra words/negations. Equal-token, single-original-line records also receive a token-order check. Both directions of one located issue are grouped while retaining their separate evidence, to avoid duplicate human alarms. Tokenization conflicts and text fragmented across records stay visible. Multi-page records without page-partitioned text retain an explicit reverse-comparison scope gap.

These are bounded discrepancy signals, not independently established insertion/order accuracy. Broad or ambiguous positions, multi-line reading order, table grid/merged cells, footnote ownership, cross-page relationships and illustration role remain unverified. Native and OCR acquisition can share engines with extraction; that is disclosed and does not establish independence. An empty finding list with unresolved scope cannot auto-pass. [Checkpoint 41](../reports/41-pdf-verifier-critical-differences.md) separates seeded development controls from unlabelled natural candidates and independent acceptance.

## Occurrences and spatial ownership

Method `original-page-comparison/3` adds spatial token-capacity checks: one output occurrence cannot explain several original occurrences. Per-engine maximum assignment retains ambiguity about the exact missing position instead of inventing an alignment. Shortfall findings carry counts and all implicated original regions. Several output records claiming the same separate parallel text yield a localized `output_spatial_ownership_ambiguous` scope item, not a proven table-error label. The workbench can highlight every region and open each affected content item. [Checkpoint 42](../reports/42-pdf-occurrence-and-spatial-ownership.md) records controls, false-prompt diagnosis, browser-component evidence and limits.

This is not independent table, reading-order, footnote or cross-page verification. Global unverified scope remains until supported evidence resolves it. Unknown scores and unresolved located scope continue to block automatic delivery.

## Workbench transaction

Method `original-page-comparison/4` adds `record_kind: "structure_only"` packets with `structure.schema: "pdf-output-structure/1"`. They retain effective grid dimensions, cell indices/spans/header status, source regions and text fingerprints, row ownership, hierarchy/order, typed links with target evidence, and logical table definitions/fragments. Ordinary text records remain compatible. Structure packets cannot account for missing original text. The CLI accepts these packets in the same records list; omitted structure cannot establish structural correctness.

The bounded checker detects grid/claimed-position contradictions and invalid or physically reversed assemblies. These are explicitly output self-consistency signals, not independent source-table recognition. Same-table/axis conflicts are grouped while retaining each conflicting pair. Typed note/context links and cross-page assemblies retain localized unverified source-relationship scope even when structurally consistent. Unknown packet schemas also remain unverified. [Checkpoint 43](../reports/43-pdf-structure-bound-verification.md) owns seeded controls, real-page limits and transaction evidence.

`POST /api/system2/verify-page` accepts only `request_id`, `document_id`, `revision`, `source_sha256` and `page_index`. The server validates loopback origin/CSRF, binds the current named operator, and resolves the source through the governed System1 snapshot. Browser file paths are forbidden. The actor requests a machine check; this is not a human source approval.

Acquisition/comparison happen outside the write lock. The transaction rechecks source hash, current document revision and the exact effective-input digest. Replayed identical request IDs return the saved receipt; conflicting IDs or changed source/results fail. A page coverage task is created even when the parser emitted no content. Findings and unverified scope become actionable blockers. Only that check's prior machine blockers are replaced; unrelated human issues and history remain.

The database owns the report/event, page state, receipt and current version. Exact original-side observations and effective comparison inputs are retained under workflow `source-verification/<sha256>.json`, linked by digest. An interrupted or stale transaction may leave an unreferenced evidence file; only the committed event has authority. Original source files and Canonical are unchanged. Reports retain tool versions and evidence hashes. `elapsed_seconds` covers the precommit comparison phase, not complete HTTP acknowledgment or Excel generation.

Effective text, location, grid/span/row assignment, hierarchy/order, typed target or assembly changes mark affected checks stale and invalidate downstream acceptance. This includes changed content on another page of the linked assembly. Review-only version increments are excluded from the semantic digest. A changed comparison method likewise marks an earlier report stale on reconciliation; its prior report/history remains retained. The stale blocker cannot be cleared by generic issue resolution; re-run the original-page check. Human inspection can resolve specific findings with source evidence, without claiming uncalibrated machine confidence. Current conservative hydration loads the source for checked-document workflow operations; a future complete original-region dependency index should reduce this cost.

## Human path and output

Use System2 → Pending review → Content proofreading → Inspect original PDF pages. `Check this original page` saves a version-bound comparison. The original remains on the left and extracted content/context on the right at desktop widths. `Locate original region` highlights its page position; enlarge it to inspect small text. A missing-text suggestion can fill an unsaved correction draft. Confirm the exact full text and location before submitting; recognized words are suggestions, not reference answers.

A correction can be saved while A/B review remains pending. Rechecking and accepting are separate actions. Resolved items move to history through existing acceptance rules; drafts, errors and unresolved scope do not become completed review.

Excel uses a background snapshot with an event and policy version. The displayed statuses distinguish saved decisions, pending, synchronizing, synchronized, failed and unknown status. Failures survive service restart, and the existing background worker retries. Cached downloads must match the snapshot hash/version; concurrent replacement or inconsistent bytes cause a retry response. Saving and normal reads do not generate Excel synchronously. Source governance follows the database authority and migration evidence recorded in [System1's current state](../../../system1/PROJECT_STATE.md).
