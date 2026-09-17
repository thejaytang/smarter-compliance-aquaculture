# PDF row-item repair checkpoint

Date: 2026-09-10. Decision: `CONTINUE`; source-preserving row identity repair is implemented, while separate-table correspondence, safe local reparse and broad repairability acceptance remain open.

## Effective behavior

A missing independent row item can now be created from the retained cells of an existing table row. No cell text is generated. The item receives a request-derived identity, original-region references, table parent, source order and provenance. Subsequent cell corrections continue to feed its effective fields. It starts pending. Evidence-only table ranges pass that restriction to new row items, preventing overlap evidence from becoming deliverable Requirements.

A row can explicitly remain within the whole-table review instead of receiving an independent item. This records review scope, not a non-Requirement classification. Once row scope is being repaired, remaining unassigned rows create `human_table_row_gaps`; generic issue resolution cannot dismiss it. The effective table and output retain all cells and the explicit disposition record.

Duplicate row retirement requires two current items belonging to the same owner and covering the same effective cells and row. Different text or typed relationships must be resolved first. Drafts and stale versions are protected. The retired original remains historical; incoming references, parents and dependencies move to the retained item. The retained item inherits unresolved blockers and source identities. Cycle checks, invalidation and delivery suspension occur in the decision transaction. Restoration preserves history and refuses conflicting later repairs or incoming references to newly created items.

This operation manages row review identities. It does not delete arbitrary cell text or join separate table owners. Cell/grid repairs remain the place to correct source row geometry; distinct source rows cannot be called duplicates merely because they contain similar wording.

## Isolated browser verification

Source: CS004, ASC Salmon and Cod Standard v1.5, original PDF SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

The page-20 tests used **explicitly seeded row-projection faults**, not naturally observed missing/duplicate indicators. First, the original 2.1.4 row projection was made historical while its original cells remained. The browser saved and restored a draft, then recreated the independent row from those cells. The effective result retained identifier `2.1.4`, its original description and criterion `Yes`, with pending content status.

A second labelled fixture duplicated the 2.1.3 row projection. The browser explicitly selected the duplicate and retained item, applied the repair and preserved the duplicate as superseded history. The current table retained one active row per indicator. No pilot Requirements were delivered or automatically accepted by these repairs.

Final isolated source revision: 99; event cursor: 122. Artifacts under `tmp/pdf-row-pilot/` include labelled seed logic, before-state snapshots, effective row repairs and history. `repaired-page20-rows.xlsx`, SHA256 `0b3e09defc3ff9eca65d27e27a3b16e72caf333f4e99b5f53441d6106a8cb497`, contains the current 2.1.3/2.1.4 rows as `Not delivered` and replaced projections as `Superseded`. Programmatic readback verified criteria and statuses. Native Excel visual acceptance remains pending after the previously confirmed Mac lock.

## Real-source finding that changes the next experiment

Inspection of original page 123 (`tmp/pdf-row-pilot/original-page123.png`) shows nine logical rows including the header. Two retained table projections from adjacent parsing windows each report ten rows: the global-level cell spans one row too far, and the Scotland cells span two logical rows instead of one. No extra textual regulation is missing at the bottom. This is a geometry problem, not a reason to create a new requirement.

The second table projection is explicitly `evidence_only` with `overlap_evidence_only`, originating from the next window's halo. It cannot be delivered as an independent Requirement. Its repeated presentation is still a review-burden concern, but it must not be described as duplicate delivered output. The row-creation guard now preserves this evidence-only boundary, verified by a targeted test.

Next validate correction of the genuine page-123 geometry and inspect how halo evidence can be attached to a primary source range without losing differing evidence or human decisions. Use this result to guide separate-table and cross-page correspondence repair before conflict-preserving local reparse. Do not automatically delete the halo projection or treat equal rendered text as sufficient reconciliation evidence.

## Regression and normal runtime

System2: **669 passed**, one missing-fixture skip and one existing warning. Workbench: 21 Python and 17 frontend passes. Logs: `tmp/table-rows-final.txt`, `tmp/table-rows-targeted.txt`, `tmp/table-rows-workbench.txt`, `tmp/table-rows-frontend.txt`.

Seven new row tests cover create-to-delivery, restore/invalidation, later-reference conflicts, unassigned-row blocking and whole-table scope, duplicate reference redirection/restoration, atomic stale/invalid rejection, text/draft conflicts, and evidence-only non-promotion. Tests establish these mechanics, not extraction accuracy or acceptable human effort.

The normal workbench on port 62742 was restarted with the row module/API. A fresh production browser confirmed the row-repair panel and current source rows without submitting a decision. Production integrity is `ok`, with 15,120 units, 31 sources waiting for review, seven existing failed sources, zero System2 review events and zero published Requirements. No migration or pilot decisions were copied. Source PDFs, Canonical files and earlier human histories remain retained. System3 semantic processing is not connected.
