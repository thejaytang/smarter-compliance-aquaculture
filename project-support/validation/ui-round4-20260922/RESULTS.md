# Round 4 implementation evidence

Date: 2026-09-22. The ten approved extracted-content editing items are implemented. Browser acceptance belongs to the coordinator; this record does not substitute unit fixtures for real keyboard/caret acceptance. The only persistent product changes in this round are `markdown-content.js` and `material-editing.js`. No live Material, PE002 data, saved source, Requirement or S/C/D record was changed.

| Item | Implementation | Evidence |
|---|---|---|
| R4-01 | A source/cell/action-state key retains existing passage-control nodes while only their position changes. A new target or changed action availability replaces them. | `editor-retention.test.mjs`: repeated same-passage activation preserves the focused trigger and performs one initial render. |
| R4-02 | Above/Below replaces or toggles the single insertion chooser. Its original source-bound position and caret bookmark remain explicit; opening/dismissal creates no block. | Chooser behavior test: above → below → cancel, repeated trigger toggle, no draft/undo change. |
| R4-03 | Escape is handled on the chooser's own controls, and Cancel uses the same dismissal path. Both restore the original Above/Below trigger, falling back to the recorded caret. | Chooser test verifies trigger restoration and unchanged draft/history. Native Escape/caret behavior remains a browser check. |
| R4-04 | Structural table actions use existing `tableAxis()` and restore the inserted or nearest surviving row/column in the same source-bound block. The outer content scroll is retained. | Table action regression: row insertion targets the corresponding cell, retains scroll and creates one undo record. |
| R4-05 | Tab-separated rectangular text pasted in a table fills cells from the current origin, retaining surrounding values and table metadata. Resulting size cannot exceed 100,000 cells; ragged/oversized input fails before mutation. Plain prose retains ordinary paste behavior. | Pure TSV test covers 2×3 literal cells, script-looking text, neighbours, metadata, ragged/oversized rejection. No clipboard HTML is read. |
| R4-06 | Tab/Shift+Tab moves between existing cells; boundaries yield to the existing accessible exit/control path. Navigation alone creates no cells or history. | 2×3 navigation regression traverses both directions, yields at bounds and leaves draft/history unchanged. |
| R4-07 | Changes and Current text now record edits in the existing bounded 40-snapshot writer history. Undo/Redo is chronological across modes. Reset clears all history/grouping/composition state for another Material. | Current A → Changes B → Current Undo/Redo preserves source evidence; mode switches add no snapshots and reset removes prior history. |
| R4-08 | Enter splits a list item within its existing list and source block, retaining start and nesting. Later items use normal native numbering. Empty final items exit the list or one nesting level. Explicit `li value` structures are rejected before mutation because the current Markdown representation cannot round-trip them. | Serialization and explicit-value guard tests. Normal list split/nested/empty exit require direct browser confirmation. Global Markdown numbering was not changed, and repeated `1.` retains standard Markdown behavior. |
| R4-09 | Caption-only edits preserve image type, attachment, source reference and unchanged attribution. Attribution-only changes preserve the caption. A precise Image label check prevents natural text such as `Imagery...` from losing its prefix. Explicit deletion remains a tombstone with original evidence. | Image retention test and actual frontend-transform → owning save → fresh-service reopen regression. Original attachment bytes unchanged. |
| R4-10 | Cell-only corrections retain current merges, caption and notes. Structural edits adjust relationships via `tableAxis()`. Unsupported merged-table shape changes explain the limitation instead of flattening the active table. Existing Source details includes current table/image metadata alongside original history. | Cell/structure/undo tests and actual save/reopen test verify current merges, notes, caption, source refs and unchanged neighbours, not merely historical retention. |

## Verification

- Complete frontend: **426/426 passed**, [log](frontend-after.log).
- Focused editor tests: **31/31 passed**, [log](editor-tests.log).
- Owning System2 MaterialService and MaterialStore: **35/35 passed**, [log](save-reopen.log). The new regression invokes the actual frontend transformations, explicitly saves through the owning service, constructs a fresh service and reads the saved revision. Image attachment/reference, corrected caption, table merge/note/caption and original bytes are asserted.
- Scoped product/test `git diff --check`: passed.
- The fixture startup initially failed the real snapshot-identity check. It now uses valid synthetic `FX004`, `FX004-001` and `FX004-001_synthetic.html` identities. An explicitly authorized health check started on an allocated port, fetched the real Material route, saved through the real HTTP handler, reopened through a fresh owning service, verified revision 2 and original/attachment bytes, and fetched its page/JS/CSS. The test service then exited normally and removed its temporary files.

## Isolated browser fixture

The coordinator can run from the repository root:

```sh
PYTHONPATH=workbench:workbench/backend/application:workbench/backend/system2/src workbench/backend/system2/.venv/bin/python project-support/validation/ui-round4-20260922/fixture_server.py --port 62847
```

Open `http://127.0.0.1:62847/`. It creates one temporary synthetic source/material and uses actual `Handler` `/api/material/save` and `/api/material` paths with existing version/Origin/CSRF checks. All other write routes are refused. Reopen instantiates a fresh owning service. No application workers, parsing, model calls or business API proxy exist.

The visible controls switch Current/Changes, undo/redo, explicitly Save/Reopen, and inspect current plus saved metadata. Synthetic content contains an ordered list starting at 5, nested items, an attributed image, a 16-row table with one merge and two notes, and surrounding passages. The fixture's extra inspection/undo controls are test harness controls, not new product panels.

Direct browser checks should cover stable focused passage buttons, one chooser, Escape/Cancel restoration, row 12/later-column structural caret recovery, a 2×3 TSV paste with one Undo, cell Tab boundaries, Current A → Changes B → Current Undo/Redo, normal list split/nested/empty exit, and explicit Save/Reopen after image-caption plus table-cell correction. The source and attachment byte checks should remain true.

The explicit-item-number limitation is a current representation boundary, not solved general source-numbering fidelity. It was referred to the planner for later review without changing this round's ten-item count.

## Coordinator acceptance

All ten items passed their applicable checks. Chrome on macOS directly verified the numbered and nested list paths, one insertion chooser with Escape focus restoration, table Tab/Shift+Tab, insertion caret targeting row 3/column 2, and structural Undo. A 2×2 TSV paste created one undo step, retained neighbours and rejected ragged input without a draft/history change. Current → Changes → Current edits undid in chronological order across modes.

Explicit native caption/cell editing, Save and Reopen reached synthetic revision 4. Fresh-service readback preserved image attachment/type/source/credit, current table merges/caption/two notes, modified cells and neighbouring values. Original and attachment byte checks remained true. [Browser evidence](browser-acceptance.json) records the exact saved synthetic material and distinguishes automated-only bounds/DOM/value tests from direct browser evidence. No live business store or Example record was edited.
