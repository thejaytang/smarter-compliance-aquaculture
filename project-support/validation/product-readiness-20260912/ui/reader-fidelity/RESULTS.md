# Original-reader correction: bounded browser evidence

2026-09-13. **The observed PDF sizing, zoom-resolution and retry defects are corrected in code and verified in an isolated browser. HTML remains a reflowed reading view, not a reproduction of the source website.** This checkpoint does not close whole-product UI, extraction-quality or workflow acceptance. [Final code and screenshot binding](final-binding.json) identifies the exact artifacts.

## Cause and change

The old PDF view stretched a fixed-resolution bitmap on zoom. Its original-pane header inherited a large global margin, while verbose notices and a wrapped toolbar consumed the reading area and created nested scrolling. Reader `/9` and the current frontend give the page the remaining pane height, move secondary explanation into Reading details, and request more physical pixels on zoom or resize. The old image remains until its replacement is decoded and checked. Requests are guarded against stale material/page/view responses; failures retain the current page and expose Retry. Rendering is capped at 4096 pixels per side and 12 million pixels, with a visible limit message. This is still a rendered-page view, not a complete native PDF reader with vector/text-layer interaction.

HTML is sanitized and reflowed. The saved PA001 file refers to 14 external stylesheets and one unavailable image; those resources are absent from the local snapshot. Its original styling cannot be reconstructed from the saved markup alone. Reading details now explains this directly. Unsupported visual regions have source-anchored placeholders instead of silently disappearing; scripts, external assets and active embedded content remain disabled. No source bytes are changed and no remote assets are fetched.

## Actual browser comparison

CS010 original SHA256: `ce5c8950c69e3b5b60b85110f5abd2c6d8637c83291c6c00ac03f28b102dac54`. Both matched captures show page 1, personal saved revision 0, Not extracted, fit width, 1280 × 720 CSS viewport and DPR 2.

| Measured property | Before | After |
| --- | ---: | ---: |
| Toolbar height | 172 px | 108 px |
| Reader height | 113.61 px | 268.20 px |
| Outer reader scroll height | 420 px | 268 px |
| Page image top in viewport | 710.39 px | 446.80 px |

[Before screenshot](cs010-1280-before.png), [after screenshot](cs010-1280-after.png), [before geometry](cs010-1280-before.json), [after geometry](cs010-1280-after.json). The fit-width bitmap remains 893 pixels wide because it is already sufficient for that narrow displayed width; unnecessary re-rendering is avoided.

Additional actual checks:

- CS010 controls and page remain usable at [1440 × 900](cs010-1440-after.png) and [1920 × 1000](cs010-1920-after.png), with corresponding DOM geometry JSON files. The latter screenshot raster is 1912 × 1000 despite a verified 1920 CSS viewport. Two earlier attempts changed the selected tab rather than the inspected tab; they are retained as `viewport-attempt-*-actual1280.png` and are excluded from width acceptance. Browser screenshot bytes are JPEG despite the retained `.png` filenames; the binding records actual format and raster size.
- At 200% page zoom, the CS010 image increased from 893 × 1263 to 2897 × 4096 pixels. A 1588 CSS-pixel page at DPR 2 would need 3176 pixels horizontally, so the resource cap prevents full requested detail. The visible message says “Available page detail reached. Use Open original for finer inspection.” See [resolution observation](cs010-200-resolution.json). This is page zoom, not an operating-system/browser zoom acceptance claim.
- Page 1 to page 2 navigation retained the correct page identity. Stopping the owned fault service during a page-2 detail request retained the complete old page and exposed Retry. Restarting the same isolated origin and clicking Retry loaded the higher-resolution page 2. See [failure](resolution-failure-retained.json) and [retry](resolution-retry-success.json).
- Expanded workspace and two keyboard separator adjustments retained page 1 and visible resizer focus; reader height was 646 pixels. See [expanded view](expanded-keyboard-resize.png). Expanded mode and column overrides were reset afterward.
- Actual PA001 opening displayed the reflowed-view label and the 14-stylesheet/one-image explanation in [Reading details](pa001-html-details.png), with [captured text](pa001-html-details.txt) and an [after-only reading screenshot](pa001-html-after.png). This is not a matched HTML fidelity comparison or proof that all HTML visual content is supported.

These reading checks did not extract, edit, save or confirm CS010/PA001 content.

## Tests and preservation

Reader `/9`: **32/32** combined resolution, reader-parser, navigation and HTML-display tests passed with zero failures/skips ([JUnit](reader9-junit.xml)). The preceding `/8` protocol change separately passed 41 System2 checks and 11 actual HTTP forwarding/validation tests; see [protocol evidence](../../quality/reader-resolution/RESULTS.md). Those earlier results retain their original code binding.

The updated frontend passed **171/171** checks ([output](reader-correction/all-frontend-tests.txt)). The subsequent single CSS spacing adjustment passed the 12 reader checks ([output](reader-correction/toolbar-spacing/tests.txt)) and the browser confirmation above; JavaScript did not change in that final adjustment. These results do not replace the pending full integrated candidate regression and mixed workload.

Before the owned restart, five SQLite backups passed integrity checks in [the restart manifest](../../workflow/pre-reader9-fault-restart/manifest.json). After the browser work, [preservation verification](preservation.json) found all 17 prior rows across 16 checked material/history tables retained exactly, plus all seven original hashes unchanged. Newly opened PA001 is additional isolated data. This is scoped fixture preservation, not a new full backup of the normal business workspace.

## Loading, recovery and remaining work

- Latest reader/server/frontend were loaded and exercised at `http://127.0.0.1:60905/`, the owned fault fixture. Its current owned execution session is 6250. Resume this exact fixture with the existing Workbench environment and `project-support/product-readiness-20260912/serve_isolated.py faults`; do not rebuild its data.
- Coordinator 55542 and reviewer 58814 were subsequently restarted with reader support during the [returned-conflict checkpoint](../../workflow/return-conflict/RESULTS.md). Normal 62742 was not restarted or migrated; no latest-backend normal loading claim is made.
- Pre-change frontend copies are under [reader correction](reader-correction/pre-change/sha256.json); the last CSS delta has its own [pre-change binding](reader-correction/toolbar-spacing/pre-change/sha256.json). The pre-HTML `/8` reader is retained as [exact code](material-reader-before-html-display.py). Recover only the intended code delta against these hashes and restart an owned isolated process; never restore test stores over business data.

Remaining: native-reader interaction parity, all-state browser zoom/reduced-preference/accessibility checks, broader HTML visual fidelity, and final integrated workflow/quality gates. The parser quality FAIL and separate Requirement-identification UNMEASURED status are unaffected by clearer source rendering. The active goal continues via the [execution entry](../../execution.md).

## Follow-up on the reported overall rendering difference

The user clarified that the entire rendering differs substantially from directly opening a PDF. A fresh CS010 browser check confirmed the primary reader is still a page image. The optional browser PDF viewer, hidden in Reading details, displayed a dark empty region in this in-app browser: [screenshot](native-viewer-current.jpg), [visible UI](native-viewer-current.txt). Its availability is therefore not accepted. Reloading the isolated page cleared a stale state-fetch message; this observation does not establish the original network cause. No content extraction, edit or confirmation was performed. Resolution and layout fixes alone do not satisfy native-like reading; source-faithful display and usable direct reading remain open acceptance items.
