# Round 6: compact A/B/C and concepts

Implemented 2026-09-22; independent review and functional browser acceptance passed. Native zoom acceptance is pending.

The round preserves the three existing ABC cards, one Save and one AI Gen. It adds no provider call, automatic citation, automatic approval, global concept panel or history stack. All supporting controls stay inside the existing Set disclosures. Product changes are `check-design.js`, `interpretations.js` and minimal quoted-term focus styling in `four-pane.css`.

The temporary before snapshot is `/tmp/ui-r6-baseline`; the reviewable round-only diff is `/tmp/ui-r6-net.diff`. These exclude all product changes that preceded this round.

| Item | Implemented behavior |
| --- | --- |
| R6-01 | Disclosures use stable rule/concept IDs, including comparison, concept-link, review notes and earlier explanation. Open state is held on the owning page draft and cannot transfer to a different unit. |
| R6-02 | Explicit creation returns the new stable rule/concept destination; only its existing ancestors open and the first relevant input receives focus. |
| R6-03 | Shared concept Name/Type inputs synchronize by exact ID, excluding the active input so its caret remains untouched. Meaning confirmation is invalidated as before. |
| R6-04 | Card citations merge exact id/quote pairs without removing old evidence. Repeated/empty additions do nothing; more than 100 references is rejected before mutation. |
| R6-05 | Concept linking checks availability and existing rule membership. Blank, missing or repeated links do nothing; same-ID reuse across different rules remains available. |
| R6-06 | An unadded citation source/quotation lives on its owning page draft, triggers existing leave protection and survives redraw and Save. Only explicit Add citation records it. Save feedback says the unadded quotation remains unsaved; a quotation-only unchanged Save does not create an empty revision. |
| R6-07 | A `not_stated` field with no definition displays source-absence status; its explanation remains in supporting information and never becomes a set membership predicate. |
| R6-08 | Between/not-between requires exactly two ordered non-boolean endpoints. String order matches Python code-point comparison. Exact raw input and field invalidity survive redraw; ordinary membership lists retain separate semantics. |
| R6-09 | Quoted linked terms route by rule and actual concept IDs into existing concept details, using keyboard-accessible spans and delegated events. Same-label different IDs are all revealed; candidate summaries do not target the human draft. Navigation does not dirty or double-toggle the summary. |
| R6-10 | One temporary Set-local Undo restores the exact deleted tree and pruned concepts/evidence. Another edit, save, source change or unit switch expires it. Undo does not restore a prior approval decision. |

Verification at implementation handoff:

- Existing related suites plus 20 new behavior regressions: **51/51 passed**.
- Full frontend: **462/462 passed**, `frontend-after.log`.
- Scoped `git diff --check`: passed.
- Product modules checked as ESM.
- No backend product changes or new dependencies.

Independent review corrections added tests for native input Tab stops, read-only concept summary focus, unavailable staged source identity, same-unit source-only preferences, quotation-only reload protection and Undo expiration on a changed-source read. A source-only selection remains a page preference, with no dirty/leave restriction or automatic citation. The final removal/Undo regression also checks that invalidated approval success feedback disappears while unrelated generation feedback remains. The final 51 related and 462 full frontend tests passed after this correction; the R7 baseline includes it.

## Browser fixture

```sh
PYTHONPATH=workbench:workbench/backend/application workbench/.venv/bin/python project-support/validation/ui-round6-20260922/fixture_server.py --port 62849
```

Open `http://127.0.0.1:62849/`. The actual Interpretation and Requirement owner services use a temporary SQLite database and three synthetic source blocks. Two Requirement identities demonstrate context isolation. Only explicit Interpretation Save is exposed for writing; no generation/provider route exists. The fixture explicitly isolates body/header layout from application shell styles.

Startup, local assets, ESM fixture syntax, actual HTTP Save and fresh read passed: revision 2 retained the explicit verification edit, source unchanged, provider unavailable. The health-check process exited and removed its temporary store. Browser acceptance remains the coordinator's responsibility.

Suggested checks: inspect both same-label Facility concepts through the quoted term; verify Tab after Name; open Review notes/Link another concept then add a nested rule; change the shared Facility name and inspect Demand; merge source quotations twice; stage an exact quote and Save without Add; edit between to `5\n1` and redraw; remove/Undo nested OR/NOT and confirm old approvals remain cleared; switch units to verify state isolation. The mapped comparison stays inside its existing disclosure. AI Gen remains Not connected.

## Coordinator functional acceptance

Direct Chrome checks passed the ten functional items using the real isolated Interpretation service. [Browser evidence](browser-acceptance.json) captures the saved result and each observation. Quoted same-label concepts opened by exact IDs; all four shared-name inputs synchronized while the other ID stayed unchanged. Existing quotations survived exact-pair citation merge. Staged source/quotation survived redraw, Save and a round-trip through another Requirement, then cleared only on explicit Add. Created inputs retained normal Name/Type Tab order.

A reversed range remained visibly invalid after redraw and Save was blocked; its corrected [1,5] persisted. Deleting an earlier sibling retained the surviving comparison and review disclosures. Removal Undo restored OR/NOT and pruned evidence without restoring approval. Browser review caught an obsolete global approval message after Undo; the narrow feedback correction was verified in the browser. A single concept link disabled repetition and unlinking retained other uses. Source absence remained an explicit state rather than a membership predicate.

Final Save and explicit reopen read revision 5, reviewed=false, no card approvals, original synthetic source unchanged and provider unavailable. Normal 1144 px and narrow 572 px layouts were checked; the viewport override was reset. Native 200% browser zoom remains pending Mac unlock and is not claimed.
