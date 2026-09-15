# Continuous Markdown content

The Extracted content pane presents the entire document as one continuous Markdown reading surface. All body content is loaded together, without block pagination, numbered blocks or repeated cards. Chapter and clause headings form nested structural sections; paragraphs flow within them. Source blocks retain stable identities for editing, provenance and inline differences. This supersedes the earlier Notebook-block presentation.

The HTML original pane has a right-aligned chapter selector. Selecting a chapter jumps immediately; its former Go button and Tools menu are removed.

## Document context and workspace notices

Extraction candidate and Document information are separate collapsible sections above the continuous body. Their open/closed choices survive content rerenders and candidate-status refreshes within the current page session, scoped to the material and view. New sections start expanded. Only the latest extraction attempt is displayed. Earlier attempts and their entries are hidden from this pane, without deleting or resolving their stored records. A failed or resolved latest attempt never causes an older candidate to reappear.

Document information appears only when extracted content or a completed/partial candidate exists, never simply from opening an unextracted original. HTML identity is derived from the bound reader: explicit document metadata, a meaningful document heading, Official Journal title paragraphs, or the saved HTML title. Missing values are not invented. PDF/spreadsheet automatic metadata recognition is not implemented; after extraction their information section permits manual entry.

Choose Edit document information to adjust its Markdown, then Save. On first edit, the source-derived information becomes a material block with `role: document_information`, source references and the original Markdown baseline. It follows the existing material save, actor isolation, history and collaboration snapshot path. Red deletions and green additions survive Save/reopen. The role keeps it in its own collapsible section and excludes it from the body and Requirement intake; Markdown headings inside it do not become body chapter parents. Unedited information remains derived from the immutable saved original, without introducing a material write merely from viewing it. Existing candidate comparison/adoption still protects human changes; replacing a candidate is an explicit decision.

Review-impact notifications appear across the top of the material page, outside the document pane, with a dismiss button. Dismissal only changes presentation and survives rerenders for the same content revision/impact in the current page session. Changed review impact can appear again; required checks and confirmation rules remain intact. Ordinary page status messages also have a dismiss button.

## Edit and review

- Click a block to reveal its actions. Double-click it, or focus it and press Enter, to edit its Markdown.
- Use Heading, Bold, Italic, List, Numbered list, Quote, Table or Link. Only the active block shows the formatting toolbar.
- Shift+Enter renders the block. Escape also renders without discarding input. Undo/Redo are available in the current block; saved material history remains available across sessions.
- Deleted content has a red background and strikethrough. Added content has a green background. Replacing text shows both fragments. Whole-block deletion remains visible in the revision view.
- Show changes switches between the revision view and the effective current text. The comparison baseline is the block's state before its first Markdown edit; Save does not reset it. Earlier edits made before this feature remain in material history.
- More contains Insert above/below, Delete content, Restore original and Source details. + Block appends a block. New blocks inherit a nearby source location as context and remain human additions; this does not prove the added wording appeared in the source.
- Save persists the personal material with its Markdown, baseline and source links. Saving is separate from review confirmation and Archive. Unsaved edits use the existing browser recovery journal and version-conflict protection.
- After saving, To requirements sends the whole effective block text. Markdown syntax and deleted revision text do not enter the requirement unit. Editing its source text later makes an existing splitting session stale under the existing guards.

Basic headings, paragraphs, explicit line breaks, lists, emphasis and simple tables render in source order. Markdown does not reproduce the original PDF's exact typography or merged table geometry. The full original remains in the left pane; the pre-edit block and table geometry are retained with its baseline. Editing a complex table displays that limitation. Images remain source-bound descriptions rather than remote fetches. Raw HTML and executable links are not enabled in Markdown.

Find keeps the complete document visible. Press Enter in Find to move to the next matching block; chapter navigation scrolls within the same full document.

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

Markdown is stored inside the existing material blocks (`markdown_source` for initial formatted extraction and `markdown` for source/baseline/original revision data). It therefore follows the owning material's saved history and existing material snapshot path. This does not change the separately documented exclusion of manual Requirement splitting tables from collaboration ZIPs.

The browser uses locally bundled [markdown-it](https://github.com/markdown-it/markdown-it) and [jsdiff](https://github.com/kpdecker/jsdiff). Native textareas provide Markdown source editing. No hosted editor, external model or browser-time package fetch is used. Versions and dependency resolution are pinned in `workbench/frontend/package.json` and `package-lock.json`; vendored assets and licenses are shipped with the UI. Node/npm is only required to rebuild those assets:

```sh
cd workbench/frontend
npm ci --ignore-scripts
npm run build
```

[Current correction and validation](../../project-support/markdown-notebook-20260915/pa004-correction/RESULTS.md) owns current delivery evidence. Native Windows interaction remains unverified.
