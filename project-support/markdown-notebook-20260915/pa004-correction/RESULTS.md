# PA004 extraction and continuous Markdown correction

## Observed failure

The normal user page showed PA004 personal revision 2, an unsaved /7 candidate with 544 blocks starting with the Lovdata logo, login and website navigation. The preceding delivery had validated a different new extraction but left this old candidate active. Automatic candidate preview also set the dirty flag and disabled Re-extract. The user subsequently clarified that the middle pane must show the whole Markdown document continuously, with blocks expressing structure and differences inline.

## Implemented behavior

- The complete Markdown body renders at once, without block pagination or numbered cells. Nested chapter/clause sections express hierarchy, while paragraphs flow continuously. Per-block identities, original references and edit baselines remain unchanged. Find navigates matches without hiding the document.
- Deleted wording uses red background and strikethrough; added wording uses green background in the same document. Paragraph and table edits, whole-block deletion and human addition retain prior diff/save behavior.
- Re-extract compares an initial preview with its server-side candidate before replacement. Human edits, issues, review checks, legacy human imports and context changes block this shortcut. The owning store accepts it only for empty saved content and a current machine preview. Only successful completion supersedes the old candidate; its entire payload remains recorded. Failure/concurrent human save keeps prior work.
- Parser /9 converts explicitly marked Lovdata one-row list-layout tables into text list items, preserving original numbering, text, emphasis, source locations and nesting. Normal data tables remain tables. Parser /8 body selection remains active.

## Source fidelity

[check_source.py](check_source.py) reads the exact PA004 snapshot and the backed-up pre-change binding. [source-comparison.json](source-comparison.json) records:

- 342 retained body blocks and 206 excluded navigation/frontmatter/control blocks.
- 34,109 body characters, excluding whitespace, match source text in exact order.
- All 60 chapter/clause headings match.
- All 154 list items match source markers, text and depth. No list-layout table remains rendered as a data table.

This is a bounded saved-HTML check, not PDF/OCR accuracy or legal review acceptance.

## Validation and activation

- [Frontend checks](frontend-continuous.log): 261 passed, including full-document content beyond block 40, nested section boundaries and inline differences.
- [System2 checks](backend-final.log): 98 passed, including preview refresh/replay/failure/concurrent-save protections, materials, body extraction, Markdown persistence, provenance and parser quality.
- [HTTP checks](http-tests.log): 13 passed, including the server-owned actor/identity refresh boundary.
- [Activation receipt](activation.json): normal service restarted at 62742 with five consistent store backups. No logical store rows changed during the restart. Automation remained disabled.
- Normal browser: Re-extract on the unchanged /7 PA004 preview generated /9, then Save recorded personal revision 6. Old candidate retained as superseded; no declarations, Archive or Requirement step was submitted.
- [Final saved-data and served-asset verification](final-verification.json) confirms personal revision 6 exactly matches the independently checked parser result and all three served UI assets match source.
- Actual UI: all 342 blocks and 60 structural sections are present together, including the final paragraph of section 50. Search for Overgangsbestemmelser retained all 342 blocks and navigated its match. Original pane was aligned with chapter 1.
- Isolated existing edit fixture: continuous Markdown displayed word replacement, table-value replacement, whole-paragraph deletion and added paragraph with the retained red/green backgrounds. No business material was edited for this diff check.

Native Windows interaction remains unverified for this correction. No Git commit/push, external model, upload or review confirmation was performed.
