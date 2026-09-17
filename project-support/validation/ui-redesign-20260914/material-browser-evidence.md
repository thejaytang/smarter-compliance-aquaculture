# Material workspace browser evidence

Date: 2026-09-14 (Europe/Oslo). Scope: isolated candidate at `http://127.0.0.1:60515/`, Chrome extension browser, agent-created tab `354552459`, reviewer Weijie Tang. These results verify the named engineering fixture flow and local layout. They are not production content acceptance, a measurement of extraction quality, Windows acceptance, or proof of a connected Requirement processor.

## Implemented and exercised behavior

- Material review and Archive use a full-width table entry and the same full-space, three-pane detail workspace. Collaboration is an on-demand dialog called through `materials.openCollaboration()`; no permanent collaboration toolbar or focus/expanded mode remains.
- Original navigation and content search/tools occupy their corresponding pane headers. Save and the current completion action remain in the material record bar. Secondary version, source, provenance, table-range and editing controls remain reachable through disclosures.
- TS001 `ENGINEERING FIXTURE · HTML water checks`: extracted and saved personal revision 4 with eight blocks, master revision 0. The original reader visibly reports the fixture's deliberately missing image. No master adoption or content confirmation was made for TS001.
- TS002 `ENGINEERING FIXTURE · Excel measurements`: original reader showed Measurements (105 rows × 26 columns), stored merged A1:C2 relationships, Temperature=12, C3 formula `=B3+1` with an explicitly unavailable saved cache, far cell Z105, Empty sheet and Hidden notes. The latter two original sheets were opened and visibly empty. Extracted five content blocks and saved personal revision 4.
- TS002 Archive action opened the existing prepare-own comparison, with five additions and zero unresolved differences. The displayed master remained revision 0. The explicit adoption dialog disclosed **0 source review changes** and required its combined-source-and-content confirmation checkbox.
- Explicit adoption produced saved master revision 1. A separate Archive finalized content dialog required checks for all three worksheets, omissions, hierarchy/associations/dependencies, and explicit completeness confirmation. The dialog stated **Content finalized · Requirements unfinished** and bound the exact saved master revision.
- After that engineering-only confirmation, Archive displayed TS002, source version TS002-001, finalized revision 2, operator Weijie Tang and recorded timestamp `2026-09-13T22:46:09.092255+00:00`. Its detail was read-only and offered Create revision. Requirements remained visibly Not connected.
- Created an engineering spot-check from the archived detail, assigned to Weijie Tang for Worksheet Measurements. The task opened in Material review in the same three-pane workspace, with Save progress and Complete review. After recording the engineering note and explicit scope confirmation, Complete review resulted in **Spot-check · passed**, check history 1, bound to archived revision 2. The accepted archive remained available.
- After candidate restart loaded the task filter, Periodic review returned zero rows because the TS002 check had passed. Content review returned only TS001. Its personal modifications were labelled **Personal changes await adoption**, not conflict.
- Opening TS001 from Content review and returning to Material list retained that filter and the one-row result. Scrolling its middle pane changed content scrollTop from 0 to 262.5 while original and Requirements remained 0.
- The coordinator's empty-selection Collaboration state was corrected to show package/inbox tools without claiming a material personal draft or exposing Review my changes.

## Layout observations

Measurements were read from the live DOM after browser viewport overrides, with screenshots inspected in the tool output. The global bar was 44 CSS px and the material bar about 46.7 CSS px. All three panes shared y=90.6953 and extended to the bottom of each viewport. No body horizontal overflow was measured.

| Viewport | Pane height | Pane widths, rounded | Result |
|---|---:|---|---|
| 1280 × 720 | 629.3 | 455.8 / 519.6 / 290.6 | Three parallel panes, headers visible, body width 1280 |
| 1440 × 900 | 809.3 | 513 / 585 / 327 | Three parallel panes, body width 1440 |
| 1920 × 1080 | 989.3 | 686 / 782 / 437 | Three parallel panes, body width 1920 |
| 720 × 450, narrow viewport supplement | 359.3 | 348 / 396 / 222 | Three panes remain flex and parallel; workspace scrollWidth 980, body width 720 |

The narrow viewport is **not** recorded as a real 200% browser zoom test. The third pane remains in the same horizontal workspace, reachable by horizontal scrolling; it does not become tabs or a stacked pane.

At 1280 × 720, the original-pane separator's ArrowRight action changed its width from 435.84 to 455.84 CSS px. Reload restored 455.84 and reopened the TS002 Archive revision 2. The middle content body measured clientHeight 593 and scrollHeight 1006 with overflow auto; the original spreadsheet window measured clientHeight 436 and scrollHeight 2943 with overflow auto.

All temporary viewport overrides were reset. The subsequent default viewport was 1470 × 779.

## Remaining acceptance boundary

True 200% browser zoom is **BLOCKED / not verified**: obtaining native Chrome returned that the Mac was locked and automatic unlock failed. The tab-level `super+plus` approach was not counted, because another agent measured no change in viewport or device pixel ratio. A user unlock and native Chrome zoom-menu test are still required. Windows acceptance remains separate.

No PDF reader failure was observed in this material browser pass, because its original-reader exercises used the named HTML and Excel fixtures. The parent restored the candidate's missing local PDF vendor assets and owns the full PDF-route verification; this note does not claim a new PDF browser pass.

## Tests and final corrections

- Final complete frontend suite: `node --test workbench/tests/*.test.mjs`, **186 passed, 0 failed**. Log: [material-node-final.log](material-node-final.log).
- Latest focused material/inspection/redesign run: **74 passed, 0 failed**.
- Material queue Python suite during implementation: **15 passed**, including task filtering before pagination and rejection of a fabricated conflict filter. Parent owns final complete Python-suite status.
- Added five material-redesign behavior tests covering temporary-list draft retention, save-before-prepare ordering, failed-save stop, reviewer scope and independent master confirmation.
- Final small corrections distinguish inspection views as Finalized revision / Spot-check status, replace the old Pending materials label in the spot-check creation dialog, and retain the inspection task/current-master choice when restoring a module. Restoring a saved master view also preserves that view rather than silently reopening a personal draft.
- Impeccable's missing-src warning at materials.js around line 445 is a construction-time false positive: previewImage first checks that the reader returned an image, then constructs the image and synchronously assigns its source in the same execution block. No persistently blank visible image was established by that detector warning.

All browser writes above were limited to the new engineering fixture. The public PA001 and CS010 copies received no engineering content confirmations. Normal service and normal business data were not modified by this subagent.
