# Entry identity, Exception and source-selection interaction

## Delivered

- One displayed Rx per source entry, shared by panes three and four. Local historical child identities remain source-bound Groups, not extra Requirement headings. Saved multi-clause interpretations remain accessible inside the owning entry.
- Only the Rx arrow toggles disclosure; clicking coloured original text does not. One entry opens at a time. The source is a full-width row, independently of Locate text and status.
- Selecting expanded original text opens a pointer-adjacent toolbar: Group / Degroup, a vertical separator, then Subject / Modal Verb / Main Verb / Object / conditions / ❌. Exceptions and subrequirements use a separate full-Requirement reference control. Collapsed text has no annotation toolbar.
- Group preserves complete existing marks within the selected source range. ❌ removes only intersecting field marks, including local child-unit marks, and retains explicit Groups and original text. Degroup preserves fields; operations that would erase NOT or alternative quantities fail with a specific explanation. Empty condition Groups can be degrouped without inventing a QC.
- Plain single fields have no visible QC. New NOT operations are accepted only for Conditions. Exception remains a separate full clause or reference, with independent source scope and no automatic negation. A source-bound exception can contain the full field structure; missing demands are not invented.
- All mutations remain unsaved previews until explicit Save. Opening, selection and disclosure do not create history. Earlier saved IDs, histories and example material are preserved.

## Verification

- **286 Workbench backend tests passed**; **330 frontend tests passed**.
- New regressions cover one-R identity, reference choice boundaries, arrow-only disclosure, plain-field controls, condition-only NOT, separate exception branches, grouping existing marks, source-range clearing, linked local marks, safe degrouping and empty-group removal.
- Normal browser at 62742: selected `should` in the top original; verified the two-section floating toolbar; created a Group containing the existing Modal Verb mark; used ❌ and confirmed the Group remained; used Degroup and confirmed only the Group disappeared. Clicking source text retained expansion. Clicking the arrow removed the editable source region. Switching to R2 left exactly one entry open. Final readback showed only R1 open, no internal R headings, and R1/R2/R3 in the fourth pane.
- Tested the rendered 1440-pixel layout and corrected source-text compression in a narrow third pane. The temporary viewport override was reset. This does not establish a new 200% or native Windows desktop acceptance result.
- Test edits were explicitly discarded through the strong leave warning. Example retained saved personal revision 1; no UI test annotation was saved.

## Activation and boundaries

Nine SQLite stores were consistently backed up for controlled activation. Final normal-service readback confirmed matching served assets, preserved business rows and clean foreign keys. Shared AI remains Not connected; automation remains disabled. Runtime copies, backups, local logs and unrelated workbook changes are excluded from this code increment. No live model call or Site Model assessment was performed.

Current behavior supersedes the previous automatic Exception-to-NOT conversion. There were zero saved canonical-tree sessions in the normal store before activation, so this change required no destructive data migration. Legacy Exception relationships are projected independently on read. The earlier saved records remain unchanged.
