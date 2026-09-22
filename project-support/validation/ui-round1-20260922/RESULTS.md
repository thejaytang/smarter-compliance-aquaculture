# Source workspace UI round 1

2026-09-22. Round 1's ten improvements passed implementation, local behavioral checks and coordinator browser acceptance. The ten-round goal remains in progress.

Changed only `workbench/frontend/components/source-workspace.js`, its existing stylesheet, `workbench/tests/source-ui.test.mjs`, and the focused `source-feedback.test.mjs`. No business database, API payload contract, initial data, Example inclusion policy, fourth-pane UI, dependency, Git commit or remote action was changed by this round.

## Checks

- Before: 387 frontend tests passed (`frontend-before.log`).
- After: 395 frontend tests passed (`frontend-after.log`).
- Source tests: 24 passed (`source-tests.log`), including eight new behavioral checks for failure/retry, state binding, focus, empty results and validation.
- Changed-file whitespace check passed.

## Item evidence and browser acceptance

| Item | Implementation evidence | Local check | Direct browser check still required |
| --- | --- | --- | --- |
| R1-01 | `renderList()` distinguishes filtered empty results; `clear-filters` restores search/decision/type but preserves sort. | Populated queue with unmatched query, clear, truly empty queue. | Search an unmatched string, read the message, Clear filters, check focus on Search. |
| R1-02 | `refresh()` exposes a dedicated list status, `aria-busy`, deduplicated read and Retry while retaining the old table. | Deferred/rejected read, one request for duplicate calls, exact old table/filter retained, successful retry clears state. | First load and Refresh with a delayed/failing disposable read; observe status and retry. |
| R1-03 | `openRecord()` stages its read, retaining old record/request until successful latest-token completion. Existing detail is inert while pending; failure retains it and offers retry. | A to B failure preserves A identity and draft; retry opens B; out-of-order A/B reads cannot overwrite B. | Observe old title during a delayed read, failure feedback and successful retry using a disposable fixture. |
| R1-04 | `renderList()` restores focus only for a previously active check-type/sort select. | Filter selection/focus retained; no focus stealing from another active element. | Operate the two review filters with keyboard and then Tab onward. |
| R1-05 | Source titles provide focus targets; Previous/Next restores the requested action when enabled; Back resolves the row using stable source identity. | Detail action focus, latest-selection heading focus and stable-ID Back with list scroll preserved. | List to detail to Next to Back, followed by history to detail to Back. |
| R1-06 | Taskbar identity wraps; narrow toolbar puts the complete title on its own line, with actions still reachable. | Source text unchanged; CSS checked. | Read a long Norwegian title at standard width and 200% zoom; inspect overlap/scroll. |
| R1-07 | H/M/L retain their request values while exposing High/Medium/Low accessible names, a visible abbreviation key and unabbreviated prior rating. | Read-only authoritative values remain HIGH and full accessible labels/prior High render. | Inspect names and select a rating with arrow keys in a disposable review. |
| R1-08 | Empty Evidence note gets a linked inline status, invalid state, scroll and focus; nonempty input clears it. | Empty note sends zero requests; a later valid preview sends the exact note. | Empty Confirm review targets the field; typing clears error; do not Apply live business work. |
| R1-09 | Problem dialog explains 4000-character limit; invalid values get field-linked errors without changing text or closing. | Blank/4001-character values append no issues; a valid report appends one unsaved issue only. | Use a disposable proposal for empty/long/valid reports and check retained text. |
| R1-10 | Shared native dialog is labelled by its actual `h2`; on close it locates the surviving/recreated original trigger using ID or command plus item identifiers. | Heading association and recreated trigger restoration. | Open Report/confirmation dialogs; Close and Escape restore the trigger and focus remains inside while open. |

## Coordinator browser acceptance

All R1-01–R1-10 core outcomes passed in Chrome on macOS using `fixture.html`, the actual SourceWorkspace and CSS, and a page-local API stub. The live PE002 Source register also showed the full title, focus target and full accessible rating names. No live source review was saved or applied.

- A filtered no-match result returned to two sources through Clear filters and focused Search. An empty pending fixture said no sources need review.
- A three-second list read exposed busy/loading; its injected failure retained two rows, and Retry cleared the error. A delayed failed FX001→FX002 detail read retained FX001; Retry displayed FX002 and focused its title.
- Changing focused check-type/sort controls retained their new values and focus after redraw; Tab continued to the first result. Back returned to the FX002 row rather than its old numeric position.
- Native Chrome's toolbar explicitly reported 200%. The viewport changed from 1144×776 to 572×388 CSS pixels; the complete long title wrapped within the 544-pixel toolbar text area and actions stayed reachable without overlap. Zoom was restored to 100%.
- The Authority radio exposed High/Medium/Low; ArrowRight changed HIGH to MEDIUM. Empty Confirm review focused the invalid note and sent zero writes; entering a note cleared its error.
- Empty and 4001-character reports stayed in the correctly named native dialog with an actionable error; all 4001 characters remained. A valid report appeared only in the unsaved proposal. Closing after the resulting redraw and using Escape returned focus to Report a problem. Synthetic Save was used only to clear the fixture's leave guard.

Native Windows and spoken screen-reader output are not covered by this macOS browser check. Failure cases ran only against the isolated fixture, not live business endpoints.

## Disposable browser fixture

`fixture.html` imports the actual `SourceWorkspace` and shipped styles. It starts with two synthetic read-only source records; **Allow local draft editing** exposes synthetic review fields and problem reports. Visible controls fail/delay the next list or detail read; **Empty review queue** exercises the genuine empty pending state. All API calls are handled by an in-page stub, with no business API proxy. Local write attempts are listed in the visible event log; local Save only changes this page's synthetic data. Reloading the browser resets that synthetic data. The ordinary source-draft browser journal may retain synthetic notes under the fixture origin only.

From the repository root, start any unused loopback port, for example:

```sh
workbench/.venv/bin/python -m http.server 62844 --bind 127.0.0.1 --directory .
```

Open `http://127.0.0.1:62844/project-support/validation/ui-round1-20260922/fixture.html` in the coordinator-controlled browser. Stop the temporary server after acceptance. The fixture's script passed `node --check`; it has not yet been opened by the implementation agent.
