# Material interaction revision, 2026-09-14

Implemented the user's staged three-pane interaction in `workbench/ui/materials.js` and `materials.css`.

- Empty content starts with one centered **Auto-extract** action. Its request and real candidate polling display an accessible loading indicator. The Requirements body stays empty until content exists.
- A first real candidate appears as editable heading/text fields following parent hierarchy, plus separate table and original-bound image components. Block tools and table operations are collapsed. Existing candidate comparison, parser limitations and original links remain accessible.
- The content footer contains two explicit reviewer declarations covering the complete original/omissions/tables/images and hierarchy/order/notes/dependencies. Archive requires both, with existing unresolved-source, conflict and candidate gates retained. Content or issue edits clear the declarations.
- Save remains a local personal-workspace draft operation. When checked content changed, the UI first saves its body, then stamps the explicitly selected checks on that exact returned body and original identity. Failure retains the draft; a different returned body/source cannot inherit the checks. Save does not confirm, adopt or archive content. Coordinator comparison/adoption and exact-master final confirmation remain separate.
- Requirements Auto-extract and Re-extract become available after content exists. Re-extract opens the requested human-edit preservation/context warning with Cancel and Confirm controls. **The actual Requirements processor/schema remains unconnected.** The controls truthfully show Not connected and do not simulate results or modify Requirements. Protecting existing human-edited Requirement items during real processing remains an integration requirement for the future adapter, not a claimed implemented processing capability.

## Verification

- [Frontend regression](frontend-tests.txt): 205 passing tests, including empty/loading states, declaration gating/reset, body/source binding, second-save recovery, structured editors and Requirements confirmation/cancellation.
- [Workbench material regression](workbench-material-tests.txt): 35 passing tests.
- [Content confirmation/impact/processor contracts](content-contract-tests.txt): 45 passing pytest cases. An initial unittest invocation collected zero cases and was corrected to the owning pytest runner; it was not counted as validation.
- Codex in-app browser, isolated service on port 52345: real TS001 HTML extraction produced eight blocks (headings, text, table, image). Observed the loading state, separate editable components, blank initial Requirements pane, subsequently enabled entry, truthful Not connected result and the requested re-extraction dialog. Cancellation retained the draft.
- Browser Save succeeded with unchecked declarations and reopened as personal revision 4. After an isolated text edit, checking both declarations enabled Archive; another edit unchecked both and disabled Archive. Rechecking and clicking Archive saved revisions 5 and 6, then opened the guarded coordinator comparison. No adoption or content confirmation was performed.
- [Database readback](saved-state.json): personal revision 6 has eight blocks, checked original scope and `confirmation: null`; master remains revision 0 with no blocks or confirmation. No normal business content was extracted, edited, reviewed, adopted or archived during validation.
- Browser layout checked at the side browser's native narrow width and a temporary 1440×960 viewport to inspect the parallel panes. The temporary viewport is restored afterward. The final isolated browser console showed no errors or warnings. This is scoped interface verification, not broad extraction-quality or Windows acceptance.

[Code fingerprints](code-fingerprints.json) identify the checked revision. `fixture/` retains isolated evidence and source copies. `serve.py` uses current product code with only the material worker enabled. Normal business databases and automatic source/discovery/scheduling controls are outside the test fixture.

Normal port 62742 was refreshed and the existing PA004 personal material reopened read-only. The in-app browser shows the new centered content Auto-extract entry, an empty Requirements body and disabled Requirements Re-extract; no console errors were reported. The temporary viewport was reset and the isolated browser tab closed. The isolated service was stopped.
