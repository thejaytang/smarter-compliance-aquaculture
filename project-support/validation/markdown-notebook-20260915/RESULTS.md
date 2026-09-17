# Markdown notebook and body-only extraction

The later [PA004 and continuous-document correction](pa004-correction/RESULTS.md) supersedes the Notebook-cell presentation and the earlier parser /8 current-state claims below. This report retains the first delivery evidence.

Date: 2026-09-15. Delivered on the normal local Workbench at `http://127.0.0.1:62742/`.

## Result

The user's Jupyter Notebook clarification owns the interface: vertically stacked rendered Markdown cells with explicit lightweight boundaries, one active editor and its tools. Source metadata and repeated cell forms are absent from the default view. The user's correction owns the revision colors: red background plus strikethrough for deletions, green background for additions. The source before a cell's first Markdown edit remains its baseline across saves. Effective current text, excluding deletions, passes to the existing requirement splitting flow.

New candidates select body content with headings. Recognizable TOCs, navigation, cover metadata and repeated page chrome are excluded with source-bound evidence. An actual saved PA001 HTML snapshot retained 224 body blocks and excluded 192 non-body blocks, beginning at the first chapter. Body headings and footnotes remained. The first real-material pass revealed in-body Share paragraph controls; the extractor now separates those controls before body selection. [Actual-source summary](real-html-evidence.json) records the evidence. This one document and synthetic PDF checks do not establish all-document body-selection accuracy.

The [user contract](../../workbench/docs/markdown-content.md) owns tools, behavior, storage, filtering and limitations. [Code manifest](code-manifest.json) identifies the delivered files.

## Validation

| Validation | Result | Evidence |
| --- | --- | --- |
| Full frontend suite | 256 passed | [Log](frontend-final.log) |
| Workbench backend suite | 217 passed | [Log](workbench-backend.log) |
| Relevant System2 material, parser, provenance and review checks | 110 passed | [Log](system2-final.log) |
| Final body-selection checks, including retained foreword | 8 passed | [Log](body-final.log) |
| Final Markdown-focused checks | 11 passed | [Log](markdown-final.log) |
| Served local assets | All checked assets match current source; no parent source drift | [Evidence](served-assets.json) |

Earlier new-test fixture failures used incomplete snapshot metadata and an HTML fragment without a document signature. Corrected fixtures passed; the earlier logs remain historical evidence. No production parser fallback was introduced to accommodate invalid fixtures.

Actual browser work used isolated TS005 material on `127.0.0.1:62075` with workers disabled. It verified:

- Source-ordered title, paragraph, list and simple table cells with no default textareas or repeated block forms.
- Inline replace, Undo/Redo, Shift+Enter rendering, Save and reload, retaining the deletion and insertion marks.
- Table value replacement, a green added cell and keyboard deletion of a complete cell. Final fixture material revision 4 retained all baselines and original links; content remained unreviewed.
- Show changes toggled to effective content without deleting stored revision evidence.
- To requirements created a source-bound session containing `inspect`, with the deleted `remove` absent from unit text.
- A 1280-pixel screenshot exposed wrapped toolbar overlap in the old fixed-height header. Moving the content tools to a dedicated compact row resolved the overlap in the confirmation screenshot; all three panes remained side by side.

[Fixture evidence](browser-evidence.json) contains the final saved material and splitting session. Native Windows interaction and user acceptance remain unverified. Markdown represents logical document formatting; exact PDF typography and merged table geometry remain in the original and saved pre-edit cell.

## Normal service activation

The normal service had no active requests and automation was disabled. Five SQLite stores were copied before the protected stop/restart. [Prepared record](activation-prepared.json) was written before stopping. [Activation record](activation.json) confirms a new service instance and unchanged logical rows in all five stores immediately after restart. Automation remained disabled. Later browser access can create ordinary session metadata.

The normal page reopened successfully in a browser. [Served asset checks](served-assets.json) verified the Markdown module, stylesheet, local dependency bundle and Materials module byte-for-byte against current files. All decomposition and material-editing writes in this task used isolated fixtures. No real material was confirmed or archived, and no Git commit, push or PR was created.

## Operational boundaries

- Body filtering applies to new candidates. An older extraction/candidate must go through Re-extract and the existing comparison/adoption path to receive the new body selection; existing human edits and immutable candidates are not silently rewritten.
- Unclear frontmatter is retained for human review. Cover selection requires an identified TOC and explicit short cover metadata, and protects recognizable foreword/introduction sections and normative text.
- Markdown revision data belongs to existing material blocks and their history/snapshot path. The separate manual Requirement splitting tables still have their previously documented local-only collaboration ZIP boundary.
- Browser libraries are bundled locally with pinned package/lock files and licenses. No hosted editor, external model or CDN was activated.
