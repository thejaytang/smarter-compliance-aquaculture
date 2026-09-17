# PDF original-boundary split checkpoint

Date: 2026-09-10. Decision: `CONTINUE`; table geometry, safe local reparse and measured reviewer effort remain open.

## Effective changes

Hierarchy-enabled PDF source text can now be divided before content acceptance. The split request must preserve every source character in order. Each new part receives an explicit content type and original evidence selection. Non-body fields and existing incoming/outgoing typed relationships require explicit destination choices. An identifier cannot be copied onto multiple parts. Parentage must resolve to one part; evidence and other fields can intentionally belong to multiple parts.

New identities retain a version-bound character range, source-unit identity and original-region references. The old unit is retained as superseded history. Current tasks, outline, effective exports and delivery use the replacement units. No source PDF or original Canonical is rewritten. A split does not accept text or resolve inherited blockers. Affected acceptance and downstream results are invalidated transactionally.

The browser offers cursor and existing-line-break boundaries, previews each resulting part, and groups same-page paragraph evidence to avoid requiring one click per extracted line. A group retains all of its underlying regions. The selected original region can extend beyond a character range; the preview explicitly states this limitation instead of promising a tighter crop.

Restore is available from either split child. It reinstates earlier boundaries and relationships while retaining the retired child records. Later child edits and new dependencies block conflicting restoration. Replayed requests return their prior receipt; malformed or incomplete relationship assignments fail without partial changes.

Split drafts preserve boundaries, source ranges and assignments. A browser walkthrough found that explicit draft saving failed to retain its returned guard, causing the reviewer's own save to look stale after refresh. Both structured-repair and split draft saving now persist the returned guard. An already-stale draft requires comparison before it can be saved against a newer result; local unsent values remain retained.

## Real-source experiment

Source: CS004, ASC Salmon and Cod Standard v1.5, original page 20. PDF SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

The original has a Rationale paragraph followed by a separate paragraph starting `When considering benthic effects`. The retained parser had already separated these paragraphs, so this experiment deliberately joined them in the isolated source copy. **The over-merge was seeded; it was not an observed parser defect.** Its request and original effective values are retained in `tmp/pdf-split-pilot/seed-request.json` and `before.json`.

The browser applied split → restore → split, including explicit draft save/reload. The two final parts retain ten and five original line regions respectively. Comparison with the original also identified a genuine omitted `1500` in the first paragraph. A separate browser text correction restored that number. Both parts remain pending content review, including unresolved broader text/footnote checks; no acceptance or pilot delivery was fabricated.

Final isolated source revision: 77. Current parts:

- `split:74a41ae5ed6ebdfb17fb3d03`: Rationale, with the separate `1500` correction;
- `split:6b1824a68a7746af869630e5`: When considering benthic effects.

Artifacts under `tmp/pdf-split-pilot/` include `effective-parts.json`, `history.json` and `repaired-page20.xlsx`. The workbook SHA256 is `79f4c02b5e573eb541fa317ac24da8bb7068fe7e0b3f2910150388606aad3c10`. Programmatic readback verifies current paragraphs in rows 16–17, superseded earlier boundaries labelled in adjacent rows, and no delivered result. The bounded workbook is a source-range validation artifact, not the full source register.

The original page and browser crop were visually inspected. At a 1280-pixel browser width the side-by-side original paragraph is small; expansion remains available, and source readability/zoom should be evaluated in the human-effort checkpoint. Native Excel visual acceptance remains pending because the Mac was locked during the earlier attempt; a saved workbook or programmatic readback is not that acceptance.

## Verification scope

Eleven split integration checks cover exact text/field/evidence disposition, incoming parent/reference redirection, incomplete/malformed requests, duplicate requests, restore from a child, later-edit conflicts, delivery suspension, current navigation and Excel agreement. These checks do not estimate machine extraction fidelity or reviewer effort.

Runtime validation is confined to `workbench/runtime/pdf-hierarchy-pilot/`. Test decisions and split data are not migrated into production. This code extension requires no production data migration. Full regression passed 640 tests with one missing-fixture skip and one existing Starlette warning. Workbench passed 21 Python and 17 frontend checks. The normal service restarted on port 62742; a fresh browser verified the split entry without submitting a production decision. Production retained 15,120 units, zero active parsing and zero System2 human decisions; SQLite integrity passed. Full regression logs are retained under `tmp/boundary-split-final.txt`, `tmp/boundary-split-workbench.txt` and `tmp/boundary-split-frontend.txt`.

## Next checkpoint

Continue with a bounded original table requiring actual row/column/span repair, followed by a cross-page table mapping. A note or accepted flag must not count as geometry repair. Then validate local reparse proposals against existing human overlays using explicit differences and conflict handling. Keep Norwegian/scanned/mixed-PDF fidelity, unresolved source defects, native Excel visual inspection and measured human discovery/repair cost as distinct unfinished gates. System3 semantic processing is not connected.
