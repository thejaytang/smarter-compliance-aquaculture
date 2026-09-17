# System2 Excel register acceptance | 2026-09-09

## Outcome

Implemented `delivery/requirement_workbook.py`, Workflow adapter synchronization and the shared browser's Excel download route/link. Production register: `system2/System2_Requirement_Register.xlsx`, with 38 source worksheets plus Source Index and Read Me. Production remains at zero System2 parsing jobs, policy revision 1 and 95% thresholds. No isolated decisions were copied into production.

The System1 registry SHA256 remains `7beb2c9d63afcf693f41b3440b3ed3bb3cb7dd350b149480957d4f2901b8d041`.

## Verification

- System2 full regression: 584 passed, one missing PDF sample skipped. The seven new workbook regressions cover unstarted/non-INCLUDE scope; accepted delivery and correction invalidation; unchanged-file detection and Excel locks; long Unicode text and formula-like source text; withdrawal; dated registry cells and interrupted saves; threshold increases and retained human confirmation.
- Workbench: 20 Python tests passed, including fresh attachment response and failed-refresh handling. The existing 14 frontend tests passed after the download-link change.
- Production HTTP download returned 200, the correct XLSX media type, attachment disposition and a readable 40-sheet workbook. State readback reported zero jobs and a current workbook receipt. Evidence: `tmp/workbook-http-result.json`.
- Isolated real HTML/XLSX state exported PA001's 150 content units and CS009's 2,596 units to separate sheets. These remain isolated audit content, not accepted production Requirements.
- Native Microsoft Excel opened the index and PA001 source sheet with all 40 tabs and no repair prompt. Source index layout, link navigation, metadata, empty-source instruction and header freezing were inspected. The workbook was closed without importing or saving a human decision.
- Native Excel's actual owner lock prevented refresh while the file was open. Closing the check window allowed automatic refresh. Applied review state was retained.
- OfficeCLI initially identified font child-order schema incompatibility in openpyxl serialization. The exporter now normalizes that font order without changing cell content. Production and populated isolated workbooks pass OfficeCLI Open XML validation.
- The workbench service was reloaded on `127.0.0.1:62742`; the browser retained Weijie Tang's session and showed Download Excel register in System2.

## Boundaries

This verifies the Excel carrier and its integration. It does not parse unstarted sources, establish PDF accuracy, validate live model effect, or accept the System3 consumer. The seven previously incomplete HTML inputs remain unresolved upstream. Browser/Workflow decisions and Canonical facts remain authoritative. Desktop-open and downloaded workbooks are snapshots until reopened or downloaded again.

Contract: [Excel register](../contracts/requirement-workbook.md).
