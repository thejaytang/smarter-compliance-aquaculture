# Material library UI round 2

2026-09-22. R2-01 through R2-10 passed implementation and coordinator acceptance. The final frontend suite passed 405 tests. Native input-method composition was covered by behavioral tests, not a manual operating-system IME session.

Product edits are confined to the Materials library code and one repeated Archive heading in MaterialInspection. No backend, queue membership, Example policy, original content, business database, API schema or dependency was changed.

## Coordinator browser acceptance

The actual Materials component and CSS ran in Chrome against the 124-record page-local fixture. No live business request was proxied.

- R2-01/02/05: ranges 1–50, 51–100 and 101–124 were correct; explicit paging reset scroll to zero and focused the range. Same-reviewer leave/return preserved page 2, another reviewer began at page 1, and switching back restored page 2.
- R2-03/04: a Unicode query entered on page 3 followed immediately by Previous issued only offset zero for the new query and showed the one matching row. Composition-event sequencing and leaving/remounting mid-composition passed their focused regression tests. An unmatched query showed `0 of 0 materials`.
- R2-06/07: the blank saved-source opener was disabled; FX001/v1 and FX002/v2 remained distinguishable despite identical Unicode/HTML-like titles. Selecting FX002 enabled Open and the logged request contained exactly FX002.
- R2-08: running, partial, ready and failed rows exposed their distinct processing states, with adoption still pending and failed extraction retaining saved content.
- R2-09/10: Archive list, material header and inspection heading stated only Content finalized. Two checks showed their different archived revisions/dates; selecting revision 2 requested the exact check-v2 task ID. The fixture records that request without opening a real inspection.

## Validation

- `workbench/.venv/bin/python workbench/tests/run_checks.py frontend`: 405 tests passed; see `frontend-after.log`.
- Material library, navigation lock and existing material UI targeted run: 86 tests passed; see `material-tests.log`. The final full run additionally covers strict rejection of malformed inspection dates.
- Ten new behavior tests cover all ten items; no new test framework/dependency.
- Changed-file whitespace check passed.

| Item | Implemented result and local evidence | Browser acceptance |
| --- | --- | --- |
| R2-01 | Range shows exact accepted offset/row count/total with a named page-control group; 0, 1, 50, 51 and 124-result cases passed. | Read initial, middle and last pages, plus empty search. |
| R2-02 | Existing reviewer/category session context retains accepted offset and scroll; remount tests prove Review/Archive/reviewer separation. | Page 2, scroll, use Leave and return; switch reviewer and Archive independently. |
| R2-03 | Composition suspends search debounce until completed text; real timer test sends one complete Unicode query and ordinary typing remains debounced. Leaving/remounting clears composition state; a mid-composition module exit followed by ordinary search and paging passes. | Use a native input method or composition-capable fixture interaction; inspect local request log. |
| R2-04 | Paging compares its accepted query/filter context with the current one, cancels pending debounce and starts new contexts at zero; stale responses cannot replace the newest query. | Page 2, type new query and immediately Next; inspect zero-offset request and no duplicate timer result. |
| R2-05 | Explicit page movement resets library scroll and focuses the result range; ordinary reads and Back restoration preserve their own scroll. | Next from bottom begins at range; open/close material returns to prior list scroll. |
| R2-06 | The saved-source opener starts disabled, has a prerequisite hint, and only enables for an existing exact selected source ID; busy/idle respects that prerequisite. | Expand saved-source section, inspect blank/valid choice and opener state. |
| R2-07 | Source options show exact ID, source title and recorded version; duplicate Unicode/hostile titles remain distinct and escaped. | Select both same-title sources and inspect exact source_id in the local log. |
| R2-08 | Current running, partial, ready and failed extraction states appear in Pending work via existing derived status; adoption is still pending and routine saved-content noise is suppressed. | Read first four synthetic rows and an ordinary row. |
| R2-09 | Archive row, material header and inspection heading say Content finalized without inventing Requirement completion or incompleteness; revision and recorded author/time remain. | Inspect an Archive row and its opened detail. |
| R2-10 | Inspection links include archive revision and recorded creation time; exact task IDs stay unchanged. Missing, malformed and impossible dates say Date not recorded. | Read the two checks on material 5 and activate each; inspect original task ID in the log. |

## Isolated browser fixture

Open `http://127.0.0.1:62844/project-support/validation/ui-round2-20260922/fixture.html` using the same repository-root static server as round 1. It imports the actual Materials class and shipped CSS, and supplies 124 synthetic materials through an in-page API stub. Reviewer, Archive and Leave-and-return controls exercise the real mount flow. All request identities are recorded visibly; none are proxied to business APIs. Synthetic inspection selection intentionally stops with a visible fixture-only message after logging the selected task ID. The script passed `node --check`.

No browser action, live work mutation or server startup was performed by the implementation agent.


R2-09 follow-up during R3 review: `Collaboration.renderToolbar()` and `confirmMaster()` had two remaining Archive labels. Both now say `Content finalized`; confirmation still explains that archiving content does not complete Requirement structuring. The existing coordinator/archive callers remain unchanged. A rendered toolbar/dialog regression was added in `collaboration-ui.test.mjs`; this is a correction to R2-09, not an additional improvement point. The latest complete frontend result is recorded with R3.
