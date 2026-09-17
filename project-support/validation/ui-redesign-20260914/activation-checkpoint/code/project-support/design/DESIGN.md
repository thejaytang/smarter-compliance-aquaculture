# Workbench design contract

This is the single visual agreement for the active workbench, reorganizing the existing light shell under the [2026-09-14 redesign goal](workbench-ui-redesign-goal-20260914.md) for the user's material-processing task. It applies UI UX Pro Max accessibility/layout guidance and Impeccable Operate guidance. Product truth is in [PRODUCT.md](PRODUCT.md); acceptance status is in [PROJECT_STATE.md](../../PROJECT_STATE.md).

The skill's generic marketplace, marketing typography and remote-font suggestions do not fit this task. The user already specified the audience, task, aesthetic and permission for reversible decisions. Preserve that direction and the working three-pane structure.

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

- The persistent material title/version and Save action lead the work area. Candidate processing, personal draft state and master confirmation must remain separately worded.
- One 44px-class global row contains workspace/module navigation, collaboration and operator menus. One compact record task bar contains identity, save status and final decisions. Package exchange, version/history and maintenance are named on-demand actions; no extra permanent collaboration row.
- Full-width source/material lists are replaced by their full-space detail when opened. Back/switch preserves query and location; no permanent global rail or library beside material panes.
- The desktop task frame owns viewport height. Original and content scroll independently inside opaque surfaces; toolbar growth must not make Save disappear above a long page.
- All three material panes remain side by side at every viewport/zoom level. Use operator-adjustable widths, keyboard resizing and accessible horizontal overflow where needed; never pane tabs or an expanded mode that hides core actions.
- The normal 100% desktop shell targets at most 120-140px combined global/task/pane-header height. Evidence text stays readable. Archive reuses the same three-pane frame in read-only mode and labels the confirmed content-only scope explicitly.
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
