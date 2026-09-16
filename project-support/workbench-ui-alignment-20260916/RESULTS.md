# Workbench UI alignment validation

Date: 2026-09-16. Base: `f74a780`, branch `codex/workbench-optimization-20260916`.

## Scope and result

Applied the Impeccable Operate layout/polish workflow to the existing four-pane material workspace. A source-only layout assessment and a bounded browser correction/confirmation pass addressed conflicting control styles, redundant root gutters, inconsistent pane minimums, multiline text alignment, and action placement. Existing semantic colours, source content, Requirement structure, manual saves and API behavior are preserved.

Changes: common 12px pane gutters and 40px headers; corrected remove controls and aligned link selectors; explicit Group indentation without anonymous root boxes; compact quantity controls; aligned second-pane passage/table controls; aligned fourth-pane summaries, sources, Logic and Save; narrow-screen task bars and dialogs. The pane minimum calculation now accounts for the actual open panes, rails and separators.

## Automated checks

- `node --test workbench/tests/*.mjs`: **347 passed, 0 failed**. Includes a new pane-minimum regression for all-open, partially collapsed, one-open and all-collapsed layouts. Later confirmation corrections touched CSS only.
- `git diff --check`: clean at implementation validation; checked again before commit.
- One Impeccable detector run returned six warnings. Retained narrowly scoped exceptions: existing semantic relation borders/outer annotation underlines, the collapsed-rail marker, and Markdown blockquote styling are meaningful source/navigation cues. The PDF region image receives its source dynamically, so the literal-template missing-src finding does not establish a broken image. No warnings were hidden by changing the detector.

## Browser evidence

Normal service: `http://127.0.0.1:62742/`. Current English example PE001, material `3069f79e2481e4c18f1e268c8344de9f`.

| Check | Observed result |
| --- | --- |
| 1920px viewport | Page width 1920px; all four panes fit. |
| 1440px viewport | Pane headers align at 40px; header actions stay together and source chips wrap. |
| 1280px viewport | Page width 1280px; workspace client width 1224px and content width 1261px. Individual panes retain 260/340/320/320px and do not overflow internally. |
| 390px viewport | Page remains 390px; workspace alone scrolls horizontally. Save and Close remain inside the viewport. Help dialog is 356px wide, with no internal horizontal overflow. |
| Actual Chrome 200% | Native Chrome reported 200%; viewport was 1280 CSS px with DPR 2. Page width remained 1280px, workspace content 1261px. Headers, source cards and actions remained aligned. Restored to 100%, verified viewport 2560px and DPR 1. |
| Controls | Remove controls measure 28×28px with zero padding. Link selector and button measure 32px high with matching bottom edges. Reading-mode text has a dedicated 124px select. |
| Deep groups and long text | R4 nesting retains actual hierarchy without anonymous outer borders. Multiline leaf IDs align at the top. Long fourth-pane source wording remains complete in a scrollable area. |
| Collapse and restore | Keyboard Home collapses panes into 44px rails. Double-click and Enter restore them. Default pane widths were restored after the check. |
| Second-pane actions | Keyboard focus reaches To requirement; button is centered vertically with a 12px right inset. Context/H1/H2/Table insertion menu is accessible. |
| Tables | A temporary table stayed within its passage; row/column edge controls were reached. The observed 2px control overlap was corrected by matching button height to the existing 28px placement offset. |
| Dialog and discard | Help opens/closes at narrow widths. Leaving the temporary table showed the unsaved-work warning; explicit discard removed only the test edit. |

## Data and verification boundary

The complete Requirements API response, including all four active sessions and deletion metadata, exactly matched the saved pre-test snapshot after browser testing. No material, splitting or interpretation save, review or archive action was taken. Temporary content edits were discarded. No source or database migration was made.

The user's existing Chrome tab contained unsaved splitting work. It was not reloaded, saved or discarded. The zoom check used a separate temporary tab, which was closed after restoring 100% zoom. Existing user tabs remain open.

This pass establishes the listed local macOS browser behavior and frontend regression results. Native Windows execution and real-model quality were not tested in this UI-only change. No actual compliance assessment was performed. Reload after saving existing page work is required to load the new assets in an already-open tab.
