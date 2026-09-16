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

## Publication

On 2026-09-16, implementation commit `50dc48039e78729129d7ed90ff01f7aa05407727` was pushed to `codex/workbench-optimization-20260916` and verified as [PR #2](https://github.com/thejaytang/smarter-compliance-aquaculture/pull/2)'s head. [CI run 35098706313](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35098706313) started for this exact commit and was still running at handoff. Local pass counts above do not assert completed remote or native Windows acceptance.


## Source-negation follow-up

User requested removing explicit NOT authoring in this version. Plain and nested Conditions no longer show a NOT button. Frontend rejects a stale NOT action before changing a draft; backend rejects the retired operation without adding history. Source wording such as “not installed in the North of Norway” or “unless rope secured” is retained verbatim, without generating an extra NOT operator. Historical stored negation remains readable and visibly read-only; no saved structure or history migration occurs. Group QC, including the previously requested Not All quantity shortcut, and independent Exception relationships are unchanged.

Validation: 286 backend and 332 frontend tests passed. Regression cases cover absent controls for plain/nested Conditions, literal negative wording in fourth-pane projection, stale actions without a draft change or saved revision, and historical structure compatibility. Normal 62742 was activated with nine consistent owning-store backups. Readback confirmed unchanged saved business tables, clean foreign keys and matching served assets. During activation a transient local file-read stall and SQLite I/O error occurred; exact identified iCloud placeholder files were hydrated, then readback passed. No database restore or content rewrite was performed. The actual example browser page shows R1 open, R2/R3 closed, 13 field/group blocks, zero NOT controls, literal negative source wording and no unsaved changes. Native Windows desktop and real AI were not exercised for this change.


## Colour, quantity and spacing follow-up

Source-preview containment now recognizes same-field duplicate annotations and an owning reference over its own child field, including equal-span references. The first example's “be checked” and “replaced” use the same green as Main Verb, and “for integrity” uses the same orange as Object; genuine unrelated field conflicts retain overlap indicators. Source and decomposition records are unchanged.

MIN–MAX is a fifth, mutually exclusive quantity option. Its inputs are disabled until selected, and shortcuts disable them again. The mode choice itself neither writes history nor changes quantity. Bounds retain numeric validation, preview and explicit-save semantics. The separate QC heading is removed. Explicit Groups indent their children and show connector guides. Requirement headers show Locate followed by Remove with an entry-specific confirmation and Cancel; removal retains existing recoverable history and protects unsaved work. Fourth-pane cards have protected 14px/16px gutters and inset disclosure markers, and second-pane To requirement has a reserved text gutter with a 12px right inset.

Validation: all 336 frontend tests passed, including colour conflicts, equal-span references, exclusive range selection, stale/readonly guards, targeted removal confirmation/cancellation and unsaved protection. Actual normal-browser checks verified exact green/orange colours and no false overlap in example R1; MIN–MAX disabled/enabled inputs, live [1,3] preview and return to disabled bounds after All; Remove R2 confirmation and cancellation; fourth-pane 14px/16px computed padding; second-pane button width 84px, right inset 12px and exact vertical centering. Test drafts were explicitly discarded; example remained Personal revision 1. This frontend-only increment used the existing normal service without a backend restart. Native Windows desktop was not exercised.

## Pane width, complete-entry links and source register follow-up

Second-pane Markdown now fills its pane instead of stopping at 75ch. A ResizeObserver repositions existing passage/table controls without replacing their menu DOM, losing focus or saving content. Exception and Subrequirement have separate visible selectors for other complete Rx entries. New inline relation fragments and links to internal units are rejected server-side. Linked entries display Rx plus source text and Unlink. Existing inline relation content remains read-only under Saved decomposition; saved identities/history are unchanged.

Source register now places File type after Original. Only STORED originals display their recorded format (HTML/PDF/etc.); undownloaded sources display an em-width dash and missing recorded formats display Unknown. No URL-extension inference is used.

The user explicitly identified PA001 and PA004 as unwanted testing work. PA004's old personal revision 10 and PA001's empty personal copy were retired from active workspace selection with their complete databases/descriptors retained locally for recovery. Both return to shared revision 0 / Not extracted. Two PA004 test Requirement entries were removed through the normal recoverable API. Empty unchanged personal copies no longer appear as Your saved content in the material queue. The pinned example remains personal revision 1. This supersedes older state references to PA004 revision 10 as active work.

Validation: **339 frontend and 288 Workbench backend tests passed**. Normal 62742 was restarted with consistent snapshots of nine owning stores; saved business tables and foreign keys were verified before the explicitly requested cleanup. Browser checks: at 1920px the second-pane document reached 689.19px and passage 665.19px, beyond the former 661px cap, with exact button centering and 12px right inset; viewport override and widths were reset. A cross-entry Exception link to R2 appeared with full entry text and Unlink; the test draft was discarded. PA001/PA004 list rows show First processing / Not extracted, and reopening PA004 had empty extracted content. The register displays HTML and PDF for stored files and dash for undownloaded files. No real AI call, Site Model execution or native Windows desktop check was performed.

Fourth-pane QueryBuilder consolidation and group NOT are a requested design direction, not delivered in this increment. See the interpretation guide's pending section for the proposed simplified Sources, automatic checking-chain preview, inline rule editing, explicit Save and History arrangement.

## Compact relation picker correction

The previous complete-entry link UI wrongly repeated the Exception/Subrequirement heading inside a second coloured panel and kept large legacy inline decomposition cards in the daily editor. Each relationship now has one coloured section, one heading, one dropdown and Link; existing external Rx links use compact buttons with an Unlink action and source-text tooltip. Legacy inline relationships, including their exact quantities and source wording, remain visible only within History & structured result → Earlier inline relationships. A small in-place history note identifies their presence. No saved source, semantic tree or history is rewritten. Quantity controls remain on groups of actual links; mixed legacy groups retain their quantity in history instead of presenting hidden fragments as visible choices.

All 340 frontend tests passed, including a regression that reproduces the legacy/external mixture, rejects duplicate panels/headings, verifies preserved history/quantity and unchanged data, and retains QC for external-link groups. Backend logic is unchanged.

Normal-browser verification on example R1 found exactly two relation panels, each with one dropdown and no descendant relation panel. Choosing R2 produced only a compact R2/Unlink pair. The preview was discarded, the viewport reset, and the example remained saved revision 1. Static frontend changes are served on normal 62742; no database migration or backend restart was needed.


## Subrequirement quantity and link cards

The 2026-09-16 follow-up replaces compact Rx/Unlink pairs with vertical reference cards. Each row shows Rx and source wording, with a top-right × that removes only the reference node. Subrequirement and Exception reference groups show quantity controls above their direct children. Sibling selection can create an inline nested group; every level retains its own exact/range quantity and a subgroup counts as one parent member. A completed entry reopens as an unsaved preview for these actions. Existing source/history, target Requirements and manual-save boundaries are unchanged. Legacy mixed groups retain their hidden quantities in history instead of assigning those counts to a partial visible list.

Validation: all 346 frontend tests and 17 group backend tests passed. New regressions cover nested reference quantities, per-link removal routing, completed-entry draft reopening and read-only controls. On the normal Chrome example, removing R3 left links R2/R4 while the separate R3 Requirement remained. Grouping R2/R3 produced an inline subgroup; choosing inner Any [1,2] and outer All 2 retained both independent values. Screenshots confirmed vertical cards, nested indentation and each row's separate ×. Both previews were explicitly discarded through the leave warning. The complete saved Requirement API response matched the pre-test response exactly, with four active sessions. No browser test created a saved revision.

This static UI increment is served by normal 62742 without a backend restart or database migration. Native Windows desktop interaction and real AI were not exercised. Unrelated runtime files and workbook edits are excluded from publication.
