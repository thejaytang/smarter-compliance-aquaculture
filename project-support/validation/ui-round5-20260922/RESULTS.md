# Round 5: Requirement annotation and Groups

Implemented on 2026-09-22. Browser acceptance belongs to the coordinator and is not claimed by this implementation record.

## Scope and boundaries

The product change is limited to `requirements.js`, `requirement-structure.js` and the selected-link reading region in `requirements.css`. Stable source text, code-point spans, session/unit/node IDs, server validation, explicit saving and interpretation approval semantics are unchanged. Source mutations in the fixture affect only its temporary synthetic store.

`loadList()` already called `open(id)` when this round began, with an existing regression requiring initial fourth-pane selection. Round 5 did not introduce that behavior; it is not counted as an improvement.

## Ten implemented items

| Plan item | Implementation and evidence |
| --- | --- |
| R5-01 | Both quantity input binders retain numeric text such as 99; existing `quantityRange()` marks it invalid and blocks preview until corrected. Existing legacy test now asserts retention; structure test covers 99, correction and two-digit 10. |
| R5-02 | `StructureEditor.picks` holds direct-child stable IDs per session/unit/owner. Rendering restores checkboxes/count; grouping derives source-ordered IDs from current children. Successful structure operations prune invalid picks; context changes reset them. |
| R5-03 | Removal records target draft keys but discards them only after a successful preview. Regression covers unrelated invalid quantities, definitive rejection, uncertain transport and success. |
| R5-04 | `readSession()` rejects late responses/errors; `open()` returns explicit success only after the intended session and unit are accepted. Annotation navigation respects that result. Dirty/pending/read-failure/missing-unit/out-of-order regressions preserve the prior valid pair. |
| R5-05 | `reveal()` resolves the exact stable node, expands its ancestor path and focuses either the node or its identified relationship row. Transparent wrappers use their own sole displayed child; missing marks report an error. Legacy field navigation remains. |
| R5-06 | The existing link picker has an associated selected-source reading region containing label, stable ID and full original wording. Binding uses `textContent`, clears on no selection and never links before the explicit action. CSS wraps this region beneath the picker. |
| R5-07 | Combined intake counts distinct source passages and Unicode code points including two-newline separators. Zero/101/100001 selections remain checked in the dialog without a request. Definitive errors retain picks; uncertain results close the picker and retain existing exact-request Retry. |
| R5-08 | Every matching candidate, including the already-open candidate, is read through the authoritative session endpoint. Current candidates open; stale candidates lead to the explicitly requested fresh preview; failed/superseded reads create nothing. |
| R5-09 | A definitively rejected selection action restores its exact owner-relative code-point range only if session/source context is unchanged. It does not run on ordinary redraws or steal later quantity/disclosure focus. Source changes invalidate it; transport uncertainty keeps editing locked for Retry. |
| R5-10 | After a definitive Save & close rejection, navigation finds the existing server-defined empty clause/group, unresolved quantity or one-sided relationship, expands its path and focuses quantity/source controls. The existing message identifies the local label. No new completion prerequisite was added; ordinary Save retains incomplete work. |

## Automated verification

- Full frontend: **442/442 passed**, `frontend-after.log`.
- Requirement/structure frontend suites: **90/90** within the full suite, including 16 new behavior regressions and the corrected clamp expectation.
- Existing Requirement backend suite: **20/20 passed**.
- Existing Group/relationship backend suite: **17/17 passed**.
- Scoped `git diff --check`: passed.
- No backend product code or dependencies were changed.

## Isolated browser fixture

Run from the repository root:

```sh
PYTHONPATH=workbench:workbench/backend/application workbench/.venv/bin/python project-support/validation/ui-round5-20260922/fixture_server.py --port 62848
```

Open `http://127.0.0.1:62848/`. The server uses the actual Requirement owner service and HTTP handler, an in-memory synthetic Material provider and a temporary SQLite database. All six seeded entries and 106 source passages are synthetic. It has no business API proxy, worker or background model call. Its external assets are only the actual local frontend modules/styles.

Fixture-only browser corrections added the missing modal-callback closing parenthesis, the `interpretations.sourceChanged()` callback and explicit body/header layout isolation. The served fixture module was then checked in ESM mode.

For preview Retry, the inner operation request ID, steps and expected revision are retained; the existing nonpersisting outer preview wrapper gets a new request ID. Whole HTTP body byte identity is not claimed.

Startup and HTTP health checks passed on a temporary port, including an actual Save & close and fresh session read: `phase=complete`, saved revision 27, original synthetic source unchanged. The implementer's health-check process exited cleanly and its temporary store was removed. The coordinator starts/manages the browser acceptance instance.

Suggested acceptance sequence:

1. Main entry: check first/third Object fragments, choose MIN–MAX, verify picks/count. Type maximum 99, blur and verify exact 99/error/no request; correct or choose All. Group selected must use first/third stable IDs.
2. Use Collapse Groups then Locate second shackle A and Locate relationship. Verify exact target and retained unrelated closures. Set a read failure or 3s delay before another jump; dirty/pending blocks must retain the existing document/selection.
3. In Exception/Subrequirement picker, compare the two long shared-prefix entries. Read their distinct tails and literal script-looking source before Link. Blank selection clears the reading region.
4. Set definitive rejection before selecting original text in the real header, choose an assignment, and verify the exact source range/tools return. A subsequent corrected field can proceed. Set transport interruption separately and verify only Retry can confirm it.
5. Combine passages: use fixture-only Clear or Select 101 controls inside the native modal. Both invalid selections stay available without an intake request. A valid combination preserves original ordering. Unicode limit is covered by the automated 100001-code-point regression.
6. Open each pending fixture (empty, quantity, relationship), collapse Groups, then Save & close. The real server rejects completion and the editor reveals its repair location. Ordinary Save still accepts an explicitly changed incomplete draft.
7. Inspect request log and saved evidence; fixture source remains unchanged. The separate fourth-pane association display lets the coordinator check that blocked reads do not switch its unit.

## Coordinator functional acceptance

Direct Chrome interactions and the actual isolated Requirement HTTP service passed the ten items' functional checks. See [browser evidence](browser-acceptance.json). Maximum 99 and sibling picks survived invalid input/redraw; dirty or failed navigation retained the document/unit pair. Stable F6 and relationship targets opened only their ancestor path. Both long link tails remained readable as literal text. Empty/101 combined picks retained selection and issued no start request. A definitively rejected fish-emoji annotation restored its exact code-point selection and succeeded on the next explicit action.

Ordinary Save persisted unresolved quantity work at revision 27. After an explicit quantity decision, Save & close and reopening read revision 28, phase complete, with the synthetic original unchanged. Transport Retry retained the exact inner operation ID/steps/version; the existing read-only preview envelope ID is regenerated, so whole HTTP-body equality is not claimed. Reusing the existing main passage performed an authoritative session read without duplication. All three incomplete structure categories were rejected by the real service and revealed their repair location. Automated checks cover removal failure retention, out-of-order/source-stale responses and the larger Unicode bound.

Two test-harness defects were corrected during acceptance: module closing syntax and the missing interpretation sourceChanged callback. A saved response preceded the callback failure; reloading confirmed that revision before continuing. The harness also inherited global body/header flex layout; its isolated container styling was corrected and the normal-width browser view was checked. These are not counted as product improvements. Native 200% zoom remains pending while the Mac is locked; round verification remains pending that layout check.

A 572 px browser viewport check also passed: the exact nested fragment stayed reachable, and focusing Maximum scrolled its existing quantity row so the complete input remained inside the viewport. The override was reset to the normal 1144 px viewport. This is responsive-layout evidence, not native 200% browser zoom. Group selected also sent the two distinct saved IDs for the repeated shackle A fragments, leaving shackle B separate; the resulting preview was explicitly discarded and revision 28 retained.
