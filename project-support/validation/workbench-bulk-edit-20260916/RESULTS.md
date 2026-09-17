# Bulk content editing checkpoint, 2026-09-16

## Delivered

The second pane supports passage checkboxes, Shift-click ranges and a heading action to select all preceding body passages. The confirmation applies one batch to the unsaved page draft. Bulk deletion retains stable IDs, source references and Markdown baselines. Current text hides deleted passages; Changes retains redlines. Bulk editing exposes separate Markdown fields in one dialog so source ownership and table structure do not collapse into an unrelated first block. Undo restores the pre-batch blocks until an intervening change. Document information is outside body selection.

The close-material action now uses the explicit unsaved-work dialog. Material saves and extraction status refreshes guard unsaved Requirement splitting. Unsaved content, splitting and interpretation changes are not automatically written to browser storage or history. Old saved history remains retained.

## Verification

- Node regression: 286 tests passed, including range selection, bulk edits/deletion, immutable source references, undo, stale/read-only guards and leave warnings.
- Workbench backend: 264 tests passed. The final deleted-session projection adjustment passed the 16 Requirement tests again.
- System2 material tests passed, including preferred-version selection, idempotency and stale-save rejection.
- In-app browser on isolated port 53161: select-before-section chose four passages, including heading/list/table; Shift-click chose the same four. Delete retained Chapter 3 and its following paragraph. Undo restored all content. Close prompted; explicit Save created personal revision 2; reload retained the deleted effective text. Batch editing of two passages applied once; Discard returned to saved revision 2.
- Read-only SQLite inspection: revisions 0, 1 and 2 exist; only explicit Save added revision 2. Unsaved subsequent edits did not add history. All source references in revisions 1 and 2 match.
- Normal service 62742 was activated after eight consistent database backups. Existing business rows were unchanged; foreign-key checks passed. Served UI assets matched files. API remains Not connected and automation remains disabled.
- The user's already-open browser draft was not reloaded or edited. Save it before refreshing to load the new UI.

The local activation manifest and runtime databases are private recovery artifacts and are not included in Git publication.

## Boundaries and outstanding earlier requests

This checkpoint establishes bulk content interaction, manual-save regression and source/runtime activation. It does not establish all earlier interaction acceptance. The shared-API whole-document Auto-extract flow, the fully populated normal `example` material, remaining cross-pane interaction acceptance and fresh native Windows desktop testing are still pending. The example specification alone is not an installed demonstration material. No real model call or Site Model compliance evaluation was run.

Subsequent update: the normal example is now installed and pinned first; see the [example checkpoint](../workbench-example-20260916/RESULTS.md). Other boundaries above remain unchanged.

## Direct-writing follow-up

The later user request supersedes per-block editing in the default second-pane view. Current text is one native contenteditable document. Selection across paragraphs supports replacement/deletion; Enter splits, boundary Backspace/Delete joins, and Ctrl/Cmd+Z restores the prior source-bound block state. Passage controls are outside the editable DOM. Hover or keyboard focus exposes To requirement and upper/lower + insertion menus for Context, H1, H2 and Table. Table cells edit directly, with row/column insertion and deletion at their edges; no merge operation is exposed. Requirement intake continues to require explicitly saved content and follows document order.

Deleted blocks keep their IDs, references and original baselines. Joined passages retain combined source context. Added paragraphs are explicitly human additions. Opening unchanged Markdown does not normalize or rewrite it. Unsupported structural changes fail closed. Paste accepts plain text only. Empty and metadata-only documents remain editable without opening a new history record. Save/loading locks release correctly when an operation ends.

Validation on macOS:

- 314 frontend regression checks passed. This includes source-order Requirement intake and editor loading/saving lock recovery.
- 267 Workbench backend/HTTP checks passed; no schema or database migration was needed.
- 37 System2 material, body and Markdown checks passed, including saved baselines and original source/history protection.
- 16 isolated browser DOM checks passed under the app's strict script/style policy. They cover formatting/Unicode, repeated text, cross-paragraph deletion, exact undo/redo, heading splits, joins, select-all replacement, rerendered empty documents, metadata-only first input, before/after insertion, table dimensions/caption/notes, selection across table cells, intake guards and fail-closed identity checks. Reproduce by serving `workbench/` locally and opening `tests/browser/continuous-document.html`, then choosing Run browser checks. The fixture has no API or storage calls.
- Normal 62742, agent-owned example tab: direct Unicode typing, Enter, unsaved status and strong leave warning; Context/H1/H2/Table menu; Table insertion, direct cell typing, 2→3→2 rows and 2→3→2 columns by actual button clicks; Changes view displayed additions. At 1280 pixels, To requirement reopened saved R1 and the list retained R1, R2, R3/R4 source order. Table controls were exercised at 1440 pixels. All test edits were explicitly discarded. The saved example remains personal revision 1; the user's separate tab was untouched.
- An actual-browser failure caught inline position attributes blocked by CSP. Positioning now uses CSS property assignment and the fixture checks the same strict policy. Both control groups now target their correct row/column.
- Mechanical UI scan reported only existing blockquote styling and the existing PDF image placeholder (its source is supplied at runtime); no new issue was reported for the direct editor.

The current UI uses standard browser editing/selection APIs and platform-neutral source transformations. Native Windows desktop/IME/assistive-technology acceptance has not been run here. Real model calls remain outside this verification. The separate Changes view retains advanced Markdown/bulk tools for compatibility; tables themselves are not whole-Requirement intake passages.

Published on 2026-09-16 as code commit `6297096aee278f8f997be0a1f9fb53dea7621ebe` on `codex/workbench-optimization-20260916`, with [PR #2](https://github.com/thejaytang/smarter-compliance-aquaculture/pull/2) updated. Push confirmed; main was not merged. [Windows/Ubuntu CI run 35089832939](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35089832939) was in progress at this handoff, not counted as a passing result.
