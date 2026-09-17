# Real PDF shared cells and table notes

Date: 2026-09-10. Decision: `CONTINUE`; this checkpoint repairs a bounded real table and its note relationships, not the full PDF pipeline.

## Observed defects and corrections

Original CS004 page 123 has one header and eight regional rows. The primary table projection `pdf:b7ff8dadc5345406104cce96` had ten logical rows, a nine-row Global Level span and two-row Scotland cells. The isolated browser changed the grid to nine rows, the shared `3**` cell to eight rows and both Scotland cells to one row. All 20 original cells and source evidence remain. No source text was deleted.

A regression experiment then reproduced a downstream error: after including the shared cell, a regional row resolved as `3** / Norway / 5`, because it sorted by the cell's start row instead of the selected row's columns. Effective row fields now retain column order. `table.selected_row` identifies the logical row; its HTML displays one row while source cell coordinates and spans remain unchanged. All eight regions now include the same retained global-level cell, for example `Norway / 5 / 3**` and `Scotland / 9 / 3**`.

The `**` footnote had also been merged with the following `In addition...` paragraph. The browser split that real source block at its original paragraph boundary, using the exact phrase and individual retained regions. The footnote keeps source regions 1–3 (y 518–564); the paragraph keeps regions 4–8 (y 578–656). Every existing character was retained. Result identities are `split:aed9511812815f5bc2e30207` (footnote) and `split:ccf26b8306dff5d2cbd0596b` (paragraph). This boundary repair does not claim that every original punctuation mark or OCR character has been verified.

The separated `**` note and the existing `*Farms based outside...` note were explicitly linked to the complete table using the browser. A second reproduced defect showed that table-level notes were omitted from row output. Effective row views now inherit explicitly table-wide relationships, annotate `inherited_from_table`, and order related content by effective source order. The two notes remain separate evidence records with four and three original regions. The following explanatory paragraph is not included in the footnote field. Table-level relations must be edited at the table; attempting to detach them locally from a row fails clearly. Related note corrections invalidate dependent delivery.

## Browser and Excel readability

The split editor can locate a unique exact phrase as the start of the next part, including text without saved line breaks. An advanced selection assigns individual original regions rather than an entire merged paragraph. The general evidence viewer offers `Enlarge original region`; a browser screenshot verified a readable original table modal with scrolling.

Task summaries now expose the evidence-only flag, and related-content choices label retained window copies. `overlap_evidence_only` has a readable explanation that the copy cannot be delivered independently. Excel render version 10 displays `Evidence only`, preserving the content without presenting it as an ordinary deliverable candidate. It also refuses to show an evidence copy as Available if an inconsistent old publication entry exists.

The second page-123 projection remains retained as overlap evidence. It is not automatically reconciled, accepted or removed; primary/halo correspondence remains a separate gate.

## Evidence and artifacts

Original PDF SHA256: `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

Final isolated source revision: **107**; event cursor: **130**. The table and affected rows/notes remain pending, the source remains incomplete, and pilot deliveries remain zero. These were repairs of observed source defects, unlike the labelled seeded row faults in the preceding checkpoint.

Artifacts under `tmp/pdf-shared-row-pilot/`:

- `before-primary-table.json`: original geometry and immutable source facts before correction;
- `effective-table-rows-and-notes.json`: corrected grid, each row, both related notes and the separated paragraph;
- `history.json`: retained named repair history;
- `repaired-page123-table.xlsx`: bounded page-123 output, SHA256 `bfbf880ac5c8f155f4856e2e184061c321ff128e5111333269a42140ecca86db`.

Workbook readback confirmed `Norway / 5 / 3**`, both ordered footnotes, no `In addition` paragraph in the notes, and `Not delivered`. The retained window copy remains visible as `Evidence only` with its older uncorrected evidence projection. Original primary table facts compare exactly equal to the before snapshot. Native Excel visual acceptance is still pending; this turn's native surface check confirmed the Mac remains locked.

## Regression and production

Full System2 regression: **673 passed**, one missing-fixture skip and one existing warning. Final focused table/note/list/workbook checks: 44 passed. Workbench: 21 Python and 17 frontend checks passed; both edited frontend modules passed syntax checks. Logs: `tmp/shared-row-before.txt`, `tmp/shared-note-before.txt`, `tmp/shared-table-final-suite.txt`, `tmp/shared-table-final-targeted.txt`, `tmp/shared-table-workbench.txt`, `tmp/shared-table-frontend.txt`.

The two before logs reproduce the wrong shared-cell ordering and missing inherited note. Passing checks cover their corrected effective views, source geometry retention, dependent delivery invalidation, inherited-detach rejection, concise evidence-only list metadata and export non-promotion.

Production remains 15,120 units, 31 sources waiting for review, seven existing failures, zero System2 review events and zero published Requirements; SQLite integrity is `ok`. The normal service serves the updated UI and read projections. Its background Excel refresh is current at event 71 and readback confirms the evidence-only Norway row is visibly labelled. The real repairs remain isolated, with no migration or pilot decisions copied into production.

## Remaining gates

Next inspect and reconstruct an actual cross-page table, with explicit column/row correspondence, repeated-header disposition, source identities, notes and restoration. Preserve the primary/halo distinction and expose differences rather than treating repeated source text as a new requirement. Then implement conflict-preserving local reparse without overwriting human overlays. Broader Norwegian/scanned/mixed-PDF fidelity, missed-error discovery, measured human effort and native Excel visual acceptance remain incomplete. System3 semantic processing is not running.
