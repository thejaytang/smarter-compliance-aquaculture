# PDF original-boundary merge checkpoint

Date: 2026-09-10. Decision: `CONTINUE`; split reconstruction, table geometry and safe reparse remain open.

## What changed

PDF sources with the hierarchy projection can join incorrectly separated original text during content proofreading. Prior content acceptance is no longer required for this repair. The selected primary unit remains the current identity and receives an overlay containing the joined text, all bound original regions, explicit type/heading level and source-fragment provenance. Other joined fragments remain immutable historical records marked `superseded_by`; they are excluded from current task, page and outline navigation, without being falsely marked accepted.

Incoming parent relationships, typed references and dependency edges are redirected to the surviving identity. Affected content and page checks reopen, and existing downstream results are suspended. Conflicting source fields, intervening substantive content, inconsistent source parentage, table geometry, stale targets, draft conflicts and dependency cycles fail explicitly. These constraints preserve unresolved work; they do not silently flatten structures or infer missing text.

Restoration returns the prior boundary overlays and relationships as a new revision. Later conflicting repairs or newly added references block restoration until reviewed, so a reference to the complete merged heading cannot silently become a reference to only one former fragment. Excel retains the full corrected heading once as the current unit and labels the preserved old fragment `Superseded`.

The detail header now presents the question, title, reason and confidence vertically. A browser screenshot exposed an inherited toolbar flex layout squeezing them into narrow columns; the scoped layout fix was visually verified on the normal workbench. Multi-page evidence now explicitly warns which page the crop displays and lists every page requiring comparison.

## Real-source repair evidence

Original: CS004, ASC Salmon and Cod Standard v1.5, page 19; SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`.

The original has one two-line Principle 2 heading. The saved parser structure had split it into:

- `pdf:b86bb0f9e38524a4f9785c5b`: `PRINCIPLE 2: CONSERVE NATURAL HABITAT, LOCAL`, level 2;
- `pdf:e7557bde7377e42174f249e9`: `BIODIVERSITY AND ECOSYSTEM FUNCTION`, level 1.

In the retained isolated runtime `workbench/runtime/pdf-hierarchy-pilot/`, the browser applied merge → restore → merge under the test reviewer Ana Jokic. The final effective heading preserves both lines at level 1 and both original evidence regions. The original crop was visually inspected in the browser and includes both lines; the effective text matches it. Content acceptance remains pending and there are no pilot deliveries from these operations. Test decisions were not copied into production.

Artifacts under `system2/tmp/pdf-boundary-pilot/`:

- `effective-heading.json`: source-bound effective output;
- `history.json`: applied merge/restore/merge history with reversible patch states;
- `repaired-page19.xlsx`: bounded real-source output, SHA256 `1f87f7a2dac7389a11af3f910877fc1974dd02a4d8ba03151fc8427a8541cba0`.

Workbook readback confirms the full two-line heading in row 12 and the preserved second fragment marked `Superseded` in row 13. Native Excel opened the file and was positioned for inspection, but the Mac subsequently locked and automatic unlock failed. **Native Excel visual acceptance for this artifact is pending user unlock.** Programmatic readback and successful file opening do not replace that check.

## Regression and deployment

System2: 629 passed, one missing-fixture skip, one existing Starlette warning. Workbench: 21 Python tests and 17 frontend tests passed. Six merge regressions cover pending-content repair, exact source preservation, target/draft conflicts, incoming relationship redirection, output/Excel agreement, retired-unit write rejection, history restoration and later-reference conflicts. These are implementation checks, not estimates of extraction accuracy or reviewer workload.

The normal service was restarted at its retained port 62742 with no active parsing. No data migration was required. Production retains 15,120 units, zero System2 human decisions and zero deliveries; SQLite integrity passed. A fresh production browser verified the new reading layout and source detail without submitting a decision.

## Next experiment and limits

The existing split path still requires prior acceptance and does not implement a complete boundary-replacement model. Replace it with source-preserving split results, explicit source ranges and explicit disposition of incoming parent/reference relationships. Validate against distinct original paragraphs, including a clearly labelled seeded over-merge when needed. Do not duplicate identifiers, criteria or notes onto every result or silently attach a child to an arbitrary split part.

After split/restore and evidence mapping pass, continue to table row/column/span and cross-page geometry repair, then safe local reparse with conflict handling. Native Excel visual acceptance above, Norwegian/scanned/mixed-PDF validation and measured discovery/repair effort remain unfinished. System3 semantic processing remains unconnected.
