# PDF table-cell boundary repair checkpoint

Date: 2026-09-10. Decision: `CONTINUE`. Row creation/retirement, cross-page table joins, safe local reparse and broader repairability acceptance remain unfinished.

## Implemented behavior

The complete-table editor supports splitting an incorrectly combined cell, joining fragments of one original cell and supplementing a missing cell. Split text must preserve every current character and explicitly assign retained original regions. Merge text uses the selected source cells and an explicit separator. Supplementation requires a bound PDF page and bounding box. New identities are request-derived; prior effective cells remain in patch history, and original PDFs/Canonical remain unchanged.

A complete proposed grid and current derived-row fingerprints accompany each operation. Effective table HTML, row fields, source references and exports consume the same corrected cells. Retired cell IDs cannot receive new text edits. Restoring supported changes rejects later conflicting edits. Related acceptance and delivery are invalidated in the same transaction; a repair does not accept content.

Incomplete grids can be saved as explicitly partial repairs. `human_table_grid_gaps` remains a structure task and cannot be dismissed through generic issue resolution. Filling the actual gap clears that blocker without accepting the table. Overlaps and out-of-range cells still fail atomically.

The browser supports proposed-layout inspection, persistent drafts, named receipts and bound cell-region previews. Previews resolve current cell evidence on the server using the current guard. They render the original PDF, not corrected text. A character-range split may retain a broader original region and displays that limitation. The preview opens in a readable modal; its styles use the external stylesheet to respect the workbench CSP.

## Real and seeded evidence

Source: CS004, ASC Salmon and Cod Standard v1.5. PDF SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

On real page 2, the parser separated `Document` and `Name:` into different cells, while the original footer shows one bordered label cell. The isolated browser joined them into `Document Name:`, retaining both source regions. The table went from 13 to 12 effective cells. Other footer fragmentation remains unresolved; this is not acceptance of the complete footer.

On page 20, an explicitly seeded over-merge combined the 2.1.3 description and criterion. The browser split it at the preserved newline, assigned the left and right source regions and restored four cells. A second explicit fixture removed the criterion cell from the effective overlay, preserving its history. The browser displayed the gap and supplemented the exact text at `page 20: 344.88,62.64,566.64,146.16`. Both interventions are labelled test faults, not observed parser errors.

Final pilot source revision: 92; event cursor: 115. The effective 2.1.3 criterion is `≥ 2 highly abundant 7 taxa that are not pollution indicator species`; 2.1.4 retains `Yes`. The table has four current cells and no grid-gap blocker. Content remains pending, and pilot deliveries remain zero. Footnote attribution and whole-source fidelity were not accepted.

Artifacts under `tmp/pdf-cell-boundary-pilot/` retain the original page-2 rendering, before/seed records, removed-cell evidence, final effective tables/rows and full repair history. `repaired-source-tables.xlsx` contains the bounded pages 2 and 20 view, SHA256 `3ea4fd54031cffde781abfdf6f80e410c08f4e9ce507aae79160c1abc695665c`. Programmatic readback verified the indicator criteria and `Not delivered` status. Native Excel visual acceptance remains pending after the previously confirmed Mac lock; this workbook was not visually accepted in Excel.

## Regression and runtime

System2 full regression: 661 passed, one missing-fixture skip. The subsequent cell-specific delivery/reacceptance test passed with the other ten cell cases, giving 11 targeted passes. Workbench: 21 Python and 17 frontend passes. Logs: `tmp/table-cells-final.txt`, `tmp/table-cells-delivery-final.txt`, `tmp/table-cells-workbench.txt`, `tmp/table-cells-frontend.txt`.

Checks include text preservation, source-region assignments, new-cell editing, retired-cell rejection, stale preview guards, transaction rollback, reversible merge, restore conflicts, gap blocking and delivery suspension/republication after explicit reacceptance. These tests do not establish extraction accuracy or acceptable human review effort.

The normal workbench on port 62742 serves the new editor and bound-cell preview. A fresh production browser visually verified the styled original-region modal without submitting a production decision. Read-only production checks confirmed SQLite integrity, 15,120 units and no review/delivery events. No migration or pilot decisions were copied into production.

## Next discriminating experiment

Extend explicit table row identity management before joining separate tables: create a missing row item, retire a duplicate while retaining its source disposition, and verify incoming references/acceptance/output restoration. Then validate one actual cross-page table continuation, including repeated headers and incomplete correspondence. Safe local reparse must preserve existing human overlays and expose conflicts before adoption. Broader Norwegian/scanned/mixed-PDF fidelity, error discovery and measured human effort remain required; System3 semantic processing is not running.
