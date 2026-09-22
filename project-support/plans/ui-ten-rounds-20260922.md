# Ten rounds of UI and interaction improvements

Updated 2026-09-22. Status: rounds 1–4 each have ten coordinator-verified improvements (40/100). Their frontend totals are 395, 405, 416 and 426 respectively; round 3 also passed 51 reader and 27 HTTP checks, and round 4 passed 35 owning MaterialService/Store checks. Round 2 composition behavior was checked through event-sequence and remount regression tests; a native input-method session was not manually tested. Rounds 5–7 each have ten implemented improvements and passed functional browser checks plus isolated owner-service save/reopen; native 200% zoom remains pending. Round 5 passed 442 frontend and 20 + 17 owning backend tests. Round 8 has ten implemented improvements, independently reviewed after one continuation-state correction; all ten functional browser checks and the 572 px layout passed, with native 200% zoom pending. Round 9 has ten implemented improvements and completed independent review after catalog validation-recovery corrections; runtime functional browser checks passed, and settings browser acceptance plus native 200% zoom remain pending. Round 10 is approved; no partial round is counted as verified.

## 1. Outcome and working rules

Deliver ten rounds, each containing exactly ten distinct, user-visible improvements with a reproducible acceptance check. One planning agent proposes the next round; one implementation agent makes the agreed changes. The coordinating agent owns final acceptance, the duplicate-Example correction, native Windows verification and product/development branch data boundaries.

The current fourth-pane contract is fixed: A, B and C show Combined extract and Set, with linked concepts in double quotation marks; one set relation follows. Keep Save, one AI Gen action and individual approvals. Retain evidence and editing through existing disclosure rather than adding permanent panels or controls. Source wording, IDs, saved histories and review gates must remain intact.

Do not count an existing feature, test-only change, unrelated cleanup or repeated version of the same fix as an improvement. The remaining rounds are directions until inspected against the latest code and observed UI. Before implementing a round, replace its direction with ten grounded items; adjust or replace disproven proposals before counting. A completed round requires its ten changes, relevant checks and direct UI evidence. A native Windows result must be obtained on Windows, separately from macOS or simulated tests.

This plan does not authorize model calls, live business-data changes, commits, pushes or publication. Those actions remain with the coordinator under the user's applicable authorization. The UI implementation must not alter Example inclusion or seed/import policy.

## 2. Round themes

| Round | Focus | Current status | Boundary |
| --- | --- | --- | --- |
| 1 | Source review navigation, readable identity and actionable feedback | Ten implemented and verified | Frontend Source workspace only |
| 2 | Materials library: finding, opening and returning to documents | Ten implemented and verified | No changes to Example selection or business inclusion |
| 3 | Original readers: location, loading, failure and keyboard use | Ten implemented and verified | Preserve original bytes and existing sanitized HTML/PDF protections |
| 4 | Extracted content: editing continuity and source-linked correction | Ten implemented and verified | Preserve block IDs, exact text, source spans and explicit Save |
| 5 | Requirements: annotation, nested Groups and selection continuity | Ten implemented; coordinator verification pending | Preserve grouping, quantities, relationships and Requirement identity |
| 6 | A/B/C: compact reading, concept clarity and editor continuity | Ten implemented and independently reviewed; native 200% zoom pending | Preserve the user's minimal fourth-pane contract |
| 7 | Saving, conflict handling, Collaboration and error recovery | Ten implemented and independently reviewed; native 200% zoom pending | Explicit generation/adoption/approval/save remain separate; local mock only |
| 8 | Reading and comparison: remaining source-grounded navigation/layout gaps | Ten implemented and independently reviewed; native 200% zoom pending | Preserve source structure, safe previews, version checks and explicit adoption |
| 9 | Settings, runtime status and recovery from interrupted operations | Ten implemented and independently reviewed; settings browser acceptance and native 200% zoom pending | Do not enable schedules, change accounts or configure live providers |
| 10 | Cross-workflow keyboard, zoom, narrow-window and return journeys | Approved; implementation follows round 9 | Preserve save ownership, exact navigation and the compact A/B/C interface |

## 3. Round 1: Source review navigation and feedback (verified)

Evidence inspected: `workbench/frontend/components/source-workspace.js`, `workbench/frontend/assets/source-workspace.css`, existing source UI tests and root guides. The problems below describe the inspected baseline; implementation and coordinator browser acceptance are recorded in the linked round evidence. Unless stated otherwise, implementation belongs in the current SourceWorkspace class and existing CSS, with existing Node tests extended only where they catch the relevant failure.

### R1-01 Distinguish no search matches from an empty review queue

- Trigger: enter a query or check-type filter that matches no source while the pending queue contains other sources.
- Current problem: `renderList()` always renders `No sources need review.` for an empty pending result. A filtered view incorrectly reports that the entire review queue is clear.
- Target: distinguish filtered zero results from a genuinely empty queue. In the filtered state, offer one Clear filters action that resets the active search, decision and check-type filters, then returns focus to the search field. Keep sorting and the actual source-selection policy unchanged.
- Files: `source-workspace.js` (`renderList`, `command`), `workbench/tests/source-ui.test.mjs`.
- Verification: a populated pending fixture with no query matches shows `No matching sources.` and Clear filters; clearing restores the original rows without writes; a genuinely empty fixture still says no sources need review.

### R1-02 Make source-list reads visible and recoverable

- Trigger: first open a Source list, or select Refresh while the list request is slow or fails.
- Current problem: `refresh()` only awaits the API and renders its result. The first list area is blank during the request; refresh has no local pending state; failure is only handled by the generic command error message.
- Target: show a concise loading/status line, set list `aria-busy`, and prevent duplicate list refreshes. Preserve an existing list on failure and present Retry in the same status area. Retrying only rereads the list.
- Files: `source-workspace.js` (`shell`, `refresh`, `command`), source UI tests.
- Verification: deferred request shows loading; a rejected refresh preserves existing rows and filters; Retry success clears the failure and busy state; repeated activation starts one request.

### R1-03 Keep source-detail selection honest during load failures

- Trigger: open a source from the list or move to the next source while the detail endpoint is slow or fails.
- Current problem: `openRecord()` changes `record`, clears `detail` and resets draft flags before its detail request returns, without showing a pending state. A failed request can leave the visible previous detail paired with a different internal record.
- Target: display which source is opening and mark the relevant host busy. Commit the selected record and its detail only after a matching successful response. On failure, retain the previously visible source and its identity and offer a read-only retry for the requested source. Preserve the existing unsaved-work guard and latest-request token.
- Files: `source-workspace.js` (`openRecord`, `showDetail`), source UI tests.
- Verification: slow/open-failed A→B leaves A's displayed record and request bound to A; successful retry opens B; A/B out-of-order responses never replace the latest chosen source; no Save or mutation call occurs.

### R1-04 Keep keyboard focus in rebuilt review filters

- Trigger: change Filter review type or Sort review tasks with the keyboard.
- Current problem: both change handlers call `renderList()`, replacing the table that contains the focused select. Focus is lost when its DOM node is removed.
- Target: preserve and restore the same filter's focus after the local list redraw; retain its selected value. Do not move focus for background refreshes or when the user is elsewhere.
- Files: `source-workspace.js` (`renderList`).
- Verification: select a check type and sort order using the keyboard; focus remains on the changed select, and the next Tab follows the normal order. Background list redraw must not steal focus from a separate control.

### R1-05 Preserve the source navigation focus path

- Trigger: keyboard-open a source, use Previous/Next, then Back to list/history.
- Current problem: `showDetail()` hides the focused list, and `backToList()` rebuilds and restores scroll without restoring the opened source's focus. Detail navigation replaces the focused button without a successor target.
- Target: on user-initiated open, move focus to the visible source title or detail entry point. After Previous/Next, keep the same navigation action focused if available, otherwise the source title. Back returns focus to that source's row button, or the list/search fallback if filtering removed it. Keep existing scroll restoration.
- Files: `source-workspace.js` (`openRecord`, `renderDetail`, `backToList`, `command`).
- Verification: complete list→detail→next→back by keyboard and verify each focused target; the returned row corresponds to the last opened stable source ID, not a stale numeric row position.

### R1-06 Make long source identities readable without hover

- Trigger: inspect a source with a long legal title in a narrow window or at 200% zoom.
- Current problem: `.source-taskbar>strong` forces a single ellipsized line; the only full-title presentation in the taskbar is a mouse-dependent `title` tooltip.
- Target: allow the source title to wrap within the taskbar without displacing essential Back/Save actions. Retain source ID, real title and existing compact hierarchy. Do not introduce another permanent information card.
- Files: `source-workspace.css` (`.source-taskbar` and title rules), markup only if a semantic title target is needed for R1-05.
- Verification: inspect a long Norwegian title at normal and 200% zoom; full title is readable, toolbar actions remain reachable, and neither title nor actions overlap the review panels.

### R1-07 Give source ratings their full names

- Trigger: inspect the H/M/L source ratings with assistive technology or without prior knowledge of the abbreviations.
- Current problem: radio labels expose only H, M and L; the previous rating is also abbreviated. The criterion legend names the dimension but does not expand the selected rating.
- Target: preserve compact H/M/L visual controls while providing full High/Medium/Low accessible names and a concise visible or native-tooltip explanation; show the previous value unambiguously. Do not change rating thresholds or program evidence.
- Files: `source-workspace.js` (`renderDetail` source rating markup); CSS only as needed.
- Verification: each radio has a distinct full accessible name within its criterion, keyboard arrow selection works, and the underlying `HIGH`/`MEDIUM`/`LOW` request values and previous ratings remain identical.

### R1-08 Point missing review evidence to the field that needs it

- Trigger: choose Confirm review with an empty Evidence and remaining work field.
- Current problem: `preview()` throws a generic error before opening the confirmation dialog. The command-level status displays it at the workspace top, leaving the relevant textarea offscreen and unfocused.
- Target: show a concise field-linked message, mark the empty note invalid, scroll/focus that note, and clear the invalid state when the reviewer supplies text. Do not send preview/apply requests while the note is empty.
- Files: `source-workspace.js` (`renderDetail`, form binding, `preview`).
- Verification: empty note produces no preview call and focuses `#sw-note`; nonempty input clears the error; the subsequent preview receives exactly the entered note and still requires separate confirmation.

### R1-09 Explain invalid problem reports without discarding input

- Trigger: choose Add to my source proposal with blank text or a report exceeding 4000 characters.
- Current problem: the `report-issue` handler silently returns for these values. The dialog provides neither the limit nor a reason why the button appeared ineffective.
- Target: state the 4000-character limit next to the field, show an inline validation message and focus the field on failure, and retain the exact typed report for correction. Only valid reports enter the unsaved proposal; no automatic Save or adoption.
- Files: `source-workspace.js` (`command` report-issue dialog).
- Verification: blank and over-limit reports remain visible in the open dialog with an actionable error and add no issue; a valid report appends one local issue and still requires explicit save/adoption.

### R1-10 Name Source dialogs and return users to the trigger

- Trigger: open any dialog through the shared `SourceWorkspace.dialog()` entry, then close it with Close or Escape.
- Current problem: the shared native dialog inserts an `h2` but does not associate it as the dialog's accessible name. Some triggers are recreated by a detail redraw, so browser-native restoration alone cannot reliably return focus.
- Target: associate the dialog with its existing heading; retain a stable trigger identity and restore focus on close when its visible replacement exists, using the current source title/list only as fallback. Preserve native focus containment and Escape behavior; do not add a modal framework.
- Files: `source-workspace.js` (`dialog`), source UI tests.
- Verification: a report/confirmation dialog exposes its actual title; Close and Escape return focus to the original visible trigger or stable fallback; a rerendered trigger is handled; typing inside a dialog does not move focus outside it.

## 4. Round 2: Material library journeys (verified)

Evidence inspected: `workbench/frontend/components/materials.js`, its existing tests and `workbench/backend/application/local_workbench/material_queue.py` read contract. The queue accepts only the existing first/review/inspection task filters; do not add a nonexistent conflict API filter. These proposals intentionally avoid repeating round 1's generic loading, dialog and focus fixes. Source queue membership and Example inclusion remain the coordinator's responsibility.

### R2-01 Show the current material result range

- Trigger: browse a library with more than 50 matching materials.
- Current problem: `renderList()` shows only the total and Previous 50/Next 50 buttons. The current range is not stated.
- Target: display `51–100 of 124 materials` (and the equivalent archive wording), with correct zero and last-page bounds. Give the paging group a concise accessible name. Keep the existing 50-row API limit.
- Files: `materials.js` (`renderList`), relevant material UI tests.
- Verification: 0, 1, 50, 51 and 124-result fixtures give correct first/last visible indices without implying a visible row for an empty result.

### R2-02 Restore the material page when returning to the module

- Trigger: browse the second or later page, leave Materials for another module, then return as the same reviewer.
- Current problem: `rememberView()` stores query, filter and scroll but not the list offset; `mount()` always requests offset zero. A stored scroll position can therefore reopen over different records.
- Target: persist the current accepted offset in the existing session context and use it when remounting. A new search/filter resets offset to zero. Review and Archive keep separate page contexts, as they already do for their queries.
- Files: `materials.js` (`mount`, `rememberView`, `loadList`).
- Verification: page 2→Sources→Materials reopens the same query/filter/offset; a new query starts at zero; switching reviewer never reuses another reviewer's page context.

### R2-03 Search only complete input-method text

- Trigger: type a Chinese or Japanese material query through an input method editor.
- Current problem: every `#mw-find` input event schedules a request, including intermediate composition text.
- Target: defer the existing debounce until composition ends. Preserve complete Unicode text without transliteration or truncation, and ignore Enter as a navigation command while composing.
- Files: `materials.js` (`shell` search bindings).
- Verification: a composition sequence issues no intermediate query; composition end issues one request with the final string; ordinary Latin typing remains debounced.

### R2-04 Keep pagination and the active query in one request context

- Trigger: type a new query while on a later page, then quickly choose Next/Previous or change Task type before the debounce runs.
- Current problem: paging uses the previous result's offset with the already changed `listQuery`; the pending timer can then issue another offset-zero read. The result can jump between unrelated slices.
- Target: cancel the pending search when applying a filter, and bind page navigation to the query/filter that produced the visible page. If that context changed, resolve the new context from offset zero before permitting later-page navigation. Reuse `listTicket` for stale-result rejection.
- Files: `materials.js` (`shell`, `loadList`, pagination actions).
- Verification: a second-page fixture plus typed query and immediate Next never requests offset 100 for the new query; only the latest query/filter result appears; no source-open or write request occurs.

### R2-05 Start reading a newly selected page at its beginning

- Trigger: scroll to the paging buttons at the end of a long list and choose the next page.
- Current problem: `loadList()` replaces rows without resetting `.mw-library.scrollTop`, leaving the new page at an old scroll position, potentially near its end.
- Target: on explicit page changes, scroll the results heading into view and provide a keyboard reading entry at that heading or first result. Keep the separate Back-to-list restoration behavior unchanged and do not scroll for background updates.
- Files: `materials.js` (`loadList`, pagination actions).
- Verification: Next/Previous from the bottom shows the start and correct range of the new page; closing a material still restores the earlier list position rather than resetting it.

### R2-06 Make the saved-source opener's prerequisite visible

- Trigger: expand Open a saved source version before selecting a source.
- Current problem: Open material is enabled despite the blank selection, and only clicking it produces the generic `Choose a registered source.` notification.
- Target: keep this specific opener disabled until a valid source is selected; add a concise field-linked prompt when no source is available. Maintain disabled state across `updateNavigationLock()` and after an open request ends. Other source-row open buttons keep their own bound IDs.
- Files: `materials.js` (`shell`, `updateNavigationLock`, open-source action).
- Verification: blank selection cannot initiate a request; valid selection enables the opener; busy→idle does not enable a blank opener or disable valid row buttons incorrectly.

### R2-07 Disambiguate registered sources with the same title

- Trigger: choose between source records that share a legal title but have different source IDs or versions.
- Current problem: the saved-source select shows only the title (or ID when title is absent), although its option value is the unique source ID.
- Target: label options with source ID plus title and available version. Do not invent version metadata when absent or change the option's identity/value.
- Files: `materials.js` (`shell` saved-source options).
- Verification: same-title fixtures remain visibly distinguishable, hostile or Unicode titles are escaped correctly, and selecting each option sends its original exact source ID.

### R2-08 Show extraction work that still needs attention in library rows

- Trigger: scan a material whose extraction is running, ready/partial awaiting adoption, or failed while saved content is retained.
- Current problem: `materialStatus()` provides these states in `processing`, but the library's Pending work cell does not use it; many rows fall back to a generic Content draft label.
- Target: display the meaningful current extraction state as part of Pending work, using the already-derived status text. Suppress routine `Saved content · no current extraction` noise. Preserve source qualification and human adoption/review distinctions.
- Files: `materials.js` (`renderList`, existing `materialStatus` helper).
- Verification: running, partial, ready, failed-with-saved-content and no-current-extraction fixtures show the relevant action state without calling a candidate adopted/reviewed or duplicating the content label.

### R2-09 Limit Archive labels to verified content status

- Trigger: inspect an archived material's row and header.
- Current problem: the UI hardcodes `Content finalized · Requirements unfinished` without inspecting any Requirement completion record.
- Target: state the verified content finalization only. If the payload does not report Requirement completion, do not assert either completion or incompleteness. Preserve exact finalized revision and author/time metadata.
- Files: `materials.js` (`renderList`, `updateBar`), `material-inspection.js` (`markup`, which repeats the same hardcoded heading).
- Verification: archived fixtures render their known content confirmation and exact revision, do not manufacture Requirement status, and remain read-only until the existing Create revision flow is explicitly used.

### R2-10 Distinguish multiple checks on the same material

- Trigger: a material has several open inspection tasks for the same reviewer and status, or checks bound to different archive revisions.
- Current problem: library links show only `Check · assignee · status`; two tasks can appear identical even though their `data-task` IDs differ. The task payload already includes `archive_revision` and creation `at` in `material_queue.py`.
- Target: include the bound archive revision and recorded creation date in each compact inspection link or its immediately associated text. Do not invent a cycle number: the current task data has no authoritative cycle field. Keep the exact task ID and current inspection-open action.
- Files: `materials.js` (`renderList` inspection links); `material-inspection.js` history links may reuse the same human-readable identity if needed.
- Verification: two same-reviewer/same-status tasks with different archive revisions or creation dates are distinguishable and open their exact original IDs. Missing or invalid timestamps say not recorded rather than displaying a fabricated date; existing source/inspection data stays unchanged.

## 5. Round 3: Original readers (verified)

The coordinator directly observed Sources showing PE002 as `Text preview of the local snapshot...`, despite Materials already providing an isolated HTML reading frame. That observation grounds R3-01. The other items are based on the current reader code and require fixture/browser verification before completion. Do not change source files, parse/adopt content, alter legal annotations or write business records as a side effect of viewing.

### R3-01 Read registered HTML sources as safe webpages

- Trigger: open a saved `.html` or `.htm` source in Source review/register.
- Current problem: `server.py`'s `/api/preview/<source>` route uses a TextOnly parser for HTML, and `showEvidence()` renders the returned text. Headings, paragraphs, tables and lists lose their webpage structure. The same saved file has a structured sanitized reader in Materials.
- Target: reuse the existing complete-document sanitization in `evidence/material_reader.py` through the owning System2 adapter and display its result in a sandboxed, no-referrer iframe. Preserve source-ID resolution and expected-hash checking; never send raw paths from the browser. Keep active original HTML download-only. The label must explain the actual sanitized/reflowed presentation, without claiming published website styling. Do not downgrade the sanitizer to the less restrictive region-only function.
- Files: `backend/application/local_workbench/server.py` (registered preview), the existing System2 reader service boundary if needed, `frontend/components/evidence-viewer.js`, and source reader CSS. Reuse current HTML safety tests.
- Verification: read-only PE002 Source register preview visibly preserves headings, lists and tables; a hostile HTML fixture executes no script, loads no external resources and submits no form; a changed original hash fails explicitly; opening the preview does not create or revise a Material or source record.

### R3-02 Respect spreadsheet navigation boundaries in shared evidence previews

- Trigger: use Previous rows/Previous columns on the first spreadsheet window, or Next on the last window, in a Source/shared evidence preview.
- Current problem: `showEvidence()` clamps previous positions to one but disables buttons only when the requested position exceeds the sheet's maximum. First-window Previous remains enabled and rereads the same cells.
- Target: derive button availability from the current window's start and the returned sheet bounds; disable no-op moves at both ends. Preserve existing row/column window sizes and retain the current sheet name.
- Files: `evidence-viewer.js` (spreadsheet controls).
- Verification: first, middle, short-sheet and last-window fixtures enable only moves that change the window; disabled controls issue no request; valid moves retain the exact source/sheet and never alter cells.

### R3-03 Keep the worksheet row when moving across columns

- Trigger: navigate to a later worksheet row in Materials, then choose Previous columns or Next columns.
- Current problem: `Materials.readerAction()` sends `row:1` for either horizontal move, abandoning the current row context.
- Target: preserve the current reader window's row while changing only its column. Do not alter explicit sheet changes or row navigation.
- Files: `materials.js` (`readerAction` horizontal spreadsheet actions).
- Verification: a reader at row 121, column 25 moves horizontally at row 121; the column advances by the returned window width; the selected sheet and original binding stay unchanged.

### R3-04 Explain invalid original-location jumps

- Trigger: submit an empty, decimal, negative or out-of-range Page/Row/Column value.
- Current problem: the embedded PDF reader silently restores invalid pages; Materials clamps some page values and defaults empty row/column values to one while other invalid values reach the server. The displayed location can change without explaining the correction.
- Target: validate explicit location entry before a read/navigation. Keep the current page/cells on invalid input, display the allowed integer range beside the control and focus the offending control. A valid value uses the existing read action. Keep server validation as a separate protection.
- Files: `pdf-reader.js` page change handler; `materials.js` `reader-page` and `reader-cells` actions; minimal existing status markup/CSS if needed.
- Verification: invalid cases send no read and do not move the reader; valid edge values 1 and the actual maximum work; original page/source IDs and saved work remain unchanged.

### R3-05 Find the previous PDF match

- Trigger: search a PDF and overshoot a result, then move back to the previous match.
- Current problem: `pdf-reader.js` always dispatches `findPrevious:false`, and the page offers only Next match.
- Target: add Previous match using the existing PDF.js find controller; support Shift+Enter from the search input for the same action. Keep Enter/Find as forward search, ignore composition Enter and disable match navigation until the document is ready.
- Files: `pdf-reader.js`, `pages/pdf-reader.html`, existing PDF reader controls CSS only if needed.
- Verification: known repeated text steps backward and forward through the existing match count; query text and page binding are preserved; no browser-wide Find or model call is triggered.

### R3-06 Clear stale PDF search feedback with the query

- Trigger: clear the PDF search field using its native clear control or by deleting its contents after a successful search.
- Current problem: no query input handler updates PDF.js, so old highlights and the old match counter remain until another Find action.
- Target: when the complete query becomes empty, dispatch the controller's existing clear-search behavior and clear the match counter; disable match-only actions for an empty query. Typing a replacement query need not auto-search.
- Files: `pdf-reader.js` search bindings.
- Verification: clearing a nonempty query removes all previous highlights and hit-count text; a subsequent explicit new search works; clearing does not navigate, reload or change a saved review.

### R3-07 Remove a stale PDF failure after its failed layer recovers

- Trigger: a PDF page rendering or text/annotation layer initially fails, then successfully renders again after a zoom or retry within the same viewer session.
- Current problem: event handlers assign `state.error` on failure but never remove that error on later success. `pageStatus()` can keep reporting a failed visible page after recovery.
- Target: track the affected render/text/annotation failure independently enough to clear only the recovered failure. A successful unrelated page or layer must not erase another unresolved error. Reuse the existing `pageStates` store; no new diagnostics panel.
- Files: `pdf-reader.js` page/layer event handlers and `pageStatus`.
- Verification: failed page 3→successful page 3 clears its rendering error; a remaining text-layer failure stays visible; success on page 2 does not clear page 3; the Retry action disappears only when the visible page has no outstanding failure.

### R3-08 Make a broken original-region image actionable

- Trigger: a bound original image/region result is returned, but the image cannot decode or load.
- Current problem: `showEvidence()` creates image and Enlarge controls without image error handling. A broken image leaves a normal-looking caption and an unusable Enlarge action.
- Target: show a concise bound-preview failure, disable enlargement of the broken image and offer explicit retry of the same evidence request. Retain independently available sanitized markup or text assistance, without treating it as proof that the image loaded. Guard delayed image events with the existing evidence request identity.
- Files: `evidence-viewer.js` image branch.
- Verification: a failed image triggers a visible alert and cannot open an empty enlarged dialog; retry keeps source/range arguments; an old image error after selecting another source does not overwrite the new preview; no extraction or adoption occurs.

### R3-09 Keep the current PDF page through pane resizing

- Trigger: read a later PDF page in Fit width/Fit page and resize the surrounding pane/window.
- Current problem: `ResizeObserver` directly reassigns `viewer.currentScaleValue`; unlike the explicit zoom/rotate handlers, it does not preserve the current page. Existing PDF test fixtures already demonstrate PDF.js scale changes can restore page one.
- Target: retain and restore the current page around responsive fit-scale updates, using the same established behavior as the explicit Zoom action. Do not re-fetch the original or write review state.
- Files: `pdf-reader.js` ResizeObserver callback; existing PDF reader recovery test fixture.
- Verification: resize while on page 3 keeps page 3, URL location and parent page notification consistent; repeated resize callbacks do not fetch or recreate the source document.

### R3-10 Carry reading settings into the expanded PDF reader

- Trigger: zoom or rotate an embedded PDF, then choose Open reader to inspect it in a larger window.
- Current problem: the iframe message and parent link carry only page; `Open reader` resets zoom and rotation even though `pdf-reader.js` already supports both as validated URL settings.
- Target: include validated zoom and rotation in the existing page notification and expanded-reader link. Keep origin, frame, material ID, view and page checks, and accept only known zoom values and 0/90/180/270 rotation. No document content or new persistent preference store is needed.
- Files: `pdf-reader.js` (`notify`, reading-position updates); `materials.js` PDF message handler and `.mw-open-pdf-reader` link.
- Verification: expanded reader opens the same page/zoom/rotation; foreign-frame or mismatched source/view messages remain ignored; malformed settings cannot enter the link; the original bytes and saved material/Requirement/interpretation data remain unchanged.

## 6. Round 4: Extracted content editing (verified)

Evidence inspected: `markdown-content.js`, `material-editing.js`, current material search/render bindings, existing Node tests and the continuous-document browser fixture. R4-09 and R4-10 also have direct pure-memory reproductions: changing an image caption changes type from image to text and removes its active image metadata; changing one table cell resets active merges and notes to empty. Original metadata remains in history, which does not replace the need to retain the correct current draft. All fixes below stay in the existing source-bound document editor; neither new editors nor autosave are requested.

### R4-01 Keep contextual passage controls stable while reading and typing

- Trigger: focus a passage action by keyboard, or move the pointer within the same active passage/cell.
- Current problem: every `showTools()` call replaces `controls.innerHTML`, including repeated pointer movement and keyup within the same block. Existing ResizeObserver logic already avoids that replacement, but normal pointer movement does not.
- Target: reuse controls when the active block/cell and action availability are unchanged; update position separately. Preserve a focused control and any active selection instead of destroying its DOM node.
- Files: `markdown-content.js` (`ContinuousDocument.showTools`, binding callbacks).
- Verification: repeatedly move within one passage while its insert button is focused; the same control remains focused and no selection moves. Moving to a genuinely different passage updates the action's bound block ID.

### R4-02 Keep exactly one insertion choice open

- Trigger: click Insert above/below repeatedly, or switch from above to below before choosing a type.
- Current problem: `ContinuousDocument.action('above'/'below')` appends a new `.md-insert-menu` each time. Several menus can remain visible while one latest `insertAt` value controls all of them.
- Target: replace or toggle the one current insertion chooser, retain the selected source-bound position and never display obsolete choices for a different position.
- Files: `markdown-content.js` (insertion actions and existing controls).
- Verification: repeated above/below activation leaves at most one chooser; selecting a type inserts exactly one block at the displayed position, with the correct neighboring source context; opening/canceling creates no block.

### R4-03 Dismiss insertion controls without losing the editing position

- Trigger: press Escape or choose Cancel while keyboard focus is inside the insertion chooser.
- Current problem: Escape is handled only on the contenteditable root, but the focused chooser is its sibling. Cancel redraws the controls and removes the focused button without restoring the caret or trigger.
- Target: handle Escape for the chooser itself, dismiss it, and restore the original insertion trigger or recorded caret in the associated passage. Preserve the selected text and avoid treating dismissal as a content edit.
- Files: `markdown-content.js` (`ContinuousDocument.bind`, cancel action, bookmark/restore reuse).
- Verification: Escape and Cancel both close the chooser from a type button and return to the original editing context; no draft fields, undo entry or saved revision changes.

### R4-04 Keep table editing near the changed cell

- Trigger: insert or delete a row/column partway through an extracted table.
- Current problem: after the structural action, `ContinuousDocument.action()` rerenders and restores `{id, offset:0}`, moving the caret to the start of the whole table block, often its caption.
- Target: restore focus/caret to the inserted cell or nearest surviving cell at the affected row/column. Preserve the current scroll region and allow the reviewer to continue editing that location.
- Files: `markdown-content.js` table actions and existing caret restoration.
- Verification: insert/delete in row 12 or a later column lands at the corresponding surviving/inserted cell; first/last row and column boundaries remain valid; source refs, retained original table and unrelated cell values are unchanged.

### R4-05 Paste rectangular spreadsheet cells into an extracted table

- Trigger: paste tab-separated rows copied from a spreadsheet into an existing table cell.
- Current problem: the document paste handler always inserts all clipboard plain text into one text node; tabs/newlines therefore remain within that one cell or are flattened during table serialization.
- Target: when the caret is inside a table and the plain text is a rectangular cell grid, place its cells from that position using the existing table representation. Preserve pasted cell text and make the whole paste one undo step. Bound the operation with the current 100,000-cell limit; invalid/oversized paste must preserve the draft and explain how to correct it. Ordinary prose paste retains its current behavior; no clipboard HTML or scripts enter the DOM.
- Files: `markdown-content.js` paste handler/table actions; reuse `material-editing.js` table helpers rather than a new grid dependency.
- Verification: a 2×3 TSV paste populates six cells from the selected origin, retains surrounding cells and source IDs, and undoes in one step; oversized input produces no partial table mutation; script-looking clipboard text stays literal.

### R4-06 Navigate table cells with Tab without editing them

- Trigger: press Tab or Shift+Tab while the caret is inside an extracted table cell.
- Current problem: the general document Tab handler moves focus into passage controls, even when the user is editing a table. There is no cell-to-cell keyboard path.
- Target: move to the adjacent existing cell in reading order within the table. At the first/last boundary, allow the normal accessible exit to/from the existing controls; never create an extra row merely by navigation. Preserve the text cursor and make passage tools reachable.
- Files: `markdown-content.js` (`ContinuousDocument.bind` keydown).
- Verification: Tab/Shift+Tab visit a 2×3 table predictably and exit at its boundaries; no text, dirty flag, undo history or saved data changes from navigation alone; keyboard access to insertion/deletion controls remains available.

### R4-07 Make Undo follow the last edit across Current text and Changes

- Trigger: edit in the continuous Current text mode, edit a block through Changes/Markdown, return to Current text and undo.
- Current problem: `ContinuousDocument.undo/redo` and `MarkdownNotebook.histories` are independent. Notebook block edits do not update or invalidate the continuous document stack, so returning to it can undo an older document snapshot instead of the most recent correction.
- Target: coordinate the existing history paths so Undo reverses the actual most recent draft edit and Redo restores it. Reuse the document's bounded page-memory snapshots rather than adding persistence. A mode switch itself is not an edit.
- Files: `markdown-content.js` (`ContinuousDocument.remember/travel`, `MarkdownNotebook.change/travel`, mode transition boundary if needed).
- Verification: Current edit A→Changes edit B→Current Undo restores A while retaining its source evidence; Redo restores B; switching modes alone adds no history; neither action creates a saved revision or resurrects another material's edits.

### R4-08 Continue lists without resetting their source start or nesting

- Trigger: press Enter inside an ordered or nested list, including a list whose starting number is not one.
- Current problem: `split()` extracts the tail into a new source block and serializes its cloned list wrapper. A partial ordered-list wrapper retains the original `start` value rather than the position of the selected item, so the remainder can be renumbered; nested list boundaries have no dedicated handling.
- Target: use ordinary ordered-list editing semantics within the existing block: preserve the list start, nesting and source wording. An explicitly inserted item may naturally renumber following implicit items, for example 5/6/7 new/8 former third. Never restart the extracted tail at the old start or invent duplicate numbers. The current Markdown parser does not retain later explicit `li value` values; if a structural edit cannot serialize them losslessly, reject that edit, retain the draft and explain the limitation. Do not change ordinary Markdown's valid repeated `1.` auto-numbering globally or claim complete source-numbering fidelity. Handle an empty final item as a deliberate exit from that list without deleting prior wording or reassigning source IDs. Keep Enter-in-heading and table-cell line-break behavior intact. This boundary was clarified by the coordinator on 2026-09-22.
- Files: `markdown-content.js` (`ContinuousDocument.split`, editable list serialization).
- Verification: Enter in the second item of an ordered list starting at 5 gives the ordinary 5/6/7 new/8 former third sequence without resetting the tail to 5; nested items retain nesting; empty-item exit preserves earlier items; exact undo restores original text, numbering and refs. Unsupported explicit-value structure is retained with an actionable refusal rather than silently renumbered. Existing repeated-`1.` Markdown continues to render normally. Canonical source content is unchanged.

### R4-09 Keep an image attached when correcting its caption

- Trigger: correct caption/attribution wording in an extracted image block using the continuous or Markdown editing path.
- Current problem: `updateMarkdownBlocks()` classifies the rendered image-caption block as ordinary text and executes `delete b.image`. A pure-memory reproduction changed type image→text and reported `attachmentRetained:false`, while keeping the original only in `markdown.original`.
- Target: a caption-only correction retains the image block type, attachment, image source reference and attribution fields unless the reviewer explicitly changes them. An intentional conversion/removal remains a distinct supported action, not an accidental consequence of typing.
- Files: `markdown-content.js` (`blockMarkdown`, `updateMarkdownBlocks`, image caption serialization as needed).
- Verification: change only caption text and confirm the current draft still contains the same attachment and source refs; undo restores the exact caption; saving/reopening in an isolated fixture retains both image and corrected caption. Canonical original bytes remain identical.

### R4-10 Retain table relationships when correcting cell text

- Trigger: correct one cell in a table containing merged-cell relationships, a caption or table notes.
- Current problem: `updateMarkdownBlocks()` reconstructs a recognized table as `{rows, merges:[], notes:[]}` on every edit. A pure-memory reproduction turned one existing merge into zero and erased the active notes after replacing one cell word.
- Target: preserve unchanged table merges, caption and notes on a cell-only correction. Explicit row/column operations must use the existing `tableAxis()` relationship adjustment or another already-supported structured path; unsupported complex layout changes must not silently flatten the active table. The reading/editing view must make retained relationships inspectable using existing table/source controls.
- Files: `markdown-content.js` table conversion/actions and `material-editing.js` existing table helper if needed.
- Verification: one-cell edit leaves merges, caption, notes and all other cells byte-equivalent; insert/delete adjusts only the affected merge geometry; undo restores the exact original table; isolated Save/reopen retains the intended structure. Retention only in history is not a pass.

## 7. Round 5: Requirement annotation and Groups (approved)

Evidence inspected: `requirements.js`, `requirement-structure.js`, their current frontend tests, `backend/system3/requirements.py`, `requirement_structure.py` and the read-only annotation projection in `interpretations.py`. Four small in-memory reproductions confirmed the state-loss/wrong-target issues below without an API call or business-data write. These are proposals, not completed UI checks. Preserve every source string, Unicode code-point offset, stable Requirement/Group/fragment ID and explicit human selection. Do not reannotate existing examples, infer missing fields, approve A/B/C, or alter the server's grouping/completion rules.

### R5-01 Keep an invalid typed quantity visible for correction

- Trigger: type a MIN–MAX bound larger than the Group's direct-child count, such as 99 for a two-item Group.
- Current problem: both `RequirementsEditor.bindQuantity()` and `StructureEditor.bindQC()` run `Math.min(count, Number(input.value))` on every input event. The bound silently becomes 2 and may then be applied on blur. The inspected legacy test explicitly expects that clamp; the coordinator has approved changing this behavior as part of round 5.
- Target: retain the human's typed numeric value and use the existing quantity validator to explain the valid range. Do not submit or replace it with a different quantity until the reviewer corrects the entry or explicitly chooses a preset. Keep nonnumeric input filtering and Escape restoration.
- Files: `requirements.js` (`bindQuantity`), `requirement-structure.js` (`bindQC`), affected behavior tests.
- Verification: entering 99 leaves 99 visible, marks the field invalid and causes no quantity preview/save request; entering 2 or choosing All clears the error and applies exactly that deliberate value. A ten-item Group still permits ordinary two-digit editing without an intermediate silent substitution.

### R5-02 Retain the chosen siblings while adjusting Group controls

- Trigger: check two direct children for Group selected, then switch the same Group to MIN–MAX or open its link options before grouping.
- Current problem: checked state exists only in the checkbox DOM. `range-mode`, `show-link` and other presentation redraws call `render(true)`, and `nodeMarkup()` recreates every checkbox unchecked. The proposed sibling set is lost without an actual grouping change.
- Target: preserve checked direct-child IDs through presentation redraws within the same session and owner Group. Recompute the existing Group selected count from those IDs. Clear invalid IDs after a successful structural operation and clear the selection on a genuine session/material change; never apply a grouping merely to retain selection.
- Files: `requirement-structure.js` (`nodeMarkup`, `bind`, presentation actions); `requirements.js` context reset boundary if needed.
- Verification: check siblings A and C, switch the quantity display, and confirm A/C and Group selected (2) remain selected; grouping sends exactly those stable IDs in their original source order. A different Group/session inherits no picks and no write occurs during disclosure changes.

### R5-03 Keep quantity drafts when a requested removal does not happen

- Trigger: edit a quantity inside Group A, leave another quantity invalid, then press Remove on A.
- Current problem: `StructureEditor.action()` immediately deletes all quantity drafts under A before committing unrelated quantity rows. If another row rejects its commit, removal returns early but A's draft has already disappeared. The in-memory reproduction left the child in the tree with `quantityDraftRetained:false`.
- Target: keep the target's quantity drafts until the removal preview succeeds. If validation, a definitive rejection or an uncertain request blocks removal, retain the appropriate draft and existing retry safeguards. After confirmed removal, discard only drafts belonging to removed nodes.
- Files: `requirement-structure.js` (`action` removal path and successful apply handling).
- Verification: an unrelated invalid quantity blocks removal and preserves A's exact typed bounds, current source markings and dirty state; a successful removal clears only A's removed descendants' draft entries. No saved revision or approval is created by an unsuccessful attempt.

### R5-04 Stop annotation navigation when the destination was not opened

- Trigger: activate a coloured annotation in the extracted-content pane while the current Requirement has unsaved edits, is pending, or cannot load the referenced session.
- Current problem: `navigateAnnotation()` awaits `open()` but unconditionally assigns the requested `unit_id` afterward. `open()` can return without navigating. A pure-memory reproduction retained document `old` while selecting `otherunit`, which did not exist in it.
- Target: proceed only after the intended session and unit have actually been accepted into the current context. Preserve the current selected unit, disclosures and fourth-pane association when the existing unsaved/pending guard blocks navigation or the read fails. Use the established guard; do not add another confirmation flow.
- Files: `requirements.js` (`navigateAnnotation`, `open` result contract if needed).
- Verification: dirty, pending, rejected and out-of-order destination fixtures leave the old document and its valid selected unit paired; a successful read moves to the requested existing unit. A blocked jump sends no annotation mutation or interpretation approval.

### R5-05 Reveal the exact nested annotation that was activated

- Trigger: activate an extracted-content annotation belonging to a field or relationship inside one or more collapsed Groups.
- Current problem: the annotation payload already contains `node_id` and, for a connector, `relationship:true`. `navigateAnnotation()` ignores these fields and searches only `[data-field]`, which current structure cards do not expose. It can end at an unfocusable parent card while the actual marked fragment remains collapsed.
- Target: resolve the supplied stable node ID in the current structure, expand only its ancestor path and focus/scroll to that fragment or the existing relationship row. Retain the legacy field/target fallback for earlier saved annotations. Missing/stale IDs must report that the saved mark cannot be located rather than guessing by repeated text.
- Files: `requirements.js` (`navigateAnnotation`), `requirement-structure.js` node/relationship identity and existing disclosure sets.
- Verification: two identical phrases in different nested Groups navigate to the supplied node, not the first matching text; a connector lands on its relationship row; unrelated Groups remain collapsed. No source span, Group quantity or review state changes.

### R5-06 Read the full Requirement wording before creating a link

- Trigger: select an Exception or Subrequirement whose identifying difference falls after the first 90 characters.
- Current problem: `StructureEditor.linkMarkup()` truncates every option to 90 characters and has no selected-target preview. The full linked source becomes available only after the reviewer has added the link, creating an avoidable wrong-reference risk.
- Target: within the existing link picker, show the full original wording for the currently selected target before Link is pressed, using a compact disclosure or associated reading region. Include its current display label while binding to the same stable target ID. Leave the default unselected picker compact.
- Files: `requirement-structure.js` (`linkMarkup`, picker change binding).
- Verification: same-prefix targets can be distinguished by their later original wording before linking; changing selection updates the preview, clearing it clears the preview, and Link sends the exact selected ID. Hostile markup remains literal text; no paraphrase, inference or preemptive link/save occurs.

### R5-07 Validate a combined source selection before closing its picker

- Trigger: clear all passages or select a combination beyond the existing server limits when creating a Requirement from multiple passages.
- Current problem: `start(..., true)` silently returns for zero picks and otherwise closes the dialog before the server validates the selection. The server already limits input to 100 distinct passages and 100,000 Unicode code points, including the two-newline separators. Rejection makes the reviewer rebuild the selected combination.
- Target: show the current selected passage/text size compactly in this existing dialog, enforce the same limits before requesting a preview, and keep the checked passages available for correction on a definitive failure. Retain exact source order and individual source links; preserve the established exact-request Retry handling for uncertain responses.
- Files: `requirements.js` (`start` combined-source dialog); existing `step` result handling only as needed, without changing the server contract.
- Verification: zero, 101 passages and 100,001-code-point combinations remain in the picker with their selection intact and send no start request; a valid combination sends only original block IDs in source order. Supplementary Unicode characters and separators are counted consistently with Python. No source text is shortened to fit.

### R5-08 Reuse the matching current Requirement independently of the open entry

- Trigger: select To requirement on a passage with an existing matching entry while another stale Requirement happens to be open, or when the matching entry itself has changed source bindings.
- Current problem: `start()` finds a candidate by block ID/text but tests `!this.doc?.stale`, the state of the currently open entry. An in-memory reproduction with an unrelated stale entry chose `start` instead of opening the matching current entry. Conversely, a matching stale entry may be reopened because an unrelated entry is current. List summaries do not contain authoritative `stale`, so simply checking `existing.stale` is insufficient.
- Target: verify the matched candidate through the existing read-only session endpoint and base reuse on that candidate's returned source status. Open the current matching session; if it is stale, start the explicitly requested new preview from the current saved passage while retaining the old history. Guard delayed reads by material/session context.
- Files: `requirements.js` (`start`, existing session read path). No server schema or duplicate-Example policy change.
- Verification: an unrelated stale open entry never causes a duplicate current-session start; a stale matching candidate is not treated as editable current work merely because its text is unchanged; source/ref changes are judged by the authoritative read. A failed candidate read neither creates a new entry nor replaces the current one.

### R5-09 Preserve selected wording after a definitive annotation rejection

- Trigger: select exact source wording, choose a field/relationship assignment, and receive a definitive validation rejection such as an overlapping or unsupported connector range.
- Current problem: `StructureEditor.action()` sets `this.selection=null` after `await this.apply(request)` regardless of its false result, while pending/error redraws destroy the browser range. The in-memory reproduction confirmed that a rejected annotation loses its selected range.
- Target: retain the exact session/unit/node/code-point range for correction when the same source remains current and the server definitively rejects the proposed action. Restore its visible selection and relevant assignment tools without applying anything. Invalidate it on source/context changes; uncertain transport failures continue to use Retry and must not allow a different concurrent action.
- Files: `requirement-structure.js` (`action`, selection capture/restore), `requirements.js` render boundary if needed.
- Verification: a definitive rejection leaves the exact Unicode range selected so the human can choose a corrected field/target; no structure edit is recorded until a subsequent successful preview. A changed source or switched session clears it, and uncertain retry state never re-enables editing.

### R5-10 Locate unfinished structure when Save & close is blocked

- Trigger: choose Save & close while a collapsed Group is empty, has an unresolved quantity, or has a relationship with only one marked side.
- Current problem: the server correctly rejects completion using `requirement_structure.pending()`, but the frontend presents only the generic failure in its save bar. The incomplete nested node remains collapsed and the reviewer must search the tree manually.
- Target: identify those same explicit structural incompleteness states in the current draft for navigation, expand the first affected path and point to the existing quantity/source marking control. Show the affected local Group/Requirement label in the current feedback area. Keep server validation authoritative and keep ordinary Save capable of retaining incomplete work; do not invent missing roles, quantities, operands or approval.
- Files: `requirements.js` (`saveDraft` completion feedback), `requirement-structure.js` existing tree traversal, relationship sides and disclosures.
- Verification: each supported incomplete state in a deeply nested fixture opens and focuses its correct repair location while preventing Save & close; an unrelated unmarked purpose/context paragraph is not treated as a mandatory requirement field. Ordinary Save still retains incomplete work, and a fully valid structure follows the existing explicit completion/save path without extra approval.

## 8. Round 6: Compact A/B/C and concept editing (approved)

The coordinator approved these ten items for sequential implementation after round 5, including one temporary Set-local removal undo and presentation-only handling of source absence. Evidence comes from `interpretations.js`, `check-design.js`, `four-pane.css`, existing frontend tests and the System3 check-design validator. Pure-memory reproductions confirmed shared-input disagreement, citation clearing, duplicate concept links, invalid range acceptance, absence-reason-as-predicate rendering and the closed newly created concept. No browser, provider, service or business-data write was used for this planning pass.

Keep the default fourth pane as the same three Combined extract/Set blocks, individual approvals and set relationship, with Save and one AI Gen. Improvements belong inside existing Set disclosures or their current feedback. Do not add a global toolbar, permanent history panel, model inference, automatic approval or another data store.

### R6-01 Retain the nested editing disclosures that the reviewer opened

- Trigger: open Review notes, a Concept, Link another concept or a saved Data comparison, then add/edit another rule or concept in that Set.
- Current problem: `InterpretationEditor.render()` remembers only `details[data-disclosure]` and concept details keyed by positional `data-rd-path`. Several nested disclosures have no saved identity, so redraw closes them; deleting an earlier rule also changes positional paths and can attach an open state to the wrong rule.
- Target: retain presentation state through same-Requirement redraws using the stable unit and rule/concept IDs already present in the model. Keep each new Requirement's default editor closed and do not transfer another Requirement's disclosures. Opening/closing details remains a read-only action.
- Files: `interpretations.js` (`render` disclosure capture/restore), `check-design.js` stable identities in the existing markup.
- Verification: adding a rule does not close the Review notes being used; deleting an earlier sibling preserves the surviving rule's own concept/comparison disclosure; a different Requirement does not inherit those open panels. No draft, source, approval or saved revision changes on disclosure alone.

### R6-02 Start editing the rule or concept that was just created

- Trigger: choose Define logic, Add rule, Add group or New concept within a long Set editor.
- Current problem: `bindDesign()` creates the model node and redraws without an editing destination. New concepts render in closed `details`, leaving the default `New concept` name hidden until found and opened manually. The pure-memory markup reproduction confirmed a new concept was closed.
- Target: after the explicit creation succeeds locally, reveal only the new item's existing ancestor path and focus its first meaningful input: rule wording, the new group's first rule or the new concept's Name. Reuse the generated stable ID to locate it and keep the user in the same A/B/C card. Do not prefill additional legal meaning.
- Files: `check-design.js` (`bindDesign`, creation actions), `interpretations.js` local post-render focus handoff if needed.
- Verification: creating a rule near the end of a nested Set focuses that rule, creating a concept opens/focuses its Name, and keyboard entry continues immediately. Existing node IDs, rule nesting and another card's disclosure remain unchanged; no save or approval occurs.

### R6-03 Keep all editors of a shared concept in agreement

- Trigger: the same concept ID is linked in more than one rule/card, and its Name or Type is changed through one occurrence.
- Current problem: the concept input handler updates the shared model, chips, type/status summary and confirmation checkbox, but not other Name/Type inputs. A reproduction changed the shared model to `Salmon facility` while the second input still displayed `Facility`, allowing a later edit to overwrite the new label with stale UI text.
- Target: synchronize other visible instances of that exact concept ID while preserving the active input's caret/composition. Keep distinct IDs independent even when their labels match. Continue the existing explicit meaning-confirmation invalidation when Name/Type changes.
- Files: `check-design.js` concept input binding.
- Verification: changing a shared concept's name/type updates every associated editor and quoted reading output; another concept with the same old name remains unchanged. The active edit does not lose characters/caret, and no new concept ID or automatic confirmation is created.

### R6-04 Add card citations without erasing a concept's existing evidence

- Trigger: choose Use card citations for a concept that already has a quotation from another card/source, including when this card has no citations.
- Current problem: `bindDesign()` assigns `c.references = fields[root].references`, replacing the entire evidence list. A pure-memory reproduction using an empty card changed a nonempty concept quotation list to `[]`.
- Target: merge exact `{id, quote}` pairs from this card into the concept's existing references, without duplicates or altering quotation text. With no new eligible citations, make the action a clear no-op/disabled state. Respect the existing 100-reference contract without silently truncating evidence. Explicit citation removal remains separate.
- Files: `check-design.js` (`conceptMarkup`, `cite-concept` action); reuse existing validation/message area.
- Verification: an old quotation survives adding a distinct card quotation, repeated activation produces one copy, and an empty card cannot erase evidence. If the combined list exceeds the established limit, preserve both current concept data and staged intent for correction; no save/approval is implied.

### R6-05 Make linking a concept idempotent within one rule

- Trigger: activate Link concept twice before an old control is discarded, or re-trigger a previously selected existing concept after a redraw.
- Current problem: the handler always appends the chosen ID to `n.concept_ids`. A pure-memory repeated activation produced `["c", "c"]`; the server correctly rejects duplicate concept IDs.
- Target: accept only a currently available concept that is not already linked to the target rule, and recompute the existing picker/action availability after linking. Repeating the same explicit association becomes a no-op rather than a corrupt draft. Keep reuse of the same concept across different rules/cards supported.
- Files: `check-design.js` (`conceptMarkup`, `link-concept` action and selection binding).
- Verification: rapid repeated activation produces one ID in the rule and a still-saveable draft; blank/unavailable selections produce no mutation; linking the same ID to a separate rule remains valid and retains the shared concept identity/evidence.

### R6-06 Preserve a quotation being prepared before Add citation

- Trigger: choose a saved context passage and type an exact quotation, then edit a concept or receive another same-Requirement redraw before pressing Add citation.
- Current problem: `fieldMarkup()` always renders a blank `[data-ip-quote]` textarea and resets the citation select to its first option. There is no input binding or page-memory state for these staging controls, so redraw silently discards the prepared quotation and source choice.
- Target: retain this unsubmitted form state on the existing draft object per reviewer/material/unit/field in page memory, with the existing leave protection when it contains work. Clear it after a successful explicit Add citation or deliberate clearing; never turn staged text into a citation automatically. After formal Save, explicitly state in the existing feedback that an unadded quotation remains unsaved; neither claim all work saved nor silently clear it.
- Files: `interpretations.js` (`fieldMarkup`, render bindings, `add-ref` and existing leave-state integration).
- Verification: an exact quotation and chosen citation survive unrelated redraws, a validation rejection and formal Save; Add citation inserts exactly the selected pair once and then clears its staging field. Changing reviewer/unit never exposes another context's staged quotation, and no browser storage or background write is added.

### R6-07 Present source absence as a state, not a fabricated Set predicate

- Trigger: a human-reviewed field has `state: not_stated`, an empty value and an absence explanation, with no explicit rule tree.
- Current problem: `setDefinitionMarkup()` falls back from an empty value to `absence_reason` inside the set-builder predicate. The reproduction rendered `B = { x ∈ A | No condition is explicitly stated. }`, making a statement about source coverage appear to be an object-membership rule.
- Target: render an explicit compact not-stated status for that Set and keep its actual absence explanation in the existing supporting/review area. Preserve the field state, empty value and evidence exactly. Do not infer `B = A`, an empty set, unconditional applicability or a new predicate.
- Files: `check-design.js` (`setDefinitionMarkup`), existing field/review markup if needed.
- Verification: not-stated fields are visibly distinguished from an unfilled definition and a specified predicate; their source-absence explanation is readable but not placed after the membership bar. Data, generation, approval eligibility and final set-relation contract remain unchanged.

### R6-08 Validate existing comparison ranges against their actual operator

- Trigger: edit an existing mapped rule to between/not between with three lines, reversed limits, or an unsupported boolean range; then perform another Set edit that redraws the form.
- Current problem: frontend `ruleValue()` accepts any newline-list length/order for range operators. In-memory calls accepted `[1, 2, 3]` and `[5, 1]`, although `backend/system3/check_design.py` requires exactly two ordered non-boolean endpoints. Other value errors use DOM-only custom validity, which can disappear when a redraw recreates the controls.
- Target: apply the existing server arity/type/order requirements locally, retain the exact invalid typed text for correction, and reconstruct its field-level invalid state after redraw. Present the operator's needed value shape inside the existing Data comparison disclosure. Keep server validation authoritative and do not change operators, reorder limits or replace values automatically.
- Files: `check-design.js` (`ruleValue`, `ruleMarkup`, comparison input binding and validation reconstruction).
- Verification: invalid shape/order/type remains visible and invalid across redraw without changing the human's text or issuing a save; two valid ordered endpoints pass as entered. Existing `in` lists retain their separate list semantics and no new mapping UI or consumer execution is introduced.

### R6-09 Inspect a quoted concept through its existing details

- Trigger: read a specially quoted term in the compact Set output and inspect what that concept means in this rule/context.
- Current problem: `setDefinitionMarkup()` emits a noninteractive span with only a mouse `title` containing kind/status. The reviewer must expand the whole Set and manually find the matching concept occurrence; if several linked IDs share one label, `.find()` silently presents the first one's kind/status.
- Target: make the existing quoted term a keyboard-accessible route to its associated rule's existing concept details, preserving the same quiet visual treatment. Use the actual linked IDs, not text search. If multiple linked concepts share the displayed label, reveal their existing matching details without arbitrarily claiming one identity or merging them. Do not add a global concept panel or edit the expression when navigating.
- Files: `check-design.js` (`setDefinitionMarkup`, concept identity markup), `interpretations.js` local navigation binding; minimal existing focus styling if needed.
- Verification: mouse/keyboard activation reveals the correct concept under the correct rule, including a shared concept and same-label/different-ID fixture; raw expression, concept IDs and quotes remain unchanged. The summary does not toggle twice, and navigation creates no dirty flag, source inference or approval.

### R6-10 Undo the most recent rule or Group removal locally

- Trigger: remove the wrong rule or nested Group while editing a Set, before any subsequent content/structure change.
- Current problem: `bindDesign()` immediately splices the rule tree and prunes unreferenced concepts. There is no local undo for that removal; reloading the saved interpretation would discard all other unsaved work as well.
- Target: offer one temporary Undo action in the affected Set's existing feedback area. Restore the exact removed tree, IDs, AND/OR/NOT combination, predicates, quantities if present and any pruned concept identities/evidence. Expire it on the next content/structure edit, save, source/context change or unit switch so it cannot overwrite newer work. Do not create a general history stack, global button, automatic save or automatic approval.
- Files: `check-design.js` (`remove`, concept pruning boundary), `interpretations.js` current draft feedback/change boundary.
- Verification: remove/undo of a nested OR/NOT fixture restores its exact structure and shared/unshared concept references while retaining other pre-existing draft edits. An intervening edit or context switch invalidates Undo; it never revives another Requirement's tree, changes a saved revision or restores a previous approval decision.

## 9. Round 7: Save, comparison and failure recovery (implemented; native 200% zoom pending)

The coordinator approved this round after reviewing the actual save/comparison paths. Current code evidence comes from `interpretations.js`, `collaboration.js`, `source-workspace.js`, `submission-drawer.js`, their existing tests and the owning System3/Collaboration API contracts. Seven failure scenarios were reproduced using in-memory stubs only: repeated old-revision saves, new generation IDs after an uncertain response, a stuck run state, blank-number-to-zero conversion, incoming-value reuse after an edit, closing an unapplied busy edit, and concurrent opposing task decisions. Implementation follows round 6, using disposable fixtures. Conflict comparison/rebase only changes the page draft, invalidates affected approvals and never automatically saves. Refresh must not discard an uncertain result or replace its exact request identity. Reuse existing pointer parsing and stable block IDs; missing combined values must fail, never fall back to incoming. Keep one compact feedback area. No provider call, live adoption, export or source rewrite is authorized by this plan.

### R7-01 Recover a newer Interpretation save conflict without looping

- Trigger: another reviewer/tab saves a newer interpretation before this draft is saved.
- Current problem: a definitive 409 sets `sourceChanged`; the visible recovery action is Refresh source. Its handler refreshes only context and leaves `d.revision` unchanged. A pure-memory reproduction saved with expected revisions `[1, 1]` before/after Refresh source, so the next Save encounters the same conflict. The existing reload action is not exposed as a conflict recovery choice in the compact UI.
- Target: provide one conflict-only comparison/recovery entry from the existing notice. Read the latest saved interpretation and show it beside the protected local ABC draft, including concepts/evidence when different. Let the human explicitly reload the saved version or continue a reviewed local result against the verified latest revision. Distinguish a saved-interpretation revision change from changed source context/catalog by inspecting the authoritative read; do not silently overwrite either version or preserve invalid approvals.
- Files: `interpretations.js` (`save` conflict handling, existing `open`/reload and dialog paths).
- Verification: simulated competing saves retain both versions for comparison; cancellation leaves the local draft intact; an explicit choice uses the latest expected revision and preserves the exact chosen wording/IDs. A further competing save is still rejected. Context refresh alone does not claim to resolve a newer Interpretation revision, and no comparison action automatically saves or approves.

### R7-02 Reconcile an uncertain AI Gen start with the same request identity

- Trigger: the generation endpoint starts a request, but the response is lost before the UI receives its run ID.
- Current problem: the failure handler closes the dialog, stores no pending generation request and re-enables AI Gen. A second click creates a fresh UUID. A mock failure/retry issued two different IDs, although the server already deduplicates generation by request ID and exact request digest.
- Target: retain the exact confirmed generation request in page memory when the outcome is uncertain and offer a retry/reconciliation action for that same request. A definitive rejection may clear it; changed source/fields must not silently reuse its ID for different content or start a second run while the first outcome is unresolved. Continue using one AI Gen entry and the current explicit context confirmation.
- Files: `interpretations.js` generation confirmation/failure state; reuse `/api/interpretations/generate` and its existing idempotency contract.
- Verification: a stub that records a run and then loses its first response sees the same ID and byte-equivalent request on retry, returns one run and performs no second generation. A definitive failure retains human fields and permits a deliberate new request. No paid/live model is called in tests.

### R7-03 Recover generation status without discarding an edited draft

- Trigger: polling a known running generation fails while the human continues editing the interpretation.
- Current problem: `watch()` reports that status is unavailable but leaves `d.generation` truthy. AI Gen stays disabled; reopening a dirty Requirement keeps the existing draft/generation object and does not restart that watcher. The pure-memory failure left `generationRetained:true` and the generation button disabled.
- Target: show an actionable status-unavailable state with one read-only Retry status control near the existing AI Gen feedback. Resume polling the same bound run, or present its terminal ready/failed/interrupted result. Keep the human's unsaved ABC fields and the current known generation request intact; do not generate a replacement as a status check.
- Files: `interpretations.js` (`watch`, `open` recovery and generation feedback).
- Verification: a failed run read followed by Retry status resumes the same run ID and clears the stalled control when terminal; typed human content and individual approval rules remain unchanged. A response for another unit/context never replaces the active card or starts an additional model call.

### R7-04 Keep a manual merge edit open until its exact preview is applied

- Trigger: open Edit result, type a correction, and submit while another merge operation is busy or after the comparison identity changed.
- Current problem: generic `editDifference()` has neither the merge-ID guard nor the pending checks already used by order/relationship editors. `resolve()` can return early while busy, yet the dialog then closes. An in-memory reproduction closed the dialog with zero requests. It can also send an old dialog's difference ID to a newly active merge.
- Target: bind the editor to its opening merge/difference identity, guard duplicate/in-flight submission and close only after that exact decision's preview is accepted. Keep typed corrections in the dialog with inline recovery feedback on a blocked or failed attempt. Reuse the established order/relationship editor pattern without changing merge semantics.
- Files: `collaboration.js` (`editDifference`, explicit success result from `resolve` if needed).
- Verification: busy, changed-merge and rejected-request cases preserve the open editor and exact typed value; a successful matching preview closes it once. No request reaches a different merge, and no master/personal adoption occurs from editing the preview.

### R7-05 Permit only one unresolved task-adoption decision at a time

- Trigger: click Keep current and then Adopt submitted result while the first task decision is still pending or its response is uncertain.
- Current problem: `SubmissionDrawer.compare()` disables only the clicked button and has separate request IDs per choice. A mock deferred endpoint received both `current` and `incoming` concurrently for the same comparison digest.
- Target: use one comparison-level pending decision, disable both competing actions while it is unresolved, and retain the exact chosen request for an uncertain retry. After an acknowledged terminal receipt, retire those stale decision controls. A definitive failure may return the appropriate choices for explicit review; never switch choices as an implicit retry.
- Files: `submission-drawer.js` (`compare` choice handler and existing status region).
- Verification: opposite-button activation during an in-flight decision issues one request; uncertain retries preserve item ID, digest, choice and request ID; acknowledged adoption shows its actual receipt state and cannot submit a contrary decision from the old preview. Keep current never silently becomes incoming adoption.

### R7-06 Reject a blank numeric merge correction instead of writing zero

- Trigger: clear a numeric scalar in Edit result and apply that manually edited preview.
- Current problem: `collectEditedValue()` uses `Number(el.value)` before validation; JavaScript converts both an empty string and whitespace to zero. A pure-memory reproduction converted a cleared value of 12 to 0 without an explicit zero entry.
- Target: distinguish an empty invalid number from an explicitly typed zero before conversion. Keep the current typed form and point to the numeric field using the existing editor feedback. Preserve valid decimals/zero, null semantics and untouched object members; do not fill, round or infer numeric data.
- Files: `collaboration.js` (`collectEditedValue`, numeric editor feedback); this shared helper also serves Source merge corrections.
- Verification: blank and whitespace numbers cannot create a merge decision and remain editable; explicit `0` stays zero and a valid decimal retains its numeric value. A failure changes neither the original source nor the current merged preview.

### R7-07 Make outstanding merge decisions findable in the existing selector

- Trigger: return to a comparison with many differences and only a few unresolved choices.
- Current problem: the merge summary reports the unresolved count, but Find a change lists every difference with only `differenceLabel()`. It does not distinguish unresolved choices from current/incoming/edited selections, forcing users to open already settled rows to find remaining work.
- Target: organize the existing selector into outstanding and resolved/suggested choices using the returned unresolved IDs and resolution state, with concise status labels. Preserve the chosen stable difference ID across a preview redraw when it still exists. Keep the current Show change action; do not add automatic adoption or another navigation toolbar.
- Files: `collaboration.js` (`mergeSummary`, preview redraw/selection preservation).
- Verification: a mixture of unresolved/current/incoming/edit/auto/same differences can be distinguished directly in the selector; resolving one moves it to its correct group without losing its stable identity. Show change reaches the exact source/global/block difference, and an empty outstanding set does not fabricate a pending task.

### R7-08 Keep a package freeze bound to the selection the user submitted

- Trigger: choose saved submission/work items, press Download selected, then change checkboxes or the scope summary while the freeze request is still running.
- Current problem: the handler snapshots items/summary, disables only its download button and leaves the input form editable. The completion notice says the package is frozen without identifying that it belongs to the earlier selection, so the still-visible changed selection may be mistaken for the package contents.
- Target: keep the submitted selection/summary visibly fixed for the duration of that freeze and describe the captured selected scope in the existing result area. Re-enable editing only after the result or failure is known; keep the returned immutable package download link as the retry path. Do not interpret a browser download request as a file-save receipt or send the package externally.
- Files: `submission-drawer.js` (`open` freeze handler and result area); reuse `showPackageDownload` as the download-status authority.
- Verification: delayed freeze cannot visually drift to a different selected payload; success identifies the captured item selection and offers the same immutable artifact; failure restores the original form selection/summary. A later deliberate selection creates a distinct request, while retry of the same uncertain freeze retains its existing ID.

### R7-09 Refresh an expired task comparison in place

- Trigger: the current source/task changes after a task result was compared but before the decision is applied.
- Current problem: the backend rejects the stale `expected_current_digest` with `Task changed after comparison. Reopen it.` The drawer displays that text but provides no in-place way to fetch a fresh comparison; repeating a choice reuses the old preview/digest. This error is currently a definitive ValueError, not a guaranteed HTTP 409.
- Target: offer Refresh comparison in the existing failure area for a definitively outdated task comparison. Reread the same imported item and current task, preserve the submitted evidence, show the newly authoritative comparison and reset the human confirmation checkbox. Only a new explicit decision may use the new digest; keep uncertain adoption retry handling separate.
- Files: `submission-drawer.js` (`compare` failure recovery), existing collection-preview endpoint.
- Verification: a changed-digest rejection causes no adoption; refresh requests the same item, displays the current task and requires renewed confirmation before any new decision. A stale/failed refresh preserves the previous evidence and does not claim the task now matches; uncertain outcomes reconcile the earlier request first.

### R7-10 Continue editing the actual combined result

- Trigger: edit a conflict value, apply it to the preview, then choose Edit result again to make one further correction.
- Current problem: generic `Collaboration.editDifference()` and `SourceWorkspace.renderMerge()` initialize their form from `diff.incoming` even when `resolution==='edit'`. The current combined value is available in the returned material/source review but is not used. A pure-memory fixture showed `Submitted text` in the reopened editor instead of `Human edited`. The comparison card says Edited result without showing that value.
- Target: show the actual edited combined value in the existing difference card and initialize subsequent editing from that authoritative preview value, using the exact validated path and block identity. Preserve base/current/incoming evidence as separate references. If the current path no longer resolves, keep the evidence and request a fresh comparison rather than falling back silently to incoming text.
- Files: `collaboration.js` difference rendering/editing and shared exact-path value resolution; `source-workspace.js` existing source merge editor. Use existing returned preview data, not new saved business copies.
- Verification: edit/apply/reopen retains the human-combined scalar, nested object or source-review value and allows one further correction; incoming/base/current evidence remains byte-equivalent. Reordered block IDs resolve to the correct block, removed/missing paths fail explicitly, and no preview edit counts as adoption or source rewriting.

## 10. Round 8: Faithful reading and version comparison (implemented; native 200% zoom pending)

Evidence inspected: the current complete HTML sanitizer, Materials reader and location helpers, version comparison and Collaboration comparison renderers. The coordinator observed R8-01 in the actual PE002 restored-workspace preview on loopback port 62846 and approved the ten items for implementation after round 7. Pure in-memory fixtures confirmed the other nine gaps without a live endpoint, model call or business write; this does not constitute implementation or UI acceptance. Retain the safe iframe, strict CSP, source hash binding and unchanged original files. Local anchors must have a unique surviving target. Parse absolute cell references as a whole validated string rather than deleting dollar signs indiscriminately. Merged tables with content in covered cells retain the stored-grid fallback. Real browser zoom is required for the layout acceptance. The existing HTML toolbar is deliberately location-only; its test forbids extra buttons/disclosures, so restoring a permanent Tools menu is excluded.

### R8-01 Keep short original-table labels readable in a narrow HTML pane

- Trigger: read the actual PE002 metadata and definitions tables at approximately 400 px pane width or an equivalent zoomed layout.
- Current problem: the coordinator observed `Sist endret` and `Gjelder for` wrapping into two or three letters per line, and the short definition identifier `a.` splitting across two lines. `_html()` applies `overflow-wrap:anywhere` to the whole body and gives short table columns no useful reading constraint.
- Target: adjust only trusted reader styling so ordinary words and short identifiers remain legible while long data values can wrap or the table can scroll within the reading area. Preserve the source table hierarchy, cell order, text, IDs and original attributes; do not reconstruct or summarize the law.
- Files: `backend/system2/src/pdf_extraction/evidence/material_reader.py` trusted reader CSS; existing reader layout wrapper only if required.
- Verification: inspect the same PE002 tables at approximately 400 px and at 200% zoom; labels and identifiers remain readable, long values do not overlap or disappear, and the exact body text/anchors, strict CSP and source hash are unchanged. This is distinct from R3-01's safe HTML route.

### R8-02 Follow an existing footnote or cross-reference within the saved HTML

- Trigger: activate a source-authored link such as `<a href="#footnote">` whose destination is present in the same saved document.
- Current problem: the sanitizer removes `href`, while the complete reader replaces original IDs with derived source anchors. A pure fixture retained both the link wording and destination text but left the link with only a derived `id`, making the local reference inoperable.
- Target: map an unambiguous original fragment target to its surviving derived anchor and retain only that same-document navigation. Reuse existing anchor inventory, sandbox and source binding. Invalid, ambiguous, removed, external, file and script targets remain inert. No script, external asset fetch, source URL resolution or new toolbar is allowed.
- Files: `material_reader.py` complete-document sanitization; shared region sanitizer only if a narrow safe marker is necessary, with the stricter final allowlist retained.
- Verification: keyboard-activate a local footnote and a return link and reach their exact original target without a document fetch or content rewrite. Duplicate/missing IDs and adversarial hrefs cannot select an invented target or leave the isolated document; hash and CSP protections remain enforced.

### R8-03 Preserve declarative ordered-list numbering in the safe original reader

- Trigger: open original HTML containing an ordered list with `type="a"`, `type="I"` or `reversed`, with optional `start` and explicit item `value`.
- Current problem: the complete reader's final attribute allowlist preserves `start` and `value` but discards `type` and `reversed`. A pure fixture's `<ol type="a" start="4" reversed>` became an ordinary ascending decimal list, changing the visible original item identifiers despite retaining the words.
- Target: preserve validated declarative numbering attributes only on their applicable source elements. Keep source CSS/scripts excluded, preserve existing explicit `li value`, and make no conversion through Markdown or change to Markdown auto-numbering. This affects the original reading projection only, not requirement annotations or the R4 edit serializer.
- Files: `material_reader.py` complete reader allowlist and source-reader tests.
- Verification: alphabetic, Roman, reversed, non-one start and explicit-value fixtures retain their browser-native numbering at reading time; invalid attribute values do not inject markup or styles. Original bytes and normal repeated-`1.` Markdown editing remain untouched.

### R8-04 Retain already-read worksheet rows when continuation fails

- Trigger: scroll to Continue to next rows after reading one or more successful worksheet windows, then receive a read failure.
- Current problem: `loadReader(params, true)` uses the same catch path as full replacement and overwrites all of `#mw-reader`. It records only parameters, and Retry calls `loadReader(params)` without append. A pure fixture lost its existing rows and retried row 81 as a replacement window.
- Target: keep the successful sheet grid, its scroll position and current source identity on an append failure. Put concise failure/Retry feedback at the continuation point and retry the exact failed window in append mode. Scope pending/retry state to material, view, sheet and column window; serialize continuation requests and avoid duplicate rows or automatic retry loops.
- Files: `materials.js` (`loadReader`, `readerAction`, continuation status and loading guard).
- Verification: fail row 81 after rows 1–80 loaded, verify those rows and scroll remain, then retry and append 81 onward exactly once. Repeated activation and delayed responses cannot duplicate rows or affect another sheet/material. No saved content or review status changes.

### R8-05 Keep a selected original cell bound through same-sheet continuation

- Trigger: select an original worksheet cell, append later rows and choose Linked content.
- Current problem: every successful `loadReader()` sets `selectedCell=null`, including append. The append renderer retains the old DOM highlight, while `showLinkedBlocks()` interprets a null selection as the whole sheet. The visible selected cell and the reported association scope therefore disagree.
- Target: retain the exact selected cell/range when appending the same bound worksheet and columns, and keep its highlight synchronized with that state. Clear it on genuine replacement, sheet/material/view change or loss of the selected range. Do not infer new source links from nearby text.
- Files: `materials.js` (`loadReader`, original-cell state, `showLinkedBlocks`).
- Verification: select C23, append rows 41 onward and open Linked content; only links intersecting C23 appear and C23 remains highlighted. A new sheet does not inherit C23; another cell selection updates both the highlight and linked scope. Reading alone never mutates source associations.

### R8-06 Locate valid absolute worksheet references without guessing invalid ranges

- Trigger: follow a saved source reference such as `$C$121:$D$122`, or a malformed/nonexistent explicit cell range.
- Current problem: `Materials.locate()` parses only unanchored plain letters/digits and falls back to A1 on failure; `material-navigation.js` independently rejects dollar signs. A pure fixture navigated `$C$121:$D$122` to row 1/column 1 and found no cell links, while still retaining the original range string as selected.
- Target: use one validated navigation parser for plain and absolute A1-style cell/range references, allowing existing locator fallback only when the explicit range is absent. Normalize navigation coordinates without modifying saved reference wording. A nonempty invalid/reversed range, or one outside already-known bound worksheet dimensions, must show the existing location feedback and keep the current reader rather than guessing A1 or a partial prefix. Unknown sheet dimensions remain an authoritative reader check, not an invented client bound.
- Files: `material-navigation.js` range parsing/matching; `materials.js` `locate`; reuse applicable parsing in the shared evidence reader where practical without changing endpoint contracts.
- Verification: C121, `$C$121`, mixed absolute ranges and multi-letter columns navigate/highlight exactly; malformed values, zero rows and reversed ranges issue no read or guessed highlight. A valid sheet-only source link retains the established deliberate start-of-sheet behavior. All saved refs remain identical.

### R8-07 Expose relative passage moves even when versions add or remove content

- Trigger: compare versions where existing passages are reordered and another passage is inserted or removed.
- Current problem: `versionComparison()` reports order only when the complete ID sets have identical size and membership. A pure saved A/B versus local B/A/C fixture reports C as added but entirely hides the A/B move.
- Target: compare the relative order of surviving stable IDs and show true moves in the existing order disclosure alongside additions/deletions. An insertion that merely shifts indices must not be labelled a move. Preserve complete before/after order for inspection and bind readable passage labels to their version's IDs; do not alter content or choose a preferred version.
- Files: `version-comparison.js` order detection and existing disclosure rendering.
- Verification: A/B→B/A/C and A/B/C→C/A reveal the surviving reorder; A/B→A/C/B shows only an insertion when A/B keep their relative order. Duplicate wording remains disambiguated by identity, and opening the comparison causes no save or adoption.

### R8-08 Read recorded merged-cell structure before choosing a compared table

- Trigger: compare current/submitted tables whose wording is similar but whose valid merged-cell relationships differ.
- Current problem: `tableComparisonMarkup()` renders every stored cell as an independent `td`, displays only the merge count and places actual geometry in JSON details. A pure two-column merged heading fixture produces no `rowspan`/`colspan`, so the visible tables can look identical despite a meaningful relationship change.
- Target: render supported, valid merge geometry from the existing zero-based row/col and span records in the comparison table, using a shared read-only table renderer if available. Keep notes and all stored cell values inspectable. Unsupported, overlapping or inconsistent geometry, including nonempty covered cells, must fall back visibly to the stored grid rather than hiding text or inventing a layout. No table-editing controls are added.
- Files: `collaboration.js` `tableComparisonMarkup`, existing structured table renderer/helpers and minimal comparison CSS.
- Verification: valid row/column spans render distinct current/incoming layouts and retain notes; all cell strings remain available. Invalid or contradictory relationships produce the retained-grid limitation state with original details. Choosing/merely viewing a layout cannot mutate the table, infer headers or adopt it.

### R8-09 Show the actual PDF source page in version comparisons

- Trigger: inspect a comparison block/order entry whose original reference uses the supported zero-based `page_index` field.
- Current problem: Collaboration's private `sourceLocations()` understands positive `page` and page scope IDs but ignores `page_index`. A pure block with `{page_index:2}` has no visible Page 3 label, although the Materials reader already labels/navigates this same reference correctly.
- Target: apply the shared supported source-location rules to comparison labels, preserving explicit one-based page precedence and treating valid zero-based indices correctly. Retain unknown/missing locations as unknown rather than assigning page one; keep original reference details available. This is one cross-renderer location-consistency improvement, not one point per reference format.
- Files: `collaboration.js` comparison source-location helper; existing location helper may be moved/shared to avoid circular imports.
- Verification: page_index 0 and 2 display Page 1 and Page 3 on block and order comparisons, matching their original reader; explicit page values retain precedence. Invalid indices do not become guessed locations, and source references remain unchanged.

### R8-10 Include differing human review declarations in preferred-version comparison

- Trigger: compare a newer saved material and local draft whose text is identical but whose checked original ranges or association-review declaration differ.
- Current problem: `versionComparison()` compares blocks, order and issues only. A pure fixture with saved checked scope `page:1`/associations true and local empty scope/associations false shows no declaration difference and only says passage content/order are identical. The user is choosing a version without visibility of this separate human work.
- Target: expose differing `checked_scope` and `association_reviewed` values in a compact existing-comparison disclosure, using recorded scope labels where available and clearly separating declarations from content. Show both states faithfully; keep preferred-version save, version history and server invalidation rules unchanged. Do not union checked ranges, carry an invalid declaration forward, or imply that matching text proves review completion.
- Files: `version-comparison.js`; `materials.js` comparison call may pass existing scope labels as read-only context.
- Verification: identical-text fixtures with differing range/association checks show both exact declaration states; equal declaration states add no extra UI. Content differences still show normally. Selecting a preferred version follows the existing server checks and never auto-approves content, Requirements or A/B/C.

## 11. Round 9: Existing settings and operational status (implemented; browser acceptance pending)

Evidence inspected: `app.js` menu/polling paths, `global-settings.js`, `runtime-status.js`, `site-catalog.js`, the embedded confidence-settings form in `extraction.js`, and their owning backend configuration/scheduler contracts. Pure in-memory stubs reproduced the redraw, input-loss, conflicting-key, repeated-revision, catalog and import-input cases. Saved-assignee omission and omitted dispatch results were confirmed in generated markup; native select/file-picker behavior still needs browser acceptance. No provider call, real configuration change, schedule dispatch, import or export occurred. Reuse native controls and the existing `run()` helper; do not add a settings framework or new permanent panels.

### R9-01 Keep an open runtime report stable during automatic refresh

- Trigger: expand Previous failure retained or focus a runtime control while the application performs its periodic status read.
- Current problem: `installRuntimeStatus.draw()` replaces the dialog's complete `innerHTML` whenever an open dialog receives a successful refresh. The in-memory fixture lost the open details and replaced the focused Refresh button even when the same component remained present.
- Target: preserve component disclosures by their existing stable component IDs, the user's reading scroll and the matching focused control across status redraws, or update existing nodes without replacing them. A background refresh must not move focus. Keep only the current runtime report and its already-retained error history.
- Files: `runtime-status.js` (`draw`, existing component markup/bindings).
- Verification: expand the source component's history, focus its summary or Refresh, and complete several status refreshes; the same meaningful reading position remains. Removed components use a valid dialog fallback without stealing unrelated focus. No additional service action or history store is introduced.

### R9-02 Recover a failed runtime read without losing the last known report

- Trigger: choose Refresh status or receive a periodic read failure after a successful report, including the first read failing before a report exists.
- Current problem: the catch handler replaces the report with error text and a newly created Close button. The prior checked time and component evidence disappear, and there is no in-dialog Retry. A pure fixture confirmed both losses.
- Target: retain a clearly dated last-successful report as stale evidence, with a concise current read-failure message and one read-only Retry. With no prior report, show the same recovery action without inventing component health. Reuse the existing pending guard and expose its loading state; repeated activation must start one status read.
- Files: `runtime-status.js` failure/pending rendering and existing Refresh handler.
- Verification: failed refresh retains the old checked time while identifying that it is not current; successful Retry clears only that read failure and updates the timestamp. A first-read failure remains closable/retryable. No conversion, extraction or business mutation endpoint is called.

### R9-03 Keep settings forms fixed while their submitted save is pending

- Trigger: submit API, catalog, schedule or confidence settings, then edit inputs, redraw catalog rows, submit again or close the Settings dialog before the response returns.
- Current problem: the shared `run()` disables Close but leaves API/schedule inputs editable. Catalog and confidence saves bypass it after initial loading. The catalog fixture reported `globalBusy:false` and allowed Close during its save; the API fixture entered a second dummy key during save and then lost it when the first response cleared the password field. Catalog redraws can also recreate an enabled submit button mid-request.
- Target: use the existing Settings operation guard for embedded saves and native form/fieldset disabled state to freeze the submitted inputs and structural controls until the request settles. Capture the payload before disabling controls, block duplicate saves and Close/Escape while pending, and restore the prior permission/disabled state afterward. For the standalone confidence form, apply the same local pending rule without introducing a dialog dependency. Saved feedback must refer to exactly the submitted values.
- Files: `global-settings.js` `run`/form save wiring; optional existing-save callback in `site-catalog.js` and `extraction.js` settings form.
- Verification: deferred saves cannot accept a second submission, recreate active catalog controls or close the containing dialog. Entered values survive a rejected save; a successful API save clears only its submitted key. Read-only/offline controls remain disabled afterward. No setting is saved merely by opening or editing the form.

### R9-04 Require one unambiguous API-key change intent

- Trigger: enter a new API key and also check Remove saved key before saving.
- Current problem: the UI permits and sends both values. `AISettings.save()` gives `clear_key` precedence, silently discarding the replacement key while the UI reports that settings were saved. A pure form fixture confirmed the contradictory payload.
- Target: before a save, point to the conflicting existing password/checkbox controls and require the human to choose replacement or removal. Keep their unsaved input for correction; do not clear a typed key or silently uncheck their choice. Existing keep-key behavior with a blank input remains unchanged, and no key is displayed in feedback, logs or a comparison.
- Files: `global-settings.js` AI form validation and field-linked feedback; backend key semantics remain authoritative.
- Verification: a nonempty key plus Remove sends no save and retains the correction controls; replacement alone sends the exact entered key, removal alone sends explicit removal, and a blank unchanged key keeps the existing secret. No connection test or generation runs.

### R9-05 Resolve a changed settings revision without rebuilding unsaved input

- Trigger: save settings after another window changed the same configuration revision.
- Current problem: API, catalog, schedule and confidence forms retain the old revision after their owner's definitive rejection and expose only an error asking the reviewer to reopen/reload. Repeating Save sends the same old revision; reopening reconstructs the form from saved values and loses the unsaved configuration. The API fixture sent revision 2 twice after a changed-settings rejection. These owning services use definitive errors, not a guaranteed HTTP 409.
- Target: in the existing failure area, offer a read-only refresh of that configuration and make differing nonsecret saved values available alongside the retained form. Require an explicit human choice to use current saved values or continue editing the retained proposal against the newly read revision; never silently rebase and resubmit. Preserve server-only/hidden fields through their current owner. Show only key-presence/change intent, never key material; never copy the masked password input's value into comparison DOM, feedback or logs. Keep this recovery local to the existing forms rather than building a general merge editor.
- Files: `global-settings.js`, `site-catalog.js`, `extraction.js` settings save/error paths and their already-existing read endpoints.
- Verification: a definitive revision rejection retains every entered nonsecret value and any masked key input, reads the current version only when requested, and requires a new explicit Save after review. Another intervening change still rejects safely. Transport uncertainty is not automatically treated as a definitive conflict, and no schedule/provider operation is triggered by comparison.

### R9-06 Do not silently choose a catalog comparison after a type change

- Trigger: change a catalog field from Text with only Contains allowed to a type that does not support Contains.
- Current problem: the type handler filters incompatible operators and, when none remain, assigns `['equal']`. A pure fixture changed string/contains to boolean/equal without the reviewer selecting Equal.
- Target: retain every compatible explicit comparison, show the now-empty selection when all prior choices are incompatible, and open/identify the existing Allowed comparisons area so the human can choose. Explain the removed incompatible choices concisely in that row. Do not auto-select a substitute, save the catalog or rewrite any existing saved design. The initial defaults of a deliberately added new field are a separate existing behavior.
- Files: `site-catalog.js` type-change handler and current comparison disclosure.
- Verification: Text/Contains→Yes-no leaves no silently inserted Equal; Save stays blocked until an allowed operator is deliberately selected. A type change that retains Equal keeps it, and all mapping/label/description text survives. Existing interpretations retain their original catalog version and approval state.

### R9-07 Locate invalid catalog fields before submitting the whole catalog

- Trigger: duplicate a database mapping, type an invalid mapping, remove all allowed comparisons or exceed a current owner-defined field limit in a long catalog.
- Current problem: the native form covers required labels/mappings only. It sends duplicate/invalid identifiers and empty comparison sets, after which the server returns a generic catalog-wide error at the bottom. A pure fixture submitted an empty operators array and produced no field-linked invalid marker, leaving the responsible row undisclosed.
- Target: mirror the existing owner validation needed to identify the offending row, including unique `table.column` identifiers, nonempty type-compatible operators and existing length/count bounds. Use native validity and a concise row-linked message, reveal/focus the first invalid control, and retain exact typed values. The server stays authoritative; do not normalize mappings, add operators, truncate fields or mutate the catalog to make it pass.
- Files: `site-catalog.js` submit validation and existing row/disclosure markup; reference `backend/system3/site_catalog.py` constraints.
- Verification: duplicate and malformed mappings, an empty operator set and supported boundary cases are identified at the correct row without a save request. A corrected field submits its exact value; supplementary Unicode is counted consistently with the server where text-length limits apply. Empty whole catalogs remain valid if the server permits them.

### R9-08 Allow reselecting the same collaboration ZIP after an import failure

- Trigger: choose a ZIP for Import work, receive a file-validation or transfer failure, then choose that same file again.
- Current problem: `#sync-file.value` is reset only after a successful import. Failure retains the native input's file selection, so choosing the identical file again need not produce `change` and the apparent retry does nothing. The isolated failure fixture retained the selected input value.
- Target: reset the file-picker selection at a point that allows a fresh explicit same-file choice after failure while retaining the failed-file identity and current comparison in the existing feedback. Snapshot the File before resetting it if needed. Do not automatically retransmit, apply or discard a previous valid comparison, and keep the current unsaved-work and busy guards.
- Files: `global-settings.js` collaboration file picker/import handler.
- Verification: using the browser's native picker, a failed import followed by selecting the same ZIP triggers one new explicit import; cancel triggers none. Selecting a different file also works. A failed read does not change saved work, apply an import or erase an earlier successful preview.

### R9-09 Preserve a saved schedule assignee that is absent from the current roster

- Trigger: open Automation when the saved assignee is not among `getState().actors`, then save an unrelated interval change.
- Current problem: the Assign to select includes only current actors and marks a matching option selected. If none matches, the original assignee is omitted and the native select falls back to its first option. A fixture omitted `Absent reviewer` entirely, allowing an unrelated save to silently assign checks to `First reviewer`.
- Target: retain the exact saved assignee as a clearly identified saved value when it is outside the current roster. Require an explicit selection before changing it; a missing roster must not invent a replacement. Keep the owning service's named-reviewer and offline scheduling rules. No person is added to the roster and no schedule is enabled by rendering the option.
- Files: `global-settings.js` Automation assignee options and save validation.
- Verification: an absent saved assignee remains the selected visible value, and saving only the interval preserves its name exactly. A deliberate current-roster selection changes it only on Save. Empty rosters and read-only installations retain their guards; no task is dispatched during this test.

### R9-10 Show the reported schedule result separately from its configured timing

- Trigger: inspect an enabled schedule after a run selected fewer materials than requested, reused already-pending checks or skipped a frozen archive.
- Current problem: `/api/automation` already returns the scheduler's `status`, selected/requested/eligible counts and per-item created/already_pending/skipped outcomes, but the Settings view ignores the result and shows only last/next times. A completed dispatch fixture with zero selected from five requested is invisible in the generated UI. Backend `complete` here means task dispatch finished, not that a human completed the checks.
- Target: display one compact read-only result next to the existing timing: its reported time/state and actual task-creation counts, with an existing-style disclosure only when recorded skip reasons need inspection. Clearly distinguish configured schedule, last reported dispatch and completed human review. Missing result evidence stays unrecorded; do not infer failures, success or currentness from the next-run timestamp. Reuse the current response without adding polling or a dispatch action. New tasks remain owned by the existing scheduler after a human explicitly saves its plan; merely opening, refreshing or recovering this status view cannot dispatch them.
- Files: `global-settings.js` Automation result markup, using the existing `AutomationSettings.read()`/`MaterialInspectionSchedule.run_due()` response.
- Verification: scheduled, disabled, zero-eligible, created, already-pending and skipped fixtures describe exactly their reported outcomes. A later setting change does not relabel an earlier run as belonging to the new configuration. No automatic schedule activation, task creation, review approval or new backend history is introduced.

## 12. Round 10: Keyboard, reading continuity and precise navigation (approved)

Evidence inspected: the current `Materials` mount, navigation, history, layout, reader and region-dialog paths; `InterpretationEditor.render`/approval paths; `StructureEditor.bind`; and their existing CSS. In-memory calls using the actual methods or exact registered callback reproduced wrong save ownership, collapsed destinations, a hidden focused separator, a history/restore identity mismatch, 400 spreadsheet tab stops, lost numeric input and stale selection-toolbar coordinates. Tools dismissal, reading-mode anchoring and approval focus are grounded in their complete existing handlers and redraw paths; native browser acceptance is still pending. No live API, browser, saved-data mutation or image request was used. This round does not count a second Find/IME fix, repeat earlier reader validation or introduce another permanent toolbar.

### R10-01 Save the work owned by the focused pane

- Trigger: press Ctrl/Cmd+S while editing Requirement splitting in the third pane, or use a capital `S` key value while editing A/B/C in the fourth pane.
- Current problem: the global `Materials.saveKey` routes every unhandled shortcut to Material/inspection save. The third pane has no owning Save shortcut, while the fourth intercepts only lowercase `s`. A fixture therefore chose Material Save from the third pane and did not intercept uppercase `S` in the fourth. Material save rejects dirty Requirement splitting instead of saving that intended work.
- Target: route one shortcut to the focused existing owner: Requirement Save, interpretation Save, or the current Material/inspection Save as appropriate. Share only the small routing needed; avoid duplicate bubbling handlers. Respect pending, read-only, stale-source, unresolved-save and native-dialog guards, and ignore composing key events. Saving never approves or generates anything. If the pane's Save is unavailable, retain its own explanation rather than falling through to another save owner.
- Files: `materials.js` `mount`/save-key lifecycle; `requirements.js` existing save entry; `interpretations.js` local shortcut binding.
- Verification: Ctrl/Cmd+S from each editable pane makes exactly one call to its owner, including uppercase `S`; the other drafts and approval states remain unchanged. Composition, open dialogs, busy/read-only state and pending recovery cannot trigger another owner's save. Final browser checks include keyboard focus inside actual third-pane controls and fourth-pane Set inputs.

### R10-02 Reveal the exact destination of explicit source/content navigation

- Trigger: collapse Original or Extracted content, then use a passage's Original action, an original location's Linked content choice, or Chapters to navigate there.
- Current problem: `locate()` and `jumpToBlock()` update or scroll their destination without calling `revealPane()`. Their old narrow-window `data-active` update cannot override the current collapsed-pane layout. An isolated call left both destinations in `collapsedPanes` after navigation.
- Target: for successful explicit navigation, restore only the destination pane, retain other collapse/width preferences, and bring the recorded target into the actual horizontally scrollable workspace. Use stable block IDs and the existing exact source-location readers; do not guess a source target or create links. Give keyboard-initiated navigation a visible destination focus target without changing content or moving focus for background reads.
- Files: `materials.js` `jumpToBlock`, `locate`, `showLinkedBlocks` and current pane helpers; reuse the earlier location validators.
- Verification: a collapsed original opens at its recorded page/cell/anchor, and a collapsed content pane reveals the chosen stable block. At 200% zoom both remain reachable within the workspace. Unrelated panes stay collapsed; absent/deleted locations show the current error rather than navigating to another block. Existing third-pane annotation navigation remains unchanged.

### R10-03 Keep a keyboard path after collapsing a pane with its separator

- Trigger: focus a pane separator and use Home, End or an arrow step that collapses its adjacent pane.
- Current problem: `wireResize` calls `applyPaneWidths()` after collapse, which can hide the currently focused separator. It gives focus no successor. The actual handler fixture hid the first separator on Home without focusing the resulting collapsed rail.
- Target: after an explicit keyboard collapse that hides the active handle, focus the relevant visible collapsed rail or another adjacent valid layout control. Preserve the existing Enter/Space restore behavior, width persistence, pointer behavior and minimum widths. Do not add keyboard instructions or controls permanently to each pane.
- Files: `materials.js` `wireResize`/existing collapse helpers; existing pane keyboard tests.
- Verification: Home/End and collapse-threshold arrows leave focus on a visible target; Enter/Space can immediately restore that pane and continue the normal keyboard order. Layout remains valid with different adjacent panes already collapsed. Pointer cancel still restores its pre-drag widths and does not steal keyboard focus.

### R10-04 Dismiss existing Tools popovers predictably

- Trigger: open Material Tools, content Tools or reader Tools by keyboard, then press Escape, click outside, or finish a command from that popover.
- Current problem: these controls are native `details` styled as floating popovers, but their Material event paths have no popover-specific Escape, outside-pointer or completed-command dismissal. They can remain over the content while focus moves elsewhere. The application's separate main menu and the writer's Insert chooser already have their own lifecycle and are outside this item.
- Target: keep the existing compact native disclosure controls while closing these specific transient Tools popovers on Escape/outside interaction and after a completed command. Escape returns focus to the owning summary. Opening a dialog transfers focus to that dialog without a competing focus restore. Validation failures retain the relevant editable popover context. Do not attach menu behavior to ordinary Set, evidence, history or document disclosures, or add ARIA menu roles without their full interaction contract.
- Files: `materials.js` shell/render bindings and lifecycle cleanup; current Materials CSS only where needed for the existing popover.
- Verification: keyboard-open each Tools popover, dismiss with Escape and continue from its summary; outside pointer closes it; a launched dialog receives focus; a validation failure does not hide the invalid input. Ordinary A/B/C and evidence disclosures remain open and operate natively.

### R10-05 Bind saved-history reads and restore to the material that opened them

- Trigger: request saved history and switch materials before it returns, close/replace its dialog during a version read, or change the active material/draft while Restore is awaiting its read.
- Current problem: `historyDialog()` does not capture/check an opening material/view/actor token. Its nested Read/Restore handlers use the then-current `this.id`. The fixture requested history for A, opened that late history after B became current, and Restore subsequently read `/api/material?id=B&revision=4`. It then applied B's response using the old history choice.
- Target: capture the existing material, actor, reader view and request/dialog ownership before reading history. Keep paging, lazy version reads and Restore bound to that identity. Reject or ignore late results after close, replacement, navigation or owner change. Before applying a restored local draft, recheck the same ownership and that intervening edits have not invalidated its initial clean-draft guard. Keep prior history visible/retryable on a paging read failure rather than closing it before success. Restore remains an explicit local draft action; it must not save, restore old confirmation or overwrite newly edited content.
- Files: `materials.js` `historyDialog` read, paging, lazy-read and restore closures; reuse existing ownership/request conventions.
- Verification: deferred A history/version/restore results after switching to B cannot open a dialog, request B's corresponding revision or replace B's draft. Closing/replacing the dialog or editing the current draft before the restore response prevents application. A normal same-material restore opens the exact chosen historical version as an unconfirmed unsaved draft; explicit Save remains separate. All verification uses disposable in-memory or isolated fixtures.

### R10-06 Keep the same passage visible when switching Current text and Changes

- Trigger: read well into a long corrected document, then switch its reading mode where earlier additions/deletions make Current text and Changes different heights.
- Current problem: the mode handler redraws the document, and `renderContent()` restores only the old raw `scrollTop`. It records no stable visible block or relative passage position. Equal pixel offsets in the two layouts need not show the same passage. R4's existing cross-mode Undo keeps edit history but does not establish this reading anchor.
- Target: for a deliberate mode change, retain a stable current block and a sensible relative visible offset, then locate that same block in the new representation. Use an existing surviving neighbor or the document start only when that block is absent, without guessing source text. Preserve the mode selector's keyboard focus and current edit/Undo state. Do not scroll on unrelated background rendering or insert new navigation UI.
- Files: `materials.js` reading-mode change/render path; `markdown-content.js` existing stable block markup only if needed for the anchor.
- Verification: in a long fixture with substantial changes before the visible passage, switching both ways keeps that block visible at normal and 200% zoom. The document, dirty state, source refs and Undo/Redo history are byte-for-byte unchanged by the navigation. Deleted-only content and an empty document have a valid fallback and no exception.

### R10-07 Make the original spreadsheet one navigable keyboard region

- Trigger: enter the original worksheet with Tab and try to reach the controls after its loaded cell window, or activate a cell's native Formula disclosure.
- Current problem: `renderReader()` assigns `tabIndex=0` to every original cell, and its Enter/Space handler is attached without checking that the cell itself is the key target. The 40-by-10 fixture produced 400 cell tab stops; a nested Formula summary's key event can also be intercepted as Linked content.
- Target: reuse the existing selected-cell state for a small roving focus pattern within the loaded grid. Provide one current cell as the grid's entry point, arrow movement within existing loaded cells, and a short native Tab route through that cell's available Formula disclosure and out of the grid. Keep nested native controls' Enter/Space behavior intact; activate Linked content only from the cell itself. Do not fetch more cells, edit values, calculate formulas, infer merged values or add a grid framework merely because focus moves.
- Files: `materials.js` `renderReader` original-cell binding and existing Excel markup.
- Verification: a 400-cell window has one cell entry point; arrow movement stays within the actual loaded rows/columns and preserves exact addresses. Tab/Shift+Tab can leave the grid promptly, including cells with formulas. Enter on Formula opens its native disclosure without opening Linked content; Enter on the cell opens only its recorded associations. Append/paging preserve or choose a valid loaded focus cell without changing selection links.

### R10-08 Keep focus on the reviewed A/B/C card after an explicit decision

- Trigger: approve one A/B/C card, approve an AI candidate or dismiss a candidate using the keyboard.
- Current problem: these actions call `render()` and replace the full interpretation host. The clicked Approve becomes disabled or the candidate actions disappear, and the renderer restores disclosures but not a meaningful focus destination. A keyboard reviewer loses their position in the just-reviewed card.
- Target: after the explicit decision, retain focus within that same stable card, using its existing review status or another appropriate surviving card entry. Keep its completed decision visible in the existing feedback and preserve open editing/evidence disclosures. Do not automatically advance to, open or approve the next card, and do not move focus for background provider/generation reads. This is decision completion, separate from R6's new-rule/new-concept editor focus.
- Files: `interpretations.js` approve/accept/dismiss action paths and render focus handoff.
- Verification: approve A, approve a B candidate and dismiss a C candidate by keyboard; each leaves a visible focused location on that same card with the exact resulting status. The next Tab follows the card's normal order. The other cards' approval state and content stay unchanged, and no Save or extra AI request occurs.

### R10-09 Keep the source-selection toolbar usable after the viewport changes

- Trigger: select Requirement source text near the right/bottom edge, then shrink the window, zoom to 200% or scroll its owning pane before assigning a role or Group.
- Current problem: `StructureEditor.bind()` computes the toolbar's fixed `left`/`top` only during source mouseup/keyup. CSS limits its width but cannot correct a stale position. After the fixture narrowed its viewport from 1200 to 500 pixels, the toolbar retained `left:880px` and was outside it.
- Target: remeasure an active, still-valid source selection and constrain the existing toolbar to the current viewport when its layout changes. If the selection is no longer visible or valid, hide the toolbar without assigning stale text; preserve the source-selection guards already established in R5. Handle Escape from the toolbar without leaving focus on a hidden control, and remove listeners/observers when their owner changes. Retain all source characters and code-point span boundaries.
- Files: `requirement-structure.js` capture/toolbar lifecycle; `requirements.css` current toolbar containment if needed.
- Verification: actual browser resize and 200% zoom keep every role/Group control reachable for the same valid selection. Scrolling a selection fully away or changing its owner cannot leave an actionable stale toolbar; Escape returns to the original selection context. Keyboard selection still assigns the exact original span, and resizing or dismissing alone does not dirty the Requirement.

### R10-10 Preserve unfinished numeric typing in the PDF-region dialog

- Trigger: replace a region's Left/Top/Right/Bottom percentage using the keyboard, including temporarily clearing a field or typing a decimal value.
- Current problem: every coordinate `oninput` immediately calls `Number(value)` and `draw()`, which rewrites all four input values. The actual dialog fixture changed an empty Left field into `0` and changed a partial `12.` into `12`. Invalid intermediate input can become `NaN` rather than remaining editable. This makes precise manual entry unreliable even before Use region is chosen.
- Target: retain each raw in-progress input value. Update only the visual preview when all four coordinates form a complete, finite, nonempty rectangle within the existing 0–100% contract. On Use region, identify/focus an invalid field and retain the typed values; only a valid explicit Use updates the draft's existing source region. Keep the current coordinate/rotation transform semantics, pointer selection, source identity and final Material Save boundary. Never silently insert zero, round a human value, normalize an invalid rectangle or write `NaN` into the form/draft.
- Files: `materials.js` `selectImageRegion` numeric input, preview and Use validation wiring.
- Verification: clear and retype a coordinate, type a decimal through its intermediate state, and correct invalid/out-of-order bounds without value loss. The preview retains the last valid rectangle while input is incomplete. Use on invalid values makes no draft change; valid Use records the exact supported coordinates, and Close/Cancel leaves the previous region unchanged. Pointer selection continues to populate a valid four-coordinate proposal without saving it.

## 13. Round acceptance and rolling planning

For round 1, run the affected source UI tests and the existing full frontend suite. Use a disposable fixture for simulated slow/failing reads and invalid-input cases; use the live UI only for read-only title/keyboard checks. The coordinator checks the actual browser at a standard desktop width and 200% zoom and records each item as passed, failed or unverified with its evidence. Unit tests alone do not prove zoom, focus or screen-reader semantics.

After acceptance, inspect the next theme against current code. The implementer may report a proposed item already works or a fix requires a business-contract change; the planner must replace that item with another grounded, independent improvement in the same round before counting ten. Update this file's current status rather than adding a parallel plan. Store concise round evidence under `project-support/validation/` and link it here when it exists.

| Round | Proposed | Implemented | Verified | Evidence |
| --- | ---: | ---: | ---: | --- |
| 1 | 10 | 10 | 10 | [Implementation and browser acceptance](../validation/ui-round1-20260922/RESULTS.md), coordinator confirmed all ten checks |
| 2 | 10 | 10 | 10 | [Implementation and coordinator acceptance](../validation/ui-round2-20260922/RESULTS.md); native IME manual verification not performed |
| 3 | 10 | 10 | 10 | [Implementation and browser acceptance](../validation/ui-round3-20260922/RESULTS.md); 416 frontend, 51 reader and 27 HTTP checks |
| 4 | 10 | 10 | 10 | [Implementation and coordinator acceptance](../validation/ui-round4-20260922/RESULTS.md); 426 frontend, 35 MaterialService/Store checks and isolated save/reopen fidelity |
| 5 | 10 | 10 | 0 | [Implementation and functional browser checks](../validation/ui-round5-20260922/RESULTS.md); 442 frontend, 20 + 17 owning backend checks; native 200% zoom pending |
| 6 | 10 | 10 | 0 | [Implementation, review corrections and functional browser checks](../validation/ui-round6-20260922/RESULTS.md); 51 related tests independently rerun; implementer reports 462 frontend checks; isolated owner-service save/reopen passed, native 200% zoom pending |
| 7 | 10 | 10 | 0 | [Implementation, review corrections and functional browser acceptance](../validation/ui-round7-20260922/RESULTS.md); 90 tests independently passed before browser initialization corrections, then final Drawer 12/12 independently passed; real owner Save/reopen revision 3, source unchanged; native 200% pending |
| 8 | 10 | 10 | 0 | [Reader items 01–03](../validation/ui-round8-20260922/READER_RESULTS.md) and [frontend items 04–10](../validation/ui-round8-20260922/FRONTEND_RESULTS.md); independent reader checks 19/19, three frontend suites 63/63 then corrected reader-display 23/23; all ten functional browser checks passed, including real PE002 400 px and frontend 572 px layout; native 200% pending |
| 9 | 10 | 10 | 0 | [Runtime items 01–02](../validation/ui-round9-20260922/RUNTIME_RESULTS.md) and [settings items 03–10](../validation/ui-round9-20260922/SETTINGS_RESULTS.md); independently passed material-navigation 20/20 and final settings-peer 18/18; runtime functional browser checks passed, settings browser acceptance and native 200% pending |
| 10 | 10 | 0 | 0 | Approved; implementation after round 9; current code and seven isolated interaction fixtures inspected; browser acceptance pending |
