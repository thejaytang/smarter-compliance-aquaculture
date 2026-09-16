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
