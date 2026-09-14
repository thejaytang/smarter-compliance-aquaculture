# PDF table geometry checkpoint

Date: 2026-09-10. Decision: `CONTINUE`; cell creation/split/merge, row retirement, cross-page table joins and safe local reparse remain open.

## Implemented effective repair

The complete-table view now supports cell row/column coordinates, row and column spans, header flags and explicit existing-item-to-row bindings. All cell identities, text and original regions are retained. Invalid dimensions, overlaps, uncovered grid positions, missing cells, stale related rows and conflicting drafts fail without applying a partial layout. This operation cannot silently create missing cells or retire existing row items.

The overlay is consumed by the common effective view. Its table grid, HTML, structural evidence projection, derived row fields and source references agree. Corrected row order is reflected in current unit ordering and Excel. Typed references to a table or its row read effective fields rather than stale original table JSON. Cell text edits also regenerate table HTML, fixing a stale-render path independent of geometry changes.

Applying a layout reopens related content, page coverage and downstream results. Restoring uses the existing guarded patch history, including layout, row bindings and row ordering. Original PDFs, Canonicals and row projections remain untouched. Reacceptance is separate from repair.

The browser has a complete-table editor, live proposed-grid preview, persistent drafts, explicit comparison and named application receipts. From a row item, `Open complete table to repair its layout` opens the appropriate owner. The main original/result comparison now renders the effective table as a table, while retaining related notes/context below it.

## Real PDF evidence

Source: CS004, ASC Salmon and Cod Standard v1.5, page 20; original PDF SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

The parser had marked both cells of the `2.1.3` indicator row as headers. Original-page comparison shows this is a substantive regulation row preceding `2.1.4`. The isolated browser removed the erroneous flags, preserved the 2 x 2 layout and saved/reloaded the repair draft before applying it.

A separate **explicitly seeded column swap** challenged coordinate repair. Both columns were intentionally inverted in the isolated overlay. The browser displayed the wrong arrangement, then restored descriptions/numbers to the left column and criteria to the right. This swap was a test intervention, not a naturally observed parser defect. A proposed overlapping span was also detected in the browser before application.

Final isolated source revision: 83. Table owner: `pdf:f15bf96c905af0f7a15d41e2`; row identities end in `:row:0` and `:row:1`. Effective output preserves identifiers `2.1.3` and `2.1.4`, their criteria `≥ 2 highly abundant 7 taxa that are not pollution indicator species` and `Yes`, four original cells, no erroneous header flags and all original cell regions. The table and rows remain pending and there are zero pilot deliveries. Footnote attribution and source-wide text fidelity have not been accepted by this structure repair.

Retained artifacts in `tmp/pdf-table-geometry-pilot/`:

- `corrected-headers-before-seed.json`: actual header repair before the seeded challenge;
- `seed-request.json`: the labelled test intervention;
- `effective-table-and-rows.json`: final effective geometry, fields and evidence;
- `history.json`: guarded repair history;
- `repaired-page20-table.xlsx`: bounded source-range output, SHA256 `cd24301c24ef52119d6ec0e3b29b1ab27ee5a8cd8eb4ccc2002c913bd8c21862`.

Workbook readback verifies rows 13–14 retain the correct indicators, criteria and `Not delivered` status. The original crop and effective grid were visually inspected side by side in the browser. Opening the workbook in native Excel succeeded, but screenshot inspection again confirmed the Mac was locked and automatic unlock failed. **Native Excel visual acceptance remains pending.** The workbook is a flattened full-text source register, not a claim that original table styling or merged-cell geometry is recreated in native Excel.

## Regression and normal runtime

Full System2 regression: 651 passed, one missing-fixture skip and one existing Starlette warning. A final targeted pass rechecked the 11 geometry cases after the non-hierarchy restore-order adjustment. Workbench: 21 Python and 17 frontend checks passed. Logs: `tmp/table-geometry-final.txt`, `tmp/table-geometry-final-targeted.txt`, `tmp/table-geometry-workbench.txt`, `tmp/table-geometry-frontend.txt`.

Tests cover cell retention, overlaps, gaps, ranges, related-row concurrency, atomic failure, ordering, common HTML/structure/field output, shared cell edits, related references, delivery invalidation and restoration. Span reconstruction is exercised with synthetic geometry; real complex merged-table repair is still an acceptance gate. These checks do not establish extraction accuracy or acceptable human workload.

The normal workbench restarted on retained port 62742 and a fresh browser verified its complete-table repair entry without submitting a production decision. No data migration or pilot decisions were copied. Production SQLite integrity passed, with 15,120 units, zero System2 human decisions and no active parsing at the checkpoint.

## Next experiment

Extend the table overlay with source-preserving cell boundary operations: split an incorrectly combined cell, join fragments of one original cell and supplement a missing cell. Every old text fragment needs a traceable disposition; derived row scopes and incoming references must remain explicit. Validate the first real merged-cell failure before extending row retirement and cross-page table correspondence. Then continue conflict-preserving local reparse. Broader Norwegian/scanned/mixed-PDF validation, native Excel inspection and measured discovery/repair effort remain unfinished. System3 semantic processing is not connected.
