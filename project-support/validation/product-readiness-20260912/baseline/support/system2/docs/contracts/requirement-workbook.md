# System2 Excel requirement register

Schema: `system2-requirement-workbook/1`.

`System2_Requirement_Register.xlsx` is the maintained Excel carrier for System2 results. It has one worksheet per source document, named by stable System1 source ID, plus `Source Index` and `Read Me`. A source containing many clauses still has one sheet. The index links to each source and reports processing state, source completeness, content-unit count, pending-unit count and available Requirement count.

## Authority and scope

Canonical remains the original-fact authority; Workflow owns versioned corrections, acceptance and delivery state. Excel is their program-managed readback and delivery register. Make named decisions in the browser. Direct workbook edits are not imported and will be replaced on refresh. Original text and corrected current text are separate columns.

The register includes current INCLUDE sources, even before explicit processing starts, plus retained documents whose sources later become ineligible. Unstarted sources have no invented rows. Parsed units include candidates, Requirements, context, exclusions and explicitly labeled coverage checks. Only currently published units are `Available`. Withdrawn source versions and superseded fragments remain labeled; earlier reprocessing generations and full decision history remain in Workflow and the browser, not in a second mutable Excel history store.

Columns retain original numbering, body, classification, both review stages, current delivery status, context/applicability, source positions, title/criteria/level/notes, original body, separate confidence values and decision origins. Hidden columns R:AB retain unit/document identity and versions, generation, source snapshot/hash, policy revision, Canonical references, structure/dependencies and text-part sequence. Unhide them for auditing. Confidence values are routing scores, not document accuracy; missing scores stay blank and human confirmation does not change them to 100%.

## Synchronization and download

A dedicated workbench background worker attempts synchronization every 60 seconds, after the preceding attempt finishes. Display reads and saved decisions do not wait for Excel generation. Merely generating Excel does not enqueue a parser job. `workbook` in the System2 workflow adapter reconciles current sources and returns an up-to-date file receipt. The browser's `Download Excel register` link uses `GET /api/system2/workbook`, with a no-cache attachment response after policy synchronization. That explicit download may wait for a large export; browsing the review queue does not.

The standard production file lives in the System2 component root. Isolated runtimes put it inside their own runtime directory. Downloaded copies are dated snapshots. Close and reopen a desktop workbook to see subsequent disk changes. If Excel's owner lock exists, refresh waits until the file is closed. An export failure is reported as `workbook.status=pending_refresh` in browser state; it must never roll back or misreport a saved human decision. The download endpoint fails rather than serving a known stale file.

Exports serialize on a file lock, capture documents/policy/event cursor in one database read transaction, verify the System1 handoff, and replace the file atomically. An unchanged fingerprint plus workbook hash avoids unnecessary writes. Failure retains the previous complete file and the next background cycle retries. The receipt records workbook SHA256, input fingerprint, policy revision and event cursor. A snapshot is current at capture time; a downloaded attachment does not receive later withdrawals.

Source text is explicitly stored as text, never an Excel formula. Long cell values continue in numbered text-part rows with repeated identity/status. Count unique document/unit IDs, not continuation rows. XML-invalid control characters display as escaped code points; Canonical references preserve the exact original. Excel row limits fail explicitly instead of silently dropping content. Source sheet names are sanitized and bounded to 31 characters. Font ordering is normalized for Open XML schema validation.

## Full-text review carrier, 2026-09-09

PDF effective hierarchy extension, 2026-09-10: visible Parent content, Heading level and Reading order columns reflect the same correction layer as the browser and downstream output. Moving content changes export order; restoration creates a later snapshot with the restored order. Table parent labels use bound page references instead of embedded structure JSON. Source originals and historical snapshots remain unchanged. [Validation](../reports/24-pdf-hierarchy-repair.md) covers a bounded real-source workbook and native Excel inspection.

The browser uses background snapshots (`workbook?cached=true`) with an export-status version. Each source sheet retains titles, clauses, context, notes and full tables, including undecided content. Tables use logical rows with a shared Unit ID. Unit type and the latest named decision are visible; technical identity, member/dependency counts and Canonical hashes are hidden provenance. The database holds the full member/relationship graph; it is not copied as large JSON into each table row. Long text has explicit continuation parts, with no silent truncation. Review authority remains the browser and System2 receipts. See [v2 acceptance](../reports/20-review-workbench-v2.md).

Retained window evidence copies use the visible delivery label `Evidence only`. They retain source content and history but cannot be independently Available. Table row output includes explicitly table-wide notes and shared cell values in source column order; the original grid and references remain authoritative evidence.


## Source-version status | 2026-09-10

Controlled reconciliation writes the replaceable `source-version.json` marker. It records successful/unknown checking, timestamp, source digest and digest kind. Output metadata includes `registry_sha256` and `registry_kind`; Read Me distinguishes a workbook-file identity from a `sqlite_snapshot`. The workbench compares these with saved event/policy versions, and the same background coalescing/retry process handles source-only changes. Missing, failed or older-than-30-second checks are unknown. Thirty seconds is an operational freshness default, not an accuracy or acceptance threshold. A previous coherent download remains available with its own metadata while newer output is pending or failed. Source markers are not an alternative authority or an Excel readback path.

## Provisional B subdivision rows

Renderer 14 adds linked B rows while preserving the full A parent. Original number, generated label, parent ID, additive count, provisional policy, exact accepted-text span and unassigned-text rationale are distinct columns. Counted deliveries alone use `Available`; parent/subitem context rows identify that they are not counted. Continuation rows have zero additive count. Workbench/source-index totals and the delivery feed use the same saved per-parent counting policy. See the [subdivision contract](requirement-subdivision.md); no Excel changes are imported.

Renderer 16 also includes a Weekly checks sheet when A/B sampling tables exist. It reads batches, frozen items, initial verdicts and inspection histories in the same database transaction as current source results. Explicit shortfall and missing-class details remain visible; resolving a finding does not overwrite its initial verdict. Long fields continue across rows, and evidence notes receive expanded row heights. The [monitoring contract](weekly-original-sampling.md) defines the pending/history and activation boundaries. An empty or disabled normal sampling configuration is not a completed batch.
