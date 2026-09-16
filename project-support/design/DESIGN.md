# Workbench design contract

This is the single visual agreement for the active workbench, reorganizing the existing light shell under the [2026-09-14 redesign goal](workbench-ui-redesign-goal-20260914.md) for the user's material-processing task. It applies UI UX Pro Max accessibility/layout guidance and Impeccable Operate guidance. Product truth is in [PRODUCT.md](PRODUCT.md); acceptance status is in [PROJECT_STATE.md](../../PROJECT_STATE.md).

The skill's generic marketplace, marketing typography and remote-font suggestions do not fit this task. The user already specified the audience, task, aesthetic and permission for reversible decisions. Preserve that direction. The 2026-09-16 approved extension uses four resizable, independently scrolling panes, with collapse/restore rails and horizontal scrolling at narrow widths.

## Runtime tokens

Definitions live in [style.css](../../workbench/ui/style.css); component styles consume them.

| Token | Value | Role |
| --- | --- | --- |
| `--accent` | `#185abc` | Primary action, current selection and focus |
| `--accent-hover` | `#124a9c` | Primary hover |
| `--on-accent` | `#fff` | Primary button text |
| `--ink` | `#202c3a` | Primary text |
| `--muted` | `#47586b` | Supporting text; never reduced opacity |
| `--line` | `#cad4df` | Surface separators |
| `--surface` | `#fff` | Original, content, editor and table base |
| `--surface-subtle` | `#f3f6fa` | Grouping and secondary tools |
| `--selection` | `#e4eefc` | Current material background, with text/outline state |
| `--glass` | `rgba(247,251,255,.82)` | Navigation and task controls only |
| `--glass-solid` | `#f4f7fb` | Solid transparency fallback |
| `--radius-control` | `8px` | Controls |
| `--radius-panel` | `14px` | Work surfaces and dialogs |
| `--space-1/2/3/4` | `4/8/12/16px` | Component spacing rhythm |
| `--motion-fast` | `160ms` | Short state feedback; no entrance choreography |

## Task hierarchy

- The HTML original-pane header keeps its title on the left and chapter chooser on the right. Chapter selection navigates immediately; omit Go and the former reader Tools menu.

- The persistent material title/version and Save action lead the work area. Candidate processing, personal draft state and master confirmation must remain separately worded.
- Page-switching subpages expand under their parent in the left sidebar, with a persistent selected background, marker and accessible current-page state. Search, filter, sort and refresh controls remain in the content area. The collapsed rail retains child icons and tooltips within the active group.
- A left sidebar (208px expanded, 56px collapsed) contains workspace/module navigation. The top Smarter Compliance mark toggles it without remounting the current task; collapse preference persists locally. Collaboration and the reviewer icon sit at the bottom, with the reviewer menu opening beside the rail. This 2026-09-14 user revision supersedes the earlier horizontal global row. One compact record task bar contains identity, save status and final decisions. Package exchange, version/history and maintenance are named on-demand actions; no extra permanent collaboration row.
- Full-width source/material lists are replaced by their full-space detail when opened. Back/switch preserves query and location; no permanent global rail or library beside material panes.
- The desktop task frame owns viewport height. Original and content scroll independently inside opaque surfaces; toolbar growth must not make Save disappear above a long page.
- Material content uses one continuously editable document, including cross-paragraph selection. Passage-edge controls offer To requirement and insertion above/below; they remain outside copied text. New candidates contain body content and headings, with excluded navigation/TOC evidence retained separately. Current text and Changes remain distinct reading modes, with red deletions and green additions. Manual requirement splitting is connected in the third pane; automatic requirement extraction remains unavailable. [Markdown contract](../../workbench/docs/markdown-content.md).
- Put the human responsibility declarations at the end of the content. Require complete-original/omission and hierarchy/dependency checks before Archive, and invalidate them when content or issues change. Save remains a personal draft operation, independent of those checks. Preserve exact-revision confirmation, coordinator adoption and source/conflict protections.
- All four material panes remain side by side at every viewport/zoom level. Use operator-adjustable widths, keyboard resizing and accessible horizontal overflow where needed; never pane tabs or an expanded mode that hides core actions.
- The normal 100% desktop shell targets at most 120-140px combined global/task/pane-header height. Evidence text stays readable. Archive reuses the same four-pane frame in read-only mode and labels the confirmed content-only scope explicitly.
- HTML Location shows a semantic outline and initially navigates to recognizable document content. Complete original start and all exact source anchors remain accessible; no content is deleted to simplify navigation.
- PDF and HTML original panes give their remaining height to one reading viewport. Compact page/location controls stay adjacent to the original; warnings, native-text assistance and alternative viewing belong in Reading details. Global header margins must not consume the reader's height.
- Where supported by the loaded parent, PDF uses the locally bundled source-document reader with continuous pages and original-position text selection. Search, zoom and the full-reader link are reading actions only. The Page image fallback and full-reader link must retain the current source and page; unsupported or textless pages cannot masquerade as completed extraction.
- PDF zoom requests actual image detail for the displayed width and device pixel ratio, within explicit resource limits. Preserve the displayed page while updating, keep page/source identity and scroll position, and provide Retry/Open original after failure. CSS enlargement alone is not a resolution improvement.
- HTML must identify the current offline reflowed reading mode. Missing styles/images and unsupported visual regions remain visible limitations; do not imply faithful website layout when the saved assets cannot support it. No remote asset fetching is introduced by reading.

## Typography and states

Use the local system sans family. Source-content text and editing use 14px with 1.65 line height; supporting task text uses 12px where practical. Main headings use 22px, material titles 18px and pane headings 14px. Avoid display typography and decorative icons. Use one simple SVG stroke family for authored shell controls.

Opaque white content, dark text and an explicit selected state take precedence over transparency. Focus uses a visible 3px accent outline, including summaries, selects and separators. Errors retain input and name the recovery action. Empty/partial/failed/unsupported states must not imply success. Reduced-motion and reduced-transparency media preferences preserve the same usable task structure. The current implementation declares light color scheme; no new dark theme is introduced.

## Verification boundary

Matched actual-browser captures and behavior checks are recorded under [the execution entry](../product-readiness-20260912/execution.md). A token choice or screenshot alone does not establish accessible behavior, parsing quality or colleague acceptance. Complete one concentrated visual pass, a material correction batch and one confirmation; then prioritize behavior and quality evidence.

## Requirement colours and interpretation

The [four-pane contract](../../workbench/docs/requirement-interpretation.md) owns this extension. Shared field colours live in `four-pane.css`, not per-Requirement random assignments. Neutral Scope/Condition/Demand groups do not imply a grammatical mapping. Current text, Changes and Requirement annotations are mutually exclusive reading modes. API configuration belongs to global Settings, with explicit per-generation context disclosure.

## 2026-09-16 workflow simplification

Interpretation values lead the fourth pane. Selecting Rx synchronizes its Scope, Conditions, Demands and three editable Logic fields. With no selection, show collapsed Rx summaries. Evidence, raw source structure and optional Site Model mappings use progressive disclosure. The third-pane Rx header contains Locate / Auto-extract / Remove; its remaining area toggles the entry, independently of coloured source selection. A source trail identifies the saved interpretation, Requirement, splitting revision, source paragraph and quotation anchors. Pin Save within the pane and scope Ctrl/Cmd+S to its editor. Preserve open disclosures and reading position through local redraws. Advanced rule comparison trees remain optional.

## Four-pane alignment

- Use one 12px content gutter per pane and a 40px header. PDF page controls may wrap when required. Keep action labels on one line; wrap source wording within its card.
- Pane minimum widths are 260 / 340 / 320 / 320px, with 44px collapsed rails and 7px visible separators. The workspace minimum follows the actual visible panes. Horizontal overflow belongs to the workspace, not the page or each card.
- Anonymous root wrappers add no border or indentation. Actual Groups retain their semantic colour, border and progressive inset. Place field IDs at the top of multiline text. Keep each module's 28px remove control inside its upper-right corner.
- Align link selectors and Link buttons at 32px. Quantity controls stay in one compact 28px row; that row can scroll locally when needed. The MIN–MAX option remains required before editing bounds.
- To requirement occupies a dedicated 108px passage action lane, with a 12px outer inset. Table edge controls use the same 28px height as their placement offset. Insertion menus align with the writing surface.
- Fourth-pane arrows, Rx labels and source previews share fixed alignment columns. Long source wording remains complete in a keyboard-focusable scrolling area; Logic remains editable below it. Use 8px action gaps and a Save row anchored at the pane bottom.
- Narrow screens retain the four-pane workflow while the material task bar wraps so Save and Close stay available. Dialog padding is 24px on desktop and 16px on narrow screens.

[Browser measurements, interaction checks and limits](../workbench-ui-alignment-20260916/RESULTS.md) record this pass.

## Working continuity

Source status distinguishes specified, explicitly absent and unresolved information; an absence explanation appears only when needed. Unsaved content remains in page memory and participates in leave warnings. Only explicit Save creates revision history; layout preferences may persist separately. Recovery and source-impact lists are on-demand actions. Optional mapping selects readable labels from a configured, empty-by-default catalog; raw SQL and query execution remain outside this UI.

## Source Group relationships

The third-pane selection toolbar places Relationship beside Group. It is enabled only for a source-bound inner Group. Display the exact connector in a compact neutral-colour row between its source-ordered children, with a separate top-right removal action. Preserve the connector highlight in collapsed original text. Do not count the connector, duplicate AND/OR as metadata, expose implicit one-child wrapper boxes, or turn this field into a compliance operator.


## Third-pane interaction language, 2026-09-17

Use one action vocabulary and position in saved and unfinished entries: header disclosure for viewing; a single top source surface for marking; Split on field cards; quantity and Group selected above siblings; link selectors for other Rx entries; × on the owning card. The source toolbar names the destination with Add to and restricts same-field nesting. Nested Group link options use a compact reveal; existing links stay visible. Avoid duplicated source editors and Resume editing gates.

One bottom action bar owns Save, Save & close and confirmed Discard. Save & close validates and commits atomically; a rejected or uncertain save retains the draft. Show errors at that action bar. Pure disclosure never commits a pending numeric draft. [Canonical action table](../../workbench/docs/manual-requirement-splitting.md#interaction-language-current-2026-09-17).
