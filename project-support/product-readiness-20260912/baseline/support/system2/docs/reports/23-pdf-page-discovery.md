# PDF page discovery and local coverage dependencies

Date: 2026-09-10. Decision: `CONTINUE`. This advances the source-discovery stage after [the effective repair pilot](22-pdf-repair-pilot.md); hierarchy/table geometry and safe reparse remain unfinished.

## Observed defect and correction

Production CS004 Requirement 2.1.3 had 47 content dependencies: its table, a supposedly local completeness record spanning the entire source, and all 45 parsing-window checks. The projection regrouping had removed source-range boundaries and attached every window finding to every unit. This prevented local progress and broadened invalidation unnecessarily.

PDF coverage now has explicit per-page checks. Multi-page units depend on each referenced page. Window findings are attached by bound page range or Canonical fingerprint; an unknown scope remains blocking. Existing explicit table/shared-content links and human findings remain. The old broad completeness record is retained for overall source completion, not silently accepted or deleted. New PDF projections no longer combine paragraphs from different pages merely because they share a heading label.

In the full production-data copy, 2.1.3 now has three dependencies: its table, page 20 completeness and its own parsing window. There are still unresolved cross-window checks. The change narrows unsupported edges; it does not infer that unresolved relations are correct.

Position corrections refresh the applicable page dependencies and reopen old/new page completeness. Supplementation on a different page uses that actual page rather than the selected task's page. Fresh page-scoped parsing installations add checks for processed blank pages as well. These operations preserve source originals and version invalidated results.

## Browser discovery

Content proofreading exposes `Inspect original PDF pages`. Reviewers can choose any page, move to adjacent pages, inspect its bound original image with mapped regions, and open a mapped unit for existing repair controls. Page completeness provides an entry for checking the whole page and adding missing text. Pages and mapped-unit lists are paginated at 50. Accepted content is included, independent of the pending-task queue; unprocessed pages and pages without mapped content remain visible.

Highlights show only the listed mappings. A table and its row projections can overlap. They are not an automatic omission detector or a measured coverage percentage. Full original access remains available. Screenshot rendering is source-bound; content is never re-typeset to masquerade as original evidence.

An isolated browser check used the complete CS004 production projection and real PDF pages 20–21. Clicking the page-20 2.1.3 region opened that exact row's original, extracted criterion and repair controls. The page image and SVG were visually checked together at a 455-pixel viewport. An initial inline-style/CSP defect caused overflow and misalignment; the fix uses the existing stylesheet. Final DOM measurements: body/viewport 455 pixels, image and overlay both 389 pixels. Visual inspection showed the table and footnote boxes aligned. No source correctness decision was submitted in this discovery check.

## Migration and preservation

The isolated copy is `../workbench/runtime/pdf-page-pilot/`; its manifest, preview and receipt record the experiment. Its source documents and Canonical files were copied with preserved content hashes. No new parsing or external model was run.

After successful regression and copy validation, the production workbench was stopped at a checkpoint with zero queued/running parsing jobs and zero System2 human decisions. `review/migrate_pdf_scope.py` made an exact SQLite backup and applied the explicit migration. Receipt: `runtime/workflow/pdf-scope-migration-20260910.json`. Backup: `runtime/workflow/workflow-before-pdf-scope-20260909T222138430739Z.sqlite` (UTC timestamp).

4,286 CS004 units received changed coverage edges; 134 page checks were added. The source now has 4,466 units; all sources together have 15,120. Every one of the 14,986 previous original projections and blocker lists matched the backup exactly, and human history matched exactly. Database integrity returned `ok`; production human history and deliveries remain zero. Source completeness remains false. The normal service restarted on retained port 62742, and the new module/page API returned HTTP 200.

## Validation and limits

- Full System2 regression: 617 passed, 1 skipped, 1 existing deprecation warning, 12.63 seconds (`tmp/pdf-scope-regression-final.txt`). The skip requires absent `_PS3_副本.pdf`.
- Workbench: 21 Python tests passed; 17 frontend tests passed after final UI edits. Logs: `tmp/pdf-pages-workbench.txt`, `tmp/pdf-pages-frontend-final.txt`.
- Final browser inspection also found that page-completeness totals still filtered by chapter name and appeared empty. They now aggregate the bound page references, including reviewed locations. The final scope/browser subset passed 11 tests (`tmp/pdf-pages-final-targeted.txt`) after this fix.
- Eight scope/discovery integration tests cover cross-page dependency preservation, unknown/human findings, effective position changes, non-merging across pages, backed-up migration/history/stale guards, empty/unprocessed/accepted page discovery, corrected mapping positions, and actual-page insertion/old-new coverage invalidation.
- Twenty uncached page metadata reads on the full source copy had p95 0.074 seconds. This measures in-process database projection, not end-to-end browser interaction or concurrent-background workload. Original image rendering is separate. Current page discovery inspects this source's references through SQLite JSON; it does not scan all sources. A dedicated page index can follow if measured costs require it.

Still required: source-backed outline and parent/order edits, table geometry and cross-page repair, direct original-region selection for omission insertion, ambiguous relation resolution, safe local reparse preserving patches, independent important-error discovery validation and human workload measurement. Existing production heading/type mapping remains incomplete. The new page view is a source-first inspection entry, not proof that reviewers can yet detect and repair every complex-PDF defect. Real Norwegian and scanned/mixed-document acceptance remain unmet.
