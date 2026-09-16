# Third-pane source Group relationships

## Delivered

- An explicit source Group has one optional relationship with exact wording and code-point span. The floating toolbar adds Relationship beside Group; root-level assignment is unavailable.
- The connector appears between its source-ordered sides, with a separate removal cross and a retained original-text highlight. It does not count as a quantity child. AND / OR remain represented by quantity controls.
- Existing marks can be wrapped into source Groups without losing IDs. A one-child implicit All wrapper is omitted from the display. Group removal, connector-only removal, history restoration and protected degrouping retain their distinct meanings.
- Fourth-pane source projection uses the same Group labels as the third pane and preserves the relationship in its source description. Existing editable Logic is retained; no Site Model judgment is introduced.
- Versioned structure v2 and delivery v3 preserve connectors through explicit saves, relational projection, interpretations, recovery and reviewer-bundle exchange. Old versions remain readable. No new dependency or live model call.

## Verification

The initial full regression passed 296 backend and 350 frontend tests. After the final source-label correction, all 350 frontend tests passed again. Six focused backend tests cover exact quotations, Unicode/repeated-text offsets, invalid owners/spans, quantity preservation, missing sides, same-role Objects on both sides, page-only preview, request replay, conflicts, actor isolation, history, deletion, relational foreign keys, context invalidation and export/import. The final complete backend regression passed **297 tests**; all **350 frontend tests** pass.

Real browser checks on normal port 62742 used a separate temporary tab. Mouse double-click and keyboard selection displayed the toolbar; Relationship removal kept all marked Objects/Subjects/verbs and their counts; reassignment restored `including`; collapsed original text retained its colour. Leaving the test draft showed the unsaved-work dialog. Discard and reload recovered the saved version without an extra saved revision. Desktop widths 1440 and 1280 were inspected; a 640px check exposed a toolbar right-edge spacing issue and received a bounded correction. The final 640px screenshot confirms the toolbar ends 8px before the right edge and all seven controls remain visible; no page errors were logged. Temporary pane/viewport changes were reset and the test tab closed.

## Existing example

PE001-003 remains four complete Requirements. R2 now records `including` at [113,122] inside an outer source Group, connecting the movement-description Group to the two location Objects. Subjects remain All 2, Main Verbs All 2, locations [2,2]. The original wording and all existing fragment IDs/roles/spans are unchanged. R1's links were refreshed and retain source order R2, R3, R4 with All 3. R3 and R4 are unchanged. Final splitting revisions: R1=6, R2=3, R3=1, R4=2. R1/R2 interpretation context bindings were refreshed with the six saved editable values retained verbatim.

Live readback: one relationship projection, SQLite integrity `ok`, zero foreign-key violations. A local verification JSON records the exact IDs and quantities. Browser test edits were discarded; the user's original Chrome tab was not reloaded, saved, or discarded.

## Activation and recovery

Twelve owning SQLite stores were consistently backed up during controlled service shutdown. Existing business rows were unchanged across activation; integrity and foreign-key checks passed. The new projection table was added without destructive migration. Service launch first stalled reading an existing Python cache; bridge imports also waited on existing local package files. Exact observed files were hydrated and the launcher used a temporary bytecode-cache directory. The service recovered without restoring or rewriting business data. Normal service is running with AI Not connected and automation disabled.

Backups, API receipts and runtime verification JSON remain local in this task folder; they are excluded from Git publication. Source code, tests and this report are the publication scope. Native Windows desktop and actual AI quality were not exercised for this change.

## Publication

2026-09-17: code, tests and design notes were pushed to `codex/workbench-optimization-20260916`, commit `545a0933b554c21ec1c51668508b4dd5fb479fd7`. Remote branch readback matched the local commit. Runtime stores, local backups and API receipts were excluded.
