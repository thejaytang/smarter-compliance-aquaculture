# R10 implementation and isolated validation

All ten approved items are implemented; independent code review and root browser acceptance are separate gates.

| Item | Product implementation | Behavioral evidence |
| --- | --- | --- |
| R10-01 | Materials shortcut routes to the focused Requirement, Interpretation or Material/inspection save owner; uppercase S works, composing/default-handled/dialog events are ignored. | One owner per activation, no fallback from unavailable Requirement save. |
| R10-02 | Recorded source/content navigation reveals only the destination pane, scrolls it into the workspace and focuses its target. Missing locations retain the existing warning. | Collapsed original/content with unrelated collapsed Requirement, invalid page does not reveal. |
| R10-03 | Keyboard separator collapse focuses the new visible rail. | Home, End and threshold arrow, immediate Enter restoration. |
| R10-04 | Existing Material/content/reader Tools close on Escape, outside pointer, links and completed actions; validation retains their editable context. | Escape focus, outside dismissal and invalid reader control retention. |
| R10-05 | History/page/version/restore requests capture material, actor, view, token and dialog identity. Paging failures retain the current page. Restore rechecks the clean draft and clears historical declarations. | Late A history after B, closed/navigated/edited restore, same-material local restore without save, failed paging and retry. |
| R10-06 | Current text / Changes tracks the visible stable block and its relative position across redraw. | Same passage retained after earlier content grows; draft and dirty state unchanged. |
| R10-07 | Worksheet has one roving cell entry; arrows traverse loaded addresses, only its Formula summary joins Tab order, nested controls keep native activation. | 400 cells, exact A1→A2, native Formula Enter, same entry after redraw. |
| R10-08 | Explicit card approval/candidate approval/dismissal focuses the existing status in that same card. | Scope, Condition candidate, Demand dismissal preserve separate card semantics and do not save. |
| R10-09 | Valid original selections remeasure their toolbar on viewport/scroll changes, clamp to viewport and hide when out of view/invalid. Escape focuses the source; rebinding/reset/leave cleans listeners. | Resize, out-of-view scroll, no source mutations, Escape cleanup. |
| R10-10 | Region inputs retain raw typing; only valid coordinates update the preview. Invalid Use focuses its field without writing a draft; valid Use updates the local region. | Empty value, partial decimal, reversed edge correction, exact decimal coordinates and last-valid preview. |

Existing related suites: **94/94**. Complete frontend suite: **527/527**. Fifteen new regressions are in existing suites; no dependency or test framework was added. Logs `targeted.log` and `frontend.log`. Round-only diff `/tmp/ui-r10-net.diff`; before snapshots `/tmp/ui-r10-baseline`.

## Reproduction

Root owns persistent services and browser operation. Run:

`PYTHONPATH=workbench:workbench/backend/application workbench/.venv/bin/python project-support/validation/ui-round10-20260922/fixture_server.py --port 62855`

Open `http://127.0.0.1:62855/`. This reuses the real four-pane Materials shell, editor, Requirements and Interpretation components. The synthetic sources and actual System3 saves use a disposable SQLite store. Original PDF/worksheet reads, Material history and Material saves are explicitly page-memory simulations, with visible request logs. No business original, real provider or background scheduler is accessible. The fixture's controls offer a long document, passage-25 navigation, a 400-cell worksheet, region input, B/C candidates and deferred history.

Health checked HTML/CSS/served ES module/SVG responses and module syntax. Actual Interpretation save returned revision 2. A real Requirement Main Verb assignment saved and fresh-read at revision 3, exact value `inspect`; source evidence remained unchanged. Empty-step and missing-Origin health attempts were correctly rejected and did not save. All implementer health processes exited. Root browser verification must establish real focus, native keys, scroll and layout behavior. Native 200% remains a separate pending check until the Mac is unlocked.
