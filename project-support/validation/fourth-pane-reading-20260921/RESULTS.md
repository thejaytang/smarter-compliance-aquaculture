# Fourth-pane reading view, 2026-09-21

Implemented locally at the user's request to minimize interface burden. No commit, push or release.

## Result

- The fourth pane follows the selected third-pane Requirement instead of repeating the entire Requirement list. Reopening saved work selects the saved Requirement and loads its interpretation.
- Default reading shows Scope/A, Condition/B, Demand/C, linked concept names and the B ⊆ C relationship. Nested AND/OR and group NOT remain visible as structured prose; there is no semantic flattening or automatic compliance verdict.
- On the real R1, default visible controls fell from **15 buttons and 11 inputs** to **3 buttons and 0 inputs**. The three buttons are Edit, Save draft and Confirm interpretation. Save is disabled until needed; confirmation still respects saved state, source freshness, missing information and concept meanings.
- Edit exposes the existing rule/concept controls. Done editing changes presentation without saving, clearing text or confirming review. The shared object and period remain under Check context. Stable concept IDs remain stored without occupying the everyday view.
- Evidence consolidates mapped source wording, earlier explanations, exact quotations and supporting information. More contains generation, context management, history and advanced data integration. Unconnected mapping warnings no longer appear in the default reading flow.
- No schema, backend, dependency or business-data migration. The four live business-store files are byte-identical before/after; all Example Requirements, 21 active interpretations and prior history remain unchanged.

## Checks

- **381 frontend tests passed**: [frontend-tests.log](frontend-tests.log). New checks cover selected-Requirement rendering, switching read/edit without mutating a draft, nested OR/NOT rendering and escaping, shared concept display, immediate Save availability after an input change, and selected-entry restoration on reopen.
- The real Example was checked in the desktop browser at the existing narrow four-pane layout. R1 presents readable text; R4 retains nine proposed concepts and disabled confirmation. Both remain human-pending. The rendered original HTML remains in the first pane.
- A fresh isolated synthetic workspace exercised actual browser actions: Edit, change a rule, confirm a shared concept, Done editing, Save draft, separate Confirm interpretation, and reload. The modified rule and confirmation persisted across reload with three saved revisions. A later unsaved edit cleared confirmation in the page, left the saved revision unchanged, and was discarded through More → History → Reload saved interpretation. No test writes went to the permanent Example.
- API readback verifies the synthetic saved rule, shared concept confirmation, exact saved source binding, retained original explanation and three history revisions: [synthetic-saved-readback.json](synthetic-saved-readback.json).
- All four live business-store hashes match the pre-edit snapshot: [business-preservation.json](business-preservation.json).
- The one mechanical design-detector pass reported four pre-existing CSS warnings in source annotations, collapsed-pane styling and an old group border. The new reading surface adds none; its editing group overrides the old 2px border with 1px. Source semantic colours and unrelated pane affordances were preserved. See [design-detector.json](design-detector.json).
- The initial isolated fixture launch lacked the application import path and stopped before starting a service. It succeeded using the declared component environment and application/shared import roots; no dependency installation or environment change was needed.

The isolated service/tab were stopped/closed after verification. The normal live tab remains open. Real provider calls, actual Site Model execution and native Windows UI were not run. Existing model-prepared content was not reclassified or marked human-reviewed by this interface change.
