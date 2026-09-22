# R9 settings implementation: 03–10

Only the eight settings items are covered here. Runtime report items 01–02 remain documented in `RUNTIME_RESULTS.md`.

- R9-03: embedded API/catalog/schedule/confidence saves share the existing dialog busy guard and freeze their submitted native controls. Local confidence uses the same form guard. Existing disabled permissions are restored. Duplicate submissions and Close/Escape are blocked during the request.
- R9-04: replacement key plus removal is rejected before sending; the masked input and checkbox remain available for correction. Feedback and comparisons never include key text.
- R9-05: definitive owner “settings/catalog changed” errors expose an explicit read-only comparison. Current saved values or the retained proposal can be chosen against the read revision; either still requires a new explicit Save. Hidden confidence `system3` follows its current owner. Unknown transport errors do not offer rebasing.
- R9-06: a type change removes incompatible comparisons and explains them without inserting Equal. Empty comparisons open the existing disclosure and prevent Save until a human chooses.
- R9-07: owner-compatible mapping uniqueness, regex, lengths, Unicode code-point counts, type/operators and field-count bounds locate the first invalid row. Correcting either member of a duplicate pair clears the stale cross-row native error; no input normalization occurs.
- R9-08: import snapshots the File and immediately resets the picker, retaining the filename on failure and the previous comparison. Another explicit file selection retries; no automatic resend/apply occurs.
- R9-09: an absent saved assignee is a selected, explicitly unavailable roster option. An unrelated schedule edit retains the exact name; owner validation remains authoritative.
- R9-10: reported scheduler state/time/assignee and creation/pending/skipped counts appear separately from configuration timing, with recorded skip reasons. Dispatch completion explicitly does not mean human review completion. Missing counts/report evidence remain unrecorded.

Validation: existing `settings-peer.test.mjs` **20/20**, including 17 new behavioral/boundary regressions. Complete frontend **509/509** before the final cross-row validity correction; the final focused suite covers that correction. Logs: `settings-targeted.log`, `frontend-settings.log`. No backend, real provider, scheduler, business data, or Git changes were performed as validation.

Round-only review diff: `/tmp/ui-r9-settings-net.diff`; before files `/tmp/ui-r9-settings-baseline`. Root owns final browser acceptance, native zoom, overall documents and services.

## Isolated browser fixture

Run `workbench/.venv/bin/python project-support/validation/ui-round9-20260922/settings_fixture.py --port 62854`, then open `http://127.0.0.1:62854/`. Root controls the persistent process. The implementer's random-port health process exited after HTTP and served ES-module syntax checks. This static server rejects every POST. Actual settings component requests are handled only by synthetic page-memory stubs; logs omit any key value. Use dummy keys only.

Before opening a settings dialog, choose the next-save outcome (success, five-second delay, rejection or revision conflict), scheduler report and offline permissions. Reopen menu after Close to change these controls. All four settings classes exercise real save handlers. Standalone confidence is also included. The synthetic ZIP download can be chosen using the native picker; import response sequences support failure/reselection and retention of a previous successful comparison. No ZIP is imported into any workspace.

Check catalog Contains→Yes/no, explicit operator correction and duplicate mappings; API conflicting key intent, pending form freeze and both revision choices; schedule absent assignee and reported dispatch; confidence retained hidden-policy revision and read-only controls. Closing the dialog shows sanitized request history. No actual human-review, schedule-dispatch or provider action should appear there.
