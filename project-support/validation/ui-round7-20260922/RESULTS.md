# R7 save, comparison and failure recovery

Product implementation: 10/10. Independent review and coordinator browser acceptance are separate checkpoints. Round-only baseline: `/tmp/ui-r7-baseline`; net diff: `/tmp/ui-r7-net.diff`. The baseline includes all final R6 approval-feedback changes. No business data, backend product code, dependency, provider call, automatic save or adoption was changed.

| Item | Implemented behavior |
|---|---|
| R7-01 | A 409 exposes a conflict-only saved/local comparison. Both ABC field values and complete definitions/concepts/evidence remain visible. Explicit reload or reviewed-local continuation verifies latest revision, context and catalog again; a changed local draft or newer version blocks the choice. Local continuation clears approvals, refreshes context and requires a separate Save. Refresh source alone cannot erase the saved-revision conflict. |
| R7-02 | The exact confirmed AI start request remains on the owning page draft across an uncertain response. Retry reuses its ID and full body; a definitive rejection clears the start. Editing or changed context cannot silently start another run. |
| R7-03 | A failed known-run read exposes Retry status. It reads the same run ID, preserves human fields and rejects another unit or stale-context candidate. |
| R7-04 | Generic merge editors bind their opening preview object, difference and workspace token. Busy, failed or changed comparisons retain typed input and inline feedback. The dialog closes only after resolve explicitly returns success. |
| R7-05 | Task adoption holds one reviewer/item decision across Drawer instances. Opposing controls stay disabled for in-flight, uncertain and acknowledged-pending responses; exact retry preserves choice/digest/request ID. An adopted receipt retires the old controls. Completion updates only the latest matching view after close/reopen. |
| R7-06 | Blank or whitespace numeric edits are rejected and focused before Number conversion. Explicit zero, decimals, null and untouched object fields retain their values. |
| R7-07 | The existing change selector groups returned unresolved IDs separately from selected/suggested/matching results and preserves the chosen stable difference ID during preview redraw. |
| R7-08 | Freeze disables captured selection and summary until the result/failure, identifies the captured scope and uses the existing immutable download link. Unknown outcomes retain the exact request across close/reopen. Successful freeze retires its pending key; a later explicit freeze of the same selection receives a new ID and can capture newer saved revisions. |
| R7-09 | A definitive changed-task rejection exposes Refresh comparison, preserves old evidence on refresh failure and resets confirmation after a fresh read. Unknown decisions reconcile their original request before any refresh or opposite choice. |
| R7-10 | Material and Source merge cards expose the actual edited combined value, and repeated editing starts there. Exact JSON pointer parsing and stable block IDs resolve reordered content; unavailable paths fail with recovery feedback without substituting incoming evidence. |

## Verification

- Existing frontend suites contain 22 added behavior regressions for this round. Relevant suites: **126/126 passed**. Full current frontend: **484/484 passed**, recorded in `frontend-after.log` (includes the coordinator’s parallel runtime test; R7 itself adds 22).
- Scoped whitespace check and ESM module checks pass.
- Closing or replacing a conflict dialog cancels delayed local application; it cannot overwrite the draft or write feedback into a later dialog. The late-view task correction is independently testable through the existing `submission-drawer.test.mjs` regression covering both pending and adopted responses.
- UI and idempotency tests use in-memory endpoint stubs. No paid or external model call occurs.

## Isolated browser fixture

```sh
PYTHONPATH=workbench:workbench/backend/application workbench/.venv/bin/python project-support/validation/ui-round7-20260922/fixture_server.py --port 62850
```

Open `http://127.0.0.1:62850/`. The actual Interpretation owner service uses temporary SQLite and synthetic source/Requirement identities. Save and context read are the only POST routes exposed. Source, material, task, package and AI recovery examples use explicit in-memory stubs in the fixture; they never forward to a business endpoint. Synthetic package clicks download a local text file containing the exact selected synthetic payload. Original synthetic source bytes remain unchanged.

Startup health checked actual context POST, Save and fresh read (revision 2), original unchanged, assets HTTP 200 and the served JavaScript parsed as `.mjs`. The health process exited and removed its temporary database. Native browser acceptance belongs to the coordinator.

Suggested checks:

1. In Interpretation, edit a field, press the synthetic competing-save control, then Save. Compare both versions, cancel, reopen and explicitly continue local, then Save/reopen. The remote verification change and exact local definitions should be distinguishable.
2. Enable synthetic AI, confirm generation, observe lost start response; retry the same request then Retry status. The request log shows one request identity and the same full body. Synthetic AI run approvals cannot be saved to the real owner service and are not part of this fixture's save check.
3. Material comparison has an edited title, unresolved number and suggested/selected/matching rows. Reopen title Edit result, clear the number, use explicit zero and retry a delayed/rejected preview. Use the existing selector to inspect result states.
4. Source comparison repeats an edited source title and retains the correction on another edit.
5. Task controls can simulate delay, unknown response, pending owner receipt and changed task. Check opposing choices, close/reopen recovery, Retry and Refresh comparison plus renewed confirmation.
6. Freeze two synthetic selections with a summary, delay/lose response, close/reopen and retry. The captured scope stays fixed; the link points to the same frozen synthetic file, while a new successful freeze is a new request.

No live adoption, actual model generation, external package transmission or business-source rewriting is claimed.


## Coordinator functional acceptance

All ten functional paths passed direct Chrome checks, with the exact scope recorded in [browser acceptance](browser-acceptance.json). A competing real owner save rejected expected revision 1; comparison cancellation kept the human rule, and explicit local continuation followed by a separate Save/reopen produced revision 3. The synthetic source remained unchanged, all approvals remained pending, and no external model was called.

Lost AI-start and run-status responses reused the same request/body/run while preserving text typed during the failure. Material/Source preview edits retained the actual combined value; rejection kept the correction open. Keyboard-cleared numeric input was rejected with focus retained; explicit zero passed. The outstanding selector kept the chosen stable identity after resolution.

Task expiry required a fresh comparison and renewed confirmation. Unknown and pending decisions locked opposing choices and used an identical request through close/reopen and retry, ending in the actual terminal receipt. Unknown freeze retained captured inputs, retried its original request and showed the immutable package link; a subsequent successful same-selection freeze received a new request ID. The package UI correctly describes a requested download, not proof of file delivery.

Browser acceptance exposed bind-before-showModal initialization in the shared drawer. The task's first draw and the remembered freeze feedback now support that initial state while retaining all later owner/view/open/content guards; both fixes were retested directly. The latest drawer suite passed 12/12. Native 200% browser zoom remains pending Mac unlock, so this round is not yet included in the strict verified count.

Final browser-driven initialization correction: both task comparison and remembered freeze feedback support bind-before-showModal initialization, while later replies still require the same open dialog content. The Drawer suite is **12/12 passed** after this correction; the subsequent combined R7/R8 frontend run is **495/495 passed** in the R8 frontend log.
