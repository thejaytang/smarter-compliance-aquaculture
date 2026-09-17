# Human Review Contract

The directory/storage migration preserves the existing interface and source semantics.

- One continuously editable extracted document; stable block IDs and exact source references. Current text and Changes are reading/editing modes, not saved versions. Many blocks may support one Requirement, ordered by source position.
- One Rx identifies one Requirement entry. Its header toggles disclosure except for action buttons; coloured source text is selectable only while editing and does not toggle. One entry opens at a time. Locate synchronizes the three source/structuring views. Remove requires confirmation.
- Selection exposes Group and grammatical fields. Groups alone carry exact/inclusive-range quantities. Only an explicit Group relationship holds a source-expressed connector such as `including`; it is metadata, not a counted item. AND/OR quantities preserve their stored semantics. Do not infer extra NOT operators from wording.
- Exception and Subrequirement link complete other Requirements. Preserve explicit quantities on linked sets, ordered entries and per-link removal. Removing a Group removes its included elements; no silent flattening.
- Fourth-pane Scope/Conditions/Demands derive source wording from the selected Requirement. Logic text remains editable. AI suggestions require a click and explicit adoption; regeneration must not overwrite human edits. Source references, unknowns and provenance remain available without inventing requirements.
- The generated checking chain is derived from saved structured content and check design. A subset expression is a design for later evaluation, not an actual compliance result.
- Save, review, candidate acceptance and archive are separate. Unsaved work is page memory. Manual history is append-only after explicit save. Shared visibility does not change creator IDs; history records actual authors.

See [storage and exchange](storage-and-exchange.md) for saved contracts and cross-version bindings.
