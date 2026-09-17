# Continuous Markdown content

The Extracted content pane presents the entire document as one continuous Markdown reading surface. All body content is loaded together, without block pagination, numbered blocks or repeated cards. Chapter and clause headings form nested structural sections; paragraphs flow within them. Source blocks retain stable identities for editing, provenance and inline differences. This supersedes the earlier Notebook-block presentation.

The HTML original pane has a right-aligned chapter selector. Selecting a chapter jumps immediately; its former Go button and Tools menu are removed.

## Document context and workspace notices

Extraction candidate and Document information are separate collapsible sections above the continuous body. Their open/closed choices survive content rerenders and candidate-status refreshes within the current page session, scoped to the material and view. New sections start expanded. Only the latest extraction attempt is displayed. Earlier attempts and their entries are hidden from this pane, without deleting or resolving their stored records. A failed or resolved latest attempt never causes an older candidate to reappear.

Document information appears only when extracted content or a completed/partial candidate exists, never simply from opening an unextracted original. HTML identity is derived from the bound reader: explicit document metadata, a meaningful document heading, Official Journal title paragraphs, or the saved HTML title. Missing values are not invented. PDF/spreadsheet automatic metadata recognition is not implemented; after extraction their information section permits manual entry.

Choose Edit document information to adjust its Markdown, then Save. On first edit, the source-derived information becomes a material block with `role: document_information`, source references and the original Markdown baseline. It follows the existing material save, actor isolation, history and collaboration snapshot path. Red deletions and green additions survive Save/reopen. The role keeps it in its own collapsible section and excludes it from the body and Requirement intake; Markdown headings inside it do not become body chapter parents. Unedited information remains derived from the immutable saved original, without introducing a material write merely from viewing it. Existing candidate comparison/adoption still protects human changes; replacing a candidate is an explicit decision.

Review-impact notifications appear across the top of the material page, outside the document pane, with a dismiss button. Dismissal only changes presentation and survives rerenders for the same content revision/impact in the current page session. Changed review impact can appear again; required checks and confirmation rules remain intact. Ordinary page status messages also have a dismiss button.

## Direct document editing

**Current text** is the default. The body is one continuously editable document, without opening an editor per passage. Select text across paragraphs to replace or delete it. Enter starts a new passage; Shift+Enter inserts a line break. Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z undo and redo page-local edits. Ctrl/Cmd+A selects the body, excluding document information, controls and review declarations.

Hover a passage to reveal **To requirement** on its right and a translucent **+** at its upper and lower edges. Each + opens an inline toolbar with **Context** (ordinary text), **H1**, **H2** and **Table**. Keyboard users can focus the document, position the caret in a passage and use Tab to reach its controls. These controls sit outside the editable DOM and are never included in copied text.

Tables have directly editable cells. Hover or position the caret in a cell to reveal row controls on the right edge and column controls above the table. They insert before/after or delete the selected row/column. At least one row and one column remain. There is no merge-cell operation. Editing an imported complex table produces simple rows and columns; its pre-edit layout remains in the original and Markdown history. Table caption and notes remain part of the saved Markdown. Whole tables are not currently Requirement intake passages; To requirement applies to nonempty text and headings.

Save the material explicitly before using **To requirement**. The action brings the effective passage into the third pane in source order, independent of the order in which the user clicks passages. Existing identical sessions reopen. UUIDs remain stable; Rx labels are presentation labels. Changes to saved source wording or references make dependent splitting stale under the existing checks.

**Changes** remains available for red/green comparison against the pre-edit baseline, including removed passages. It retains the advanced Markdown and bulk tools. Returning to Current text resumes direct editing. Requirement colours remain in the third pane. Switching views does not save or review anything.

Source blocks retain their IDs, references and original baselines. A removed passage becomes an empty retained block, rather than making its ID point to the next passage. Joining paragraphs retains their combined source context. Insertions inherit a neighbouring source location as context and are marked as human additions, not authenticated source quotations. Unchanged Markdown is reused byte for byte instead of being reserialized on opening. Unsupported structural browser mutations fail closed and restore the last valid page draft. Pasted content is plain text; it cannot introduce executable HTML, remote images or hidden formatting.

Save persists the personal material through the existing version/conflict-protected service. Saving, review and Archive remain separate. Unsaved content and the bounded undo stack exist only in page memory. No automatic database, localStorage or IndexedDB draft/history writes occur. Leaving, reloading or closing retains the strong unsaved-work warning. Editing is temporarily locked while a save/read is in progress and restored afterwards.

The original whole-passage bulk editing helpers remain available in Changes for compatibility. Their edits also preserve IDs and source references and require an explicit Save.

Find and chapter navigation retain the complete document and move to the matching source block. The heading hierarchy remains in the structured model even though the editable DOM is flat to support cross-paragraph selection.

## Body-only extraction

New extraction candidates use `material-structural-parser/9` with `body-content/1`:

- HTML uses a recognizable document body (`#documentBody`, a unique main, or a unique article) and explicit navigation/TOC/frontmatter/control markers. Linked footnotes are retained when their targets live outside that body. Body headings and ordinary text remain in order; basic inline emphasis and list markers become Markdown source.
- Explicit Lovdata lettered/numbered layout tables become Markdown list items with original markers, wording, emphasis and nesting depth. Ordinary data tables retain table structure.
- Native PDF TOCs require a named contents heading plus recognizable page entries, a corresponding TOC table, or an unambiguous joined TOC paragraph. Short non-normative cover pages before an identified TOC and repeated marginal headers/footers can be excluded. Explicit chapter/section headings are retained. No fixed number of leading pages is discarded.
- Unknown or ambiguous sections remain for human review. Scanned-page recognition and all-layout extraction accuracy are not established by these rules.
- `body-selection.json` records excluded blocks, original references and reasons. Candidate processing details expose the exclusion summary. Originals, the complete structural parser artifact and prior saved versions are retained.
- Filtering applies to new candidates. An untouched, unsaved machine preview can use Re-extract directly; successful refresh retains the old candidate as superseded without claiming human review. Edited previews must be saved first. Saved human content continues through the existing protected comparison/adoption flow.

Material review means checking that the body content, including its headings, tables, figures and notes, is faithful and that exclusions are appropriate. Reviewing an original range does not require copying its website navigation or table of contents into the body document.

## Storage and local tools

Markdown is stored inside the existing material blocks (`markdown_source` for initial formatted extraction and `markdown` for source/baseline/original revision data). It therefore follows the owning material's saved history and existing material snapshot path. Full workspace ZIP version 2 also includes saved Requirement splitting and interpretation records; unsaved page edits are not included.

The browser uses locally bundled [markdown-it](https://github.com/markdown-it/markdown-it) and [jsdiff](https://github.com/kpdecker/jsdiff). A native contenteditable surface provides direct body editing; textareas remain for advanced Markdown and document metadata. No hosted editor, external model or browser-time package fetch is used. Versions and dependency resolution are pinned in `workbench/frontend/package.json` and `package-lock.json`; vendored assets and licenses are shipped with the UI. Node/npm is only required to rebuild those assets:

```sh
cd workbench/frontend
npm ci --ignore-scripts
npm run build
```

[Current correction and validation](../../project-support/markdown-notebook-20260915/pa004-correction/RESULTS.md) owns current delivery evidence. Native Windows interaction remains unverified.


### Pane-width continuity

The second-pane document and block highlights use the full available pane width, without a fixed character-width cap. Resizing the pane repositions existing passage controls and table edge tools through a ResizeObserver without rerendering their buttons, changing selection, closing insertion menus or saving content. The observer is disconnected when rebinding or resetting the editor.
