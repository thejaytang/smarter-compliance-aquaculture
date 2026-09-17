# Continuous requirement editor and material header

## Delivered behavior

- Source-ordered, collapsible requirement cards replace Whole source passage, Saved passages and the three phase pages. Every local unit renders in its source position, with original text and clickable field slots together.
- Selection-dependent actions resolve their owning card, including Unicode offsets. Assignment and relation extraction no longer require a phase-transition save. Existing phase records remain compatible; explicit completion still requires all units finished.
- Finish collapses the unit in place; complete collapses the source card. Original text, database identities, references and step history remain preserved. Group count and grouping controls are folded by default; relation text remains visible. Checkboxes have an explicit bounded size.
- The header leads with the title. Previous/Next and the left Material list button are removed. Close immediately follows Save and returns to the list, retaining the open draft; unresolved requirement writes block closing.

## Validation

- 243 frontend tests passed: `ui-tests.log`. After the final completed-unit disclosure refinement, all 10 targeted requirement UI tests passed: `requirements-ui-tests.log`.
- 10 isolated backend requirement tests passed: `requirements-tests.log`. Coverage includes inline assign/extract/done/complete without phase navigation, completed-write guards, restoration, source spans, quantities, actor isolation, replay and stale source protection.
- Browser exercised isolated TS005, material `9ae7419590bec49fd8389243f4ff4f3e`, saved material revision 4. Session `fd4c8534-9a94-477b-9b3b-b31a73571601` split into adjacent R1/R2; selecting Small fish populated R2 only. R1 received The human / shall / inspect / the fish and a linked condition. R2 finished and collapsed in place. Reload retained fields, condition and saved step 9. Finishing R1 and completing the card reached saved step 11. Close returned to Material review; Return to open material retained material revision 4 and step 11. Intake of the next source block created `e2f7a01f-e205-4526-88a0-fc2bb401860c` below the completed card.
- Browser initially exposed globally stretched relationship checkboxes; bounded sizing and folded count/group controls repaired this. Browser selection using Control+Home on macOS produced no useful selection; the backend rejected the empty selection. Exact native text selection then passed; no material data was changed by that failed attempt.

## Normal activation

[Activation record](activation.json) records five consistent pre-restart database copies and comparison after restart. All five databases had zero changed logical tables. Scheduling remained disabled and parent source changes were empty. Normal service remains on 62742. PA004 was saved at personal revision 10 before reload and retained that same saved revision afterward. The normal browser showed the title first, Save followed immediately by the close button, no previous/next controls, and both existing source cards in the continuous Requirements list.

## Limits

Automatic requirement identification remains Not connected. Browser checks used isolated engineering work; they do not certify extraction accuracy or completeness of the example requirements. Native Windows interaction and collaboration ZIP inclusion of the requirement tables remain pending. No external service, dependency or transmission was introduced.
