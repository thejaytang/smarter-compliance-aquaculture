# PDF hierarchy and reading-order repair checkpoint

Date: 2026-09-10. Decision: `CONTINUE` to source-boundary repair before expanding table geometry or reparse tools.

## Implemented behavior

The effective view now carries source content type, heading level, parent and reading order. A named reviewer can change these through guarded repairs. Moving a parent carries its current descendants. Parent cycles, dependency cycles, stale targets and superseded targets are rejected. A child placed before its parent remains blocked until its parentage or order is repaired; a generic issue confirmation cannot dismiss that defect. Supported repair restoration creates a new revision and preserves unrelated earlier repairs.

The outline exposes saved Canonical document/section containers, actual content and current parentage, including content without machine findings. Containers are labelled by their bound PDF page range, not invented chapter semantics. Lists return bounded summaries. Parent changes invalidate affected content, genuine dependants and corresponding page coverage; delivery uses the effective hierarchy and order. Excel adds Parent content, Heading level and Reading order. Table parent labels use a readable page reference.

## Real-source browser experiment

Source: CS004, ASC Salmon and Cod Standard v1.5, original SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. Original pages 19 and 20 were rendered and visually inspected. The experiment used a full production database copy under `workbench/runtime/pdf-hierarchy-pilot/`, never production human decisions.

Five browser submissions were applied under the isolated test reviewer Ana Jokic:

1. Criterion 2.1 was actually saved as a paragraph. Restored heading type and level 2 against the original heading below Principle 2.
2. Assigned the page-20 continuation table to Criterion 2.1. The outline then exposed Criterion 2.1 → table → indicators 2.1.3 and 2.1.4. This is a parent repair, not a cross-page table merge.
3. Footnote 7, visibly below the original footnote rule, was saved as a paragraph. Restored footnote type without changing text or claiming its citation relationship resolved.
4. Deliberately moved footnote 7 after 8 in an explicitly labelled isolated challenge. This was not a naturally occurring parser error or an acceptance decision.
5. Restored the values before that move through browser history. Footnote 7 returned before 8; its earlier type repair survived.

Browser inspection caught a defect that the first tests missed: shared source references allowed a coverage task to replace the table owner in the parent map. Coverage and superseded objects are now excluded as source-content identity candidates. A regression covers this collision; the corrected real outline retains both row children.

Artifacts: `system2/tmp/pdf-hierarchy-pilot/original-page19.png`, `original-page20.png`, `seeded-order.json`, `restored-order.json`, and `repaired-source-range-v2.xlsx`. The workbook is an explicitly bounded pages-19–20 inspection export, not the whole source. Native Excel opened it and displayed the new columns; an oversized table-structure parent label was fixed and rechecked. Programmatic readback verified the title type/level, 2.1.3's table parent, footnote type and final note order. No source was accepted by these five repairs.

## Regression and migration evidence

- System2 complete suite: 623 passed, 1 skipped, existing Starlette warning. The skipped source fixture remains unavailable. After the final readable-parent-label change, hierarchy/export tests passed again.
- Workbench Python: 21 passed. Frontend: 17 passed. Syntax checks passed for the edited repair and outline modules.
- Tests cover replay, stale target, cycles, parent-driven invalidation, delivery hierarchy, effective Excel order, restoration, moving subtrees and non-dismissible ordering defects. These establish implementation behavior, not extraction fidelity or acceptable human effort.

Production was stopped with no queued/running parse jobs. Migration backup: `runtime/workflow/workflow-before-hierarchy-20260909T225337791197Z.sqlite`. Receipt: `runtime/workflow/hierarchy-migration-20260910.json`.

All 15,120 `(document_id, unit_id)` original projections, blocker lists, edits and drafts were compared before/after and retained exactly. Production human history and deliveries remained zero. CS004 received 4,286 content hierarchy projections and 90 source containers; coverage tasks did not become content parents. SQLite integrity passed, source completeness stayed false. The service resumed on port 62742; a fresh browser opened the production outline. Its machine errors remain pending; isolated repairs were not copied into production.

## What is still not complete

The original Principle 2 heading spans two lines that the parser saved as separate headings with inconsistent levels. That real defect defines the next experiment: restore one original heading without requiring prior content acceptance, preserve both evidence regions, redirect children/references and verify output/restoration. Current split/merge is not yet sufficient for this guarantee.

Table row/column/span and cross-page geometry repair, graphical omission-region selection, safe local reparse with three-way conflict handling, general restoration of older text/boundary operations, independent discovery recall and measured reviewer effort remain open. This English native-text PDF does not establish Norwegian, scanned or mixed-document acceptance. System3 semantic processing is still not connected.
