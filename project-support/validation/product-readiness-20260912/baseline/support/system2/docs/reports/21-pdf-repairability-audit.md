# PDF repairability audit and proposed next checkpoint

Date: 2026-09-09. Status: design for user discussion, not implementation approval.

The active goal is source-faithful extraction with discoverable and repairable remaining errors, effective structured corrections, and acceptable review effort. Automatic perfection is not required. System3 retains semantic completion. No parser, review implementation, production decisions, thresholds or artifacts were changed by this audit. Diagnostic renders and an isolated temporary workflow were used; no new PDF parsing was started.

## Verified implementation and runtime evidence

- `review/workflow.py` provides original-preserving field edits, named transactions, receipts, drafts, reopen, supplement, split/merge and a resolved-unit projection. Existing dependency edges participate in classification invalidation and delivery suspension.
- `models/document.py` supports block type, parent/children, order, heading/list levels, segments, table cells/spans and content links. The machine pipeline contains hierarchy, footnote and cross-page handling, but feature existence is not accuracy evidence.
- Production CS004 has 134 processed pages, 45 Canonical windows and 4,332 review units. 4,287 units have chapter `Original order`; 45 have `Source completeness`. Kind counts: 2,898 source_text, 1,255 context, 133 standard_indicator, 46 coverage. These counts include window overlap and are not unique source-content or correctness counts.
- Across the 45 Canonical artifacts, 158 blocks carry heading_level and 43 carry content_links. The current PDF review projection does not carry those fields, parent/children or reading-order links. It maps most block types to source_text and checks `note`, whereas the Canonical enum uses `footnote`. Tables retain geometry but produce separate table and row views without an editable shared cell model.
- The actual local profile uses docling-parse, heuristic layout, native tables and Tesseract; external models and heavier table recognition are disabled. Optional code paths must not be described as enabled production capability.
- Visual inspection of the existing CS004 source pages 20–21 found a concrete pilot range: numbered table rows 2.1.3 and 2.1.4, explanatory paragraphs continuing to the next page, superscript markers 7–12, footnotes and a repeating document-information footer. This identifies validation cases, not extracted-text accuracy acceptance.

## Reproduced gaps

A temporary Workflow using existing test constructors exercised real decision handlers, without production writes:

1. Adding a notes relationship pointing to an existing note stores `reviewed_structure`, but leaves dependencies at `[coverage]`. After accepting/classifying the clause, correcting the note leaves that clause published. Relation edits need executable graph semantics, not merely a stored role/locator.
2. Supplement at `page 20: 10,20,100,200` appends a source_text unit with no chapter and only a free-text locator, without structured page_index/bbox. The PDF preview selects page 0 when no page_index exists. Supplement position, insertion order and evidence resolution are not a reliable closed loop.
3. Reprocess retains a retired_generation event and human history but empties current units. There is no local reparse candidate, diff, conflict resolution or human-overlay merge.

Code tracing also confirms:

- Current PDF preview shows the first referenced page. Coverage displays counts of existing units, not a page-region inventory. There is no integrated clickable page overlay or source-first missing-region review.
- Changing structure does not change unit kind, parent, order or table-cell geometry. The role/locator list has no typed relation validator. Text `level` is not a working hierarchy editor.
- Split/merge requires accepted content, uses text input/IDs, copies broad evidence and appends children. It does not reconstruct complete table/footnote/ordering semantics; accepting known-broken structure should not be a prerequisite for repairing it.
- There is no normal duplicate suppression with provenance, typed table editor, structural undo or version restore. Reopen/drafts/history alone do not provide these capabilities.
- Delivery uses `Workflow.resolved()` for references and structure; Excel reads original references and separately builds table rows. Corrected-location consistency is therefore incomplete. Browser table text and raw table content also have separate representations.
- The retained standalone PDF review service writes its Canonical path and derived artifacts. It must not be used against immutable active source facts as a workaround for missing normal-workbench controls. Compatibility should delegate to the common overlay service or use explicit diagnostic copies.

## Minimal proposed design

Reuse the local parser stack, existing SQLite, original Canonical schemas and current workbench. Do not introduce another database or model provider.

1. **One effective structured document projection.** Original PDF and Canonical remain immutable. Versioned patch operations target stable content, cell, relation and evidence identities. A shared resolver applies patches for browser, Requirement extraction, Excel and delivery. A corrected table cell has one effective value across table, row and Requirement views. Preserve machine-original and human-added provenance separately.
2. **Executable typed operations.** Support edit/insert/suppress-duplicate; change type, parent, level and order; split/merge source boundaries; edit table cells/rows/columns/spans and continuation links; attach/detach notes/references; adjust one or multiple page regions. Unresolved targets remain explicit. Validate ranges, cycles, text preservation, table occupancy and references. Validation checks consistency, not source truth.
3. **Scoped invalidation.** Compute affected old and new neighborhoods from typed relations. Invalidate the relevant content/structure, coverage and Requirement checks; immediately suspend affected deliveries in the same transaction. Preserve unrelated confirmations. Record every affected target and complete before/after operation state in receipts, including all split/merge children.
4. **Three discovery modes inside Content proofreading.** Pages for coverage, outline for hierarchy, and issues for efficient repair. These are views of the same content, not new independent queues. Keep Requirement judgment as the second stage. Provide original-page overlays, adjacent pages, multi-page ranges and associated headings/notes/tables. Reviewers can select an unmapped original region and insert content directly at its proper location.
5. **Safe reparse and restoration.** Parse only a chosen region/page window plus necessary context into a candidate version. Compare old machine result, new machine result and current human overlay; unchanged identities retain work, ambiguous matches and competing edits require decisions. Restoring an earlier version creates a new patch revision, never deletes history or overwrites intervening work.

Coverage must distinguish observed source regions, mapped regions, reviewed ranges, explicit exclusions and unresolved gaps. Neither no issue reported nor a filled coverage bar establishes accuracy. Numbering and indentation are source structure; source-unsupported interpretation remains unknown.

## Proposed staged evidence gates

### 1. Prove correction-to-output integrity first

Use the existing CS004 pages 19–21 plus adjacent context as needed. Establish a small source-checked expected result. Reproduce and fix a shared footnote reassignment, a missing-region insertion and one table-cell correction. Verify all browser/table/Requirement/Excel effective values and locations agree, related deliveries suspend, independent approvals survive, and a restore returns the expected structure. Include stale requests and exact replay. Do not claim the stage passed while any of these requires editing database/JSON outside the workbench.

### 2. Prove human discovery and structural repair

Add page/outline/issue views and only the editors required by observed cases. Test numbering, reparenting, reading order, duplicates, split/merge, merged cells and cross-page table/note relationships. Preserve uncertain cases. Include natural defects and separately labeled injected defects that are absent from the machine queue; the latter measure discovery, not parser quality. All selected source ranges must be inspectable even when machine diagnostics are empty.

### 3. Prove reparse, restoration and broader transfer

Reparse a reviewed region with a changed machine result; test unchanged replay, conflicting text, changed boundaries, shared-note dependents and interruption/restart. Human patches may not disappear or silently attach to a different region. Then use held-out ranges from another real complex PDF and an authoritative Norwegian PDF; scanned/mixed content requires its own evidence. Do not generalize from English tables to all PDF types/languages.

## Evaluation before widening scope

Report automatic text errors (including digits/symbols/negation), missing/duplicated content and hierarchy/table/note relation errors separately. Count natural errors against an independently source-checked reference, not the parser output. Report critical-error discovery separately from all-error discovery and distinguish injected challenges.

For human work, measure active time, median/p95 per repair type, clicks/context switches, completion/abandonment and unresolved tasks; compare the same kind of source range with manual transcription/organization. No acceptable-time claim is established yet. Set operational workload thresholds after the first small measured pilot with the user.

The pilot requires every seeded critical error and every known source-checked critical defect in the selected range to be repaired or explicitly unresolved, with no incorrect accepted output or stale downstream record. Expand only after zero unresolved engineering defects in these paths. Do not interpret passing this bounded sample as whole-document accuracy or machine-confidence calibration.

## Historical decision pending at audit time

Recommended next action after user agreement: stage 1, centered on effective structured results and dependent invalidation, before adding model/tool capacity or running another complete large PDF. The active goal remains pending design agreement, not blocked and not complete.

Update 2026-09-10: the user confirmed this design. Stage 1 implementation and the bounded real-source repair experiment are recorded in [the next checkpoint](22-pdf-repair-pilot.md). The audit above remains evidence of the pre-implementation state.
