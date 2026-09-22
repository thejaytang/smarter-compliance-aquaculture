# Round 3 implementation evidence

Date: 2026-09-22. Scope: the ten approved Original reader items. Implementation and scoped coordinator acceptance are complete. The live service has not been restarted for R3. No business data, source bytes, saved annotations or Requirement/SCD decisions were edited. No real model, live-service restart, Git commit or publication was performed by the implementer.

| Item | Implemented behavior | Automated evidence |
|---|---|---|
| R3-01 | Registered HTML resolves only a Source ID through System1, then calls the pure System2 `material_source-html` command. It reuses the full `_html` sanitizer with `_bytes` hash validation before creating any MaterialService. The reader creates no store or adjacent disk cache. The sandboxed, no-referrer iframe requests the same registered preview route with `view=html` and the exact hash. Its response uses the same strict independent CSP as Materials HTML, so trusted reading styles work under the real outer CSP. | `test_runtime.py`: HTTP identity/hash/HTML-CSP checks. `test_material_reader_navigation.py`: hostile full document, untouched bytes, no service/cache/runtime, changed hash, actual owning-adapter subprocess. `evidence-reader.test.mjs`: source/hash-bound frame, missing hash refusal. |
| R3-02 | Previous/Next spreadsheet controls disable moves that repeat the current start or exceed sheet bounds. Navigation keeps source/sheet and the existing 40-row/12-column step. | `evidence-reader.test.mjs`: first/middle/last/short windows and zero requests from disabled buttons. |
| R3-03 | Material horizontal column navigation retains `r.row` and the returned column-window width. | `reader-display.test.mjs`: row 121, column 25, moves to column 1/49 at row 121. |
| R3-04 | Explicit Page/Row/Column jumps require integers in the actual document range, show adjacent linked errors and focus the field. Invalid input leaves the visible location and requests unchanged. | PDF recovery and Material reader behavior tests cover blank, zero, negative, fractional, above-max and valid 1/max. |
| R3-05 | PDF Previous match and Shift+Enter use `findPrevious:true`; Enter/Find remains forward. Composition Enter is ignored; match controls remain disabled until ready/nonempty. | `pdf-reader-recovery.test.mjs`: dispatch direction, composition suppression, unavailable/empty state. |
| R3-06 | Empty PDF query dispatches the existing PDF.js `findbarclose`, clears match text, disables match-only controls and ignores late empty-query counters. | `pdf-reader-recovery.test.mjs`: successful query, clear, late feedback and explicit replacement search. |
| R3-07 | Page rendering, text and annotation errors are independent in the existing pageStates map. Each success clears only its own layer/page error. | PDF recovery test: render/text/annotation failure sequence and unrelated page success. |
| R3-08 | Failed bound images show a local alert, disable Enlarge and offer exact-binding retry. Cached failed region response is removed only on explicit retry. Independent sanitized HTML stays visible. Existing request identity rejects old image events. | `evidence-reader.test.mjs`: failed image, independent markup, same document/unit retry, loaded replacement, stale image callbacks. |
| R3-09 | Fit-width/fit-page resize preserves current page and refreshes the existing URL/parent notification without refetching the PDF. | PDF recovery fixture deliberately resets page on scale changes; repeated resize stays on page 3 and fetches once. |
| R3-10 | Embedded PDF reading notifications carry zoom/rotation. Parent links accept only the same origin/frame/material/view, valid page, known zoom list and 0/90/180/270. | PDF recovery + Material parent-message tests, including malformed display settings and foreign frames. |

## Checks

- R2-09 follow-up: two remaining collaboration Archive labels now say `Content finalized`; toolbar/dialog behavior regression added. This remains R2-09, not a new R3 point.
- Full frontend: **416/416 passed**, [log](frontend-after.log).
- System2 original-reader tests: **51/51 passed**, [log](system2-reader.log).
- Runtime and Material HTTP tests: **27/27 passed**, [log](http-reader.log).
- Scoped `git diff --check`: passed. The unrelated authored example retains preexisting source whitespace; it was not normalized.
- Native IME behavior is covered by simulated event regression, not claimed as a native-input manual test.

## Browser fixture

The fixture serves only synthetic HTML, a generated four-page PDF, local spreadsheet arrays and declared frontend assets. Registered HTML uses the actual HTTP handler and full sanitizer; PDF uses actual shipped PDF.js and its production CSP. The outer fixture now uses the same default CSP as the live Workbench. All API writes are either rejected/recorded or explicitly change only a temporary synthetic HTML fixture. No requests proxy to business APIs.

From the repository root, the coordinator can run:

```sh
PYTHONPATH=workbench:workbench/backend/application:workbench/backend/system2/src workbench/backend/system2/.venv/bin/python project-support/validation/ui-round3-20260922/fixture_server.py --port 62845
```

Open `http://127.0.0.1:62845/`. The service is coordinator-owned; changing its Python routing requires its explicit restart. The startup command accepts a different port or omission for automatic allocation.

Suggested direct checks:

1. Registered HTML: headings, list, table and readable form text; no executable form/script/external resource. Verify independent iframe CSP and table borders under the strict outer policy. Change synthetic HTML, reopen and observe the exact-hash rejection; restore and reopen.
2. Shared worksheet: initial Previous buttons disabled; valid Next changes by 40/12; last window blocks Next. Log preserves the Unicode worksheet name.
3. Broken region: independent HTML remains readable, Enlarge disabled, Retry reuses the exact unit and can succeed; switching readers suppresses old image feedback.
4. Material worksheet: starts at row 121, column 25; horizontal movement retains row. Tools contains row/column jumps; invalid jumps show field errors with no reader log entry.
5. Embedded PDF: search `Facility`, use Previous/Next/Shift+Enter, clear query and inspect actual highlights; go to page 3 and resize; rotate/zoom, then Tools → Open reader preserves settings.
6. PDF page and Material page-image controls: invalid page remains visible with a range error and no original reload. Use valid first/last boundaries.

The coordinator must separately decide whether direct read-only PE002 Source/live-original checks are complete. These implementation logs do not assert live source-fidelity acceptance or Windows results.

## Coordinator acceptance

All ten items passed their applicable checks. Chrome on macOS directly verified the registered HTML webpage under the real strict outer CSP (visible headings/list/table borders), exact-hash rejection, spreadsheet first/last boundaries, Unicode worksheet identity and row 121 retained across column navigation. Invalid row 0 and PDF page 5 left the existing location intact and focused a range error. Failed image enlargement was disabled and retry preserved the exact document/unit request while independent markup remained readable.

Real bundled PDF.js found 32 `Facility` matches; Previous/Next moved 17→16→17, with page 3→2→3. Native keyboard deletion cleared the counter and disabled both match buttons. Viewport narrowing/restoration retained page 3. Zoom 150% and rotation 90° propagated into Open reader; the expanded reader opened page 3 with the current settings. Per-layer failure recovery (R3-07), native IME event semantics and malformed-message guards are automated regressions, not claims of manual Windows verification.

A separately restored PE002-only workspace on port 62846 ran the actual application with workers disabled. Its Source register showed only PE002 and the complete preserved Norwegian law as a sandboxed HTML webpage, including metadata, definitions, all sections and Annex 1. The original hash remained exact and all four restored business databases were byte-identical before/after viewing. See [acceptance details](browser-acceptance.json). The user's live databases and annotations were not used for these preview writes or altered. This is a rendering/identity check, not a new legal review.

## Broader backend checkpoint

The full System1 suite passed **169 tests**. Full System2 initially failed because one sibling fixture import used the old standalone module path and thirteen authority tests still mocked the former subprocess.run transport. The fixtures now import their sibling package and mock the existing ComponentPool request boundary, preserving all source-selection, malformed-receipt and handoff-race assertions. No product behavior or acceptance threshold was changed to make these tests pass.

Final offline System2 run: **1171 passed, 2 skipped**. The skips are the Windows-native process-counter test on macOS and an optional user-supplied `_PS3_副本.pdf` absent from the project root. See `system1-full.log` and `system2-full.log`. These are local results, not native Windows or real-model acceptance.

The full Workbench suite also passed **341 tests** in 33.57 seconds; see [log](workbench-full.log).
