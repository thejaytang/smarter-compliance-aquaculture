# R8 frontend reading and comparison: items 04–10

All seven assigned frontend items are implemented. Items 01–03 and their browser evidence belong to the coordinator’s [reader results](READER_RESULTS.md). Coordinator browser acceptance and independent review remain separate from this implementation record.

Round-only baseline: `/tmp/ui-r8-frontend-baseline`; diff: `/tmp/ui-r8-frontend-net.diff`. Only Materials, material-navigation, version-comparison, Collaboration and three existing test suites were changed. No saved source, business database, backend route, dependency, review declaration or adoption behavior was changed.

| Item | Behavior |
|---|---|
| R8-04 | Continuation serializes the next exact worksheet window. Failure retains all successful rows, current source/reader and latest scroll. A compact retry replaces the continuation trigger, preventing automatic retry loops. Retry is bound to material, view, workspace token and the original sheet/column window; mismatched source hash/window or late replies cannot append. |
| R8-05 | Same-window append retains the exact selected cell/range and synchronizes its DOM highlight. Linked content still uses the selected range. Genuine replacement clears it; a missing selected range loses its stale highlight/state. |
| R8-06 | Shared A1 parser supports plain and mixed absolute references, rejects partial/reversed/zero/unsafe coordinates and retains saved wording. Known dimensions reject an invalid location before any read. Unknown dimensions are checked against the returned authoritative sheet while the current reader remains intact until success. |
| R8-07 | Version comparison examines relative order of surviving IDs alongside additions/removals. Insertion-only index shifts do not count as moves. Both complete orders include passage labels and stable IDs. |
| R8-08 | Valid recorded row/column spans render in the existing comparison table. Overlap, invalid geometry or nonempty covered cells retain the full stored grid with a limitation note. All notes and original details remain inspectable. No header inference or table edit was added. |
| R8-09 | A shared source-page helper handles valid one-based page precedence, zero-based page_index and page scope IDs. Invalid locations remain unknown. Block/order comparisons and the Materials label use the same rule. |
| R8-10 | Different checked_scope and association_reviewed declarations appear separately from passage content, with existing scope labels and exact IDs. Equal states add no disclosure; no declarations are merged or automatically approved. |

Validation: 11 added regressions in the existing reader-display, interaction-revision and collaboration-ui suites; those suites **64/64 passed**. Existing Materials UI regressions **73/73 passed**. Complete current frontend **495/495 passed**, `frontend-after.log`, including concurrent coordinator runtime and R7 work. Initial complete-suite mocks exposed an unnecessary full-replacement append-error lookup; it is now scoped to append only. No test expectations were weakened. Independent review then added one retained-reader race regression: a failed competing location read cannot strand the old continuation button disabled. Final reader-display is 23/23 and the three related suites are 64/64 after that correction; the complete 495-test snapshot predates only this narrow correction.

## Disposable browser fixture

```sh
workbench/.venv/bin/python project-support/validation/ui-round8-20260922/frontend_fixture.py --port 62853
```

Open `http://127.0.0.1:62853/`. The actual Materials reader and comparison renderers use synthetic worksheet responses in page memory. The server only serves local frontend assets and rejects every POST. Layout explicitly isolates body/header from global application flex styles. Static assets return HTTP 200, the served module parses as `.mjs`, and a write attempt returns 403. The health process exited.

Suggested checks:

1. Select C23, scroll to continuation and let the armed row-81 failure occur. Rows 1–80, C23 selection and scroll remain. Retry appends 81 onward once; Linked content still lists only the C23-linked passage. Delay a continuation and activate repeatedly to check the guard.
2. Locate `$C$121:$D$122`; confirm row 121/column C and exact linked passage. C121junk and an out-of-bound range keep the current reader and show location feedback. Switching worksheet clears selection.
3. Expand passage order and human review declarations. Duplicate wording is distinguished by IDs; both declaration states remain visible while content stays unchanged.
4. Compare the valid colspan heading with contradictory covered text. The latter shows its complete stored grid, limitation note, notes and original details.
5. Read the same Page 3 label in block and order comparison for the preserved page_index 2 source reference.

Native layout/keyboard acceptance and zoom remain the coordinator’s browser task; no such acceptance is inferred from unit tests.

## Coordinator functional browser acceptance

All frontend items 04–10 passed direct Chrome checks using the fixture's actual product renderers. Continuation failure retained 80 rows, C23 selection and scroll; explicit retry appended once and kept its exact Linked content. Absolute range `$C$121:$D$122` navigated to row 121/column 3. Invalid `C121junk` and out-of-bounds `$AG$1` retained the successful range without a guessed read. Switching to Other cleared the old selection.

Expanded comparisons displayed Saved A/B versus Local B/A/C with stable IDs, both human declaration states, recorded colspan 2, contradictory covered text without loss, preserved notes/details, and matching Page 3 labels. Normal and 572px layout were inspected; the latter had document width 572 and no horizontal document overflow. The temporary viewport override was reset. No write endpoint or business store was used. See `browser-acceptance.json` for all ten functional results. Native 200% zoom remains pending Mac unlock.

The disposable fixture needed `flex:none` on its explicitly sized worksheet window to avoid the production flex shorthand giving it zero height in the fixture's auto-height container. No product layout change was made for this fixture issue; worksheet checks were repeated after correction.
