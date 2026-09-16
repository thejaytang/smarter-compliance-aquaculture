# Simplified Requirement relationships and check design

## Delivered behavior

Normal Workbench frontend assets on 62742 now render all seven Requirement fields as semantic colour blocks. Condition units expose recursive conditions only. Quantity summaries and exact/range controls are directly visible in every relationship group, retaining nested owner/path identity. Whole top-level Requirements in the same material are selectable as exceptions or subrequirements. Material-wide display labels are shared by headers, cards, source highlights, references and the fourth-pane list; immutable UUID references are unchanged.

Without selection, the fourth pane shows collapsed Rx entries in number order. Selecting a saved Requirement from either pane synchronizes the other. Scope, Conditions and Demands are deterministic projections of assigned source wording, preserving nested quantities and exception ownership. Each has one editable Logic field. Missing source assignments remain explicit. The six-key backend contract and all historical records remain intact.

AI suggestion is field-specific: Generating transitions to an editable candidate with Accept/Regenerate. Formal fields remain separate until Accept. Concurrent typing, delayed/stale responses, failed regeneration, save-time editing and uncertain-save retries preserve human input. The target service and material scope remain available in Sources & details. Saves and generation require saved splitting. No live AI request was made.

## Verification

- 303 frontend tests passed, including condition-only controls, colour classes, visible nested counts, reference identity, bidirectional selection, branch-preserving source projections, candidate acceptance, stale-result rejection, generation failure, concurrent editing and uncertain-save retry.
- 15 interpretation backend tests passed against isolated stores, exercising the existing save/provider contracts.
- Normal browser: example remained first in Material review. No selected Requirement produced a fully collapsed, numerically ordered Rx list. Expanding R1 and R4 in pane four selected/opened their corresponding pane-three cards and displayed their three source projections plus Logic inputs.
- R1's relationship fields showed counts of 4/4 conditions, 1/1 exceptions and 1–2/2 subrequirements. Reopening exposed the quantity controls directly. Adding a whole R2 exception through its selector produced a source-bound R2 reference and a 2/2 exception group in an unsaved preview.
- The sea-lice Condition child opened with only its recursive conditions and quantity controls; no Subject/Modal Verb/Main Verb/Object assignment buttons were present.
- All test edits on the normal example were discarded through the explicit leave warning. Saved example splitting remained at revision 1. The user's other existing browser tab was not reloaded or changed.

## Limits

The real shared AI service remains Not connected. AI state transitions were tested with simulated responses; real provider quality and native Windows desktop interaction are not newly verified. Display numbers are presentation aliases and can change when the material structure changes; database identity and source/history links remain stable. These are check designs, not compliance findings.

The current workflow contract is [Requirement interpretation](../../workbench/docs/requirement-interpretation.md#simplified-relationship-and-interpretation-workflow-2026-09-16).
