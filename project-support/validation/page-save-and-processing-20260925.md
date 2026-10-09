# Whole-page save and processing completion

Implemented locally on 2026-09-25, `developing` based on `cabd108`. No commit or push. Earlier Windows repairs and unrelated user files remain in place.

## Behavior

- One Materials toolbar Save, including all in-memory Requirement entries and interpretation drafts. Per-pane Save controls are removed; Ctrl/Cmd+S uses the page action. Existing partial-save validation, optimistic versions and exact retry identities remain in use.
- Saves preserve interpretation bindings before saving edited upstream Requirements/content. Upstream changes can make downstream saved work stale; they never rewrite human interpretation text. An incomplete multi-store save reports partial completion and retains remaining edits.
- Panes 2, 3 and 4 have explicit completion controls and a 0–3 material progress count. Completion records are separate System2 collaboration records, so confirming progress does not increment material source revisions or invalidate S/C/D. They include actor/time, content signatures, guarded progress versions and replay receipts. Reopen invalidates downstream declarations.
- Server-side Archive requires all three current confirmations. Successful peer/coordinator archives retain their exact processing snapshot; historical display does not replace it with later progress. Existing archives are not retroactively assigned new declarations. Full snapshots retain the new human history.
- In-app departure offers Save and leave, Continue editing, and Leave without saving. Discard is disabled for three seconds; expiry never saves or navigates. Failed saves remain on the page. Native browser refresh/close retains its standard unsaved warning.

## Validation

- Frontend full suite: 537 passed. A subsequent interpretation presentation check also passed.
- Workbench full suite: 355 passed. Final archive/HTTP/static-route/snapshot group: 30 passed. Final recovery/progress group: 28 passed, including a native Windows recovery path beyond 260 characters.
- Both existing Windows integration scenarios passed: interrupted promotion recovery, preserved author/time and old SCD bindings, real component exchange, two-peer round trip, native launcher, update preservation and restart readback.
- Native Edge, isolated Example: four panes and original HTML loaded without JavaScript exceptions; three completion footers; no per-pane Save; actual content-stage confirmation; incomplete Archive rejected through direct HTTP; three-second discard lock; no automatic departure; Continue editing; whole-page Save; Save and leave then return.
- Development index boundary/naming and whitespace checks passed. Existing missing System2 historical fixtures are unchanged and were not fabricated or hidden.

Local machine evidence is under `workbench/runtime/backups/developing-sync-20260925/page-*`. The browser scenario is [page_workflow_browser_20260925.py](page_workflow_browser_20260925.py). Persistent tests are `workbench/tests/page-workflow.test.mjs`, `test_material_progress.py`, and the extended Requirement/recovery tests.

## Live workspace

The previous service was already offline at restart time. The first recovery attempt exposed ordinary `pathlib.Path` arguments bypassing the existing Windows filesystem wrapper. The backup/verification entry points now normalize those arguments. The incomplete attempt is retained at `workbench/runtime/backups/page-save-20260925-before` and must not be used for restoration.

Verified local recovery: `workbench/runtime/backups/page-save-20260925-verified`, 27 resource files, 718 code files and five stores, including runtime coordination. Stopped live integrity passed. No seed restore, data migration or live human review decision was performed. New service PID 31848 was verified at `http://127.0.0.1:50827/`; workspace identity and the new JavaScript module returned successfully. This PID is a dated observation, not a permanent service identifier.

## Authorized main publication

On 2026-09-25, the user authorized publishing the adjusted product to GitHub main. Commit `a57c94eff407d19bd70467e91eee430436f1e8a9` was pushed normally from `b97764e623994ef0f77719978676b5abb6b82da1`; remote readback confirmed that exact commit. The isolated product checkout contains 30 changed product files and passed product boundary/naming and whitespace checks. Rechecks passed 537 frontend tests and 15 targeted backend tests, the latter importing code from the publication checkout. Development files and full business snapshots were excluded; local working edits and running service were retained.
