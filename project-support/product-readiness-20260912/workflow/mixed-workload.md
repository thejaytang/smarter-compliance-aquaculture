# Workload integration evidence

## Local delivery rc1 integration checkpoint

The frozen [local-delivery-rc1 manifest](../baseline/local-delivery-rc1/manifest.json) and its code recovery copy match current product bytes. The [full run](runs/local-delivery-rc1/result.json) retains its original **FAIL**: all groups except `worker_and_save_faults` passed. The failed assertion expected a new ready/partial candidate after worker recovery, but the existing resolver had correctly reused an identical candidate's previous explicit human keep decision. Human blocks and revision remained intact.

Only the auxiliary assertion was corrected. The stricter check verifies identical source, scope, output, completion/warning/error evidence, the prior named explicit resolution, unchanged human blocks and content revision. The [targeted fault rerun](runs/local-delivery-rc1-faults/result.json) and [assertions](runs/local-delivery-rc1-faults/groups.json) pass, including actual worker interruption/recovery, lock contention and failed-save preservation. Product code did not change; the unaffected full-run groups are reused rather than repeated. This combined evidence satisfies the owning-service mixed-workload/recovery portion of C4. Actual browser closeout and loading/handoff remain separately required.

The full run preserved all five fixture sources, 130 immutable revisions and 25 parser artifacts; the targeted run preserved its five sources, 13 revisions and nine artifacts. These are preservation checks, not accuracy scores. [Current frontend regression](archive-inspection/frontend-closeout.log) passes for the same candidate. The earlier Python regression remains a separate scoped checkpoint. No fixed-duration, multi-day, colleague or Windows acceptance is claimed.

## Historical checkpoints


The current harness now includes one additional `machine_order_content_resume` group. Only its targeted owning-service path has been run: [machine-order-target-01](runs/machine-order-target-01/result.json) passed four groups (setup, TS001 initialization, the new group, preservation), with 25 logged operations in 51.24 seconds and no code drift during that run. The new group alone took 18.66 seconds. It exercised only TS001; all 5 fixture source files, 10 immutable revisions and 6 parser artifacts were preserved. This is not a new full or frozen-candidate workload result.

The new group saves human text and an added table row while swapping the text/table order under their preceding headings, explicitly re-extracts, then checks separate v2 order/text/table differences. Saving only the order choice changes unresolved differences from 3 to 2; two repeated comparisons after reopening reuse the same preview and journal. An incomplete permutation is rejected without journal writes. Explicit application then combines original order with retained human text/table edits, replays identically, leaves the master unchanged, and does not create confirmation. Raw candidate blocks/base/source/metadata remain unchanged.

Targeted reproduction, always with a new run name:

```sh
workbench/.venv/bin/python project-support/product-readiness-20260912/workflow/mixed_workload.py --run-name UNIQUE-TARGET --only-group machine_order_content_resume --label 'Targeted order/content resume check' --require-code-stable
```

The result explicitly records `execution_mode` and `exercised_sources`. Full mode adds this group after the original twelve format cycles and before fault/exchange checks. **The expanded full mode has not yet been executed or accepted.** Earlier runs below retain their own harness/code bindings and are not upgraded by this targeted result.

The earlier frozen candidate `frozen-candidate-03` (before versioned order comparison and persistent machine-preview reuse) passed **19/19 service integration groups and 208 explicitly logged actions** in 273.35 seconds. The full frontend suite passed **136/136 tests**, with zero failures or skips. The preceding full Workbench Python suite passed **122/122 tests**; its Python source/test hashes still match the final candidate.

The final expanded product manifest contains 320 files and has SHA256 `032509367ab8b0c8fcf93629a07d3d1943119af6a08ec440dcd5b84915046151`. The harness's narrower 289-file manifest has SHA256 `5406196e8690a30ca90a2bcc2576dd72f500c32df89d6fa907bed87f55a6c2ea`. Both were unchanged across verification. These are explicitly scoped file-manifest identities, not Git commit IDs.

- [Final service result and operation counts](runs/frozen-candidate-03/result.json), [group assertions](runs/frozen-candidate-03/groups.json), [operation log](runs/frozen-candidate-03/operations.jsonl).
- [Final environments, manifest scope, hashes and after-run comparison](frozen-candidate-03-environment.json).
- [Full frontend result and command](frozen-candidate-03-frontend.json), [full frontend output](frozen-candidate-03-frontend.tap).
- [Full Workbench Python result and command](workbench-python-01/result.json), [full Python output](workbench-python-01/unittest.log).

The workload used fresh isolated coordinator, Ana and Daniel stores. It verified all 5 copied/generated source files, 126 immutable historical revisions and 18 parser artifacts without changes. Operations exercised synthetic HTML, XLSX and mixed native/scanned/blank PDF; each completed four save/reopen/compare/adopt cycles. PDF remained explicitly partial. Personal/manual corrections are never scored as automated extraction success.

Coverage includes duplicate extraction/save requests, twelve rejected stale saves with retained conflicts, unchanged preparation identities before/after reopening, explicit main-version adoption and replay, original reading, interrupted-worker resumption, worker-lock contention, injected save failure, two reviewers editing the same block, package replays, explicit conflict resolution, archive retention, a partial spot-check return that stays pending, and three adoption receipts.

This is workload-based service API evidence. It does not establish browser usability, independent extraction accuracy, real colleague acceptance, Windows interoperability or multi-day stability. Elapsed time is descriptive; no idle soak is counted. The harness deliberately does not issue overall product or UI acceptance, including through its `frozen_candidate_stability` field. Evaluate these results alongside the separately recorded browser checks and remaining quality gates.

## Reproduction

Run from the workstream root using a unique name:

```sh
workbench/.venv/bin/python project-support/product-readiness-20260912/workflow/mixed_workload.py --run-name UNIQUE-NAME --label 'Reason for this run' --require-code-stable
```

The final flag rejects code changes during a run. Every invocation refuses to overwrite a previous fixture or report. The builder reads source governance in read-only mode and copies sources into a new isolated root. Existing component adapters and fixture helpers are reused; normal services and business stores are not mutated. Source uses `system1/Code/.venv`, extraction uses `system2/.venv`, and the harness uses `workbench/.venv`.

`operations.jsonl` counts explicitly logged actions; assertion checks can make additional read calls. `groups.json` retains assertion failures. RSS covers the harness process, not total worker memory.

## Retained earlier runs

| Run | Result | Scope and disposition |
| --- | --- | --- |
| [dev-mixed-01](runs/dev-mixed-01/result.json) | FAIL, 18/19 groups | The injected save correctly raised `ValueError`; the harness initially expected `RuntimeError`. All evidence retained. 206 actions, 251.93 seconds, 5 sources, 126 revisions, 17 artifacts; product code changed during development. |
| [dev-mixed-02](runs/dev-mixed-02/result.json) | PASS, 19/19 groups | Corrected error expectation; 208 actions, 253.18 seconds, 5 sources, 126 revisions, 18 artifacts. Parser changed during development, so not frozen-candidate evidence. |
| [frozen-candidate-01](runs/frozen-candidate-01/result.json) | PASS, 19/19 groups | 208 actions, 262.54 seconds, no harness code drift. Superseded by personal/master status clarity, queue refresh and retained extraction-evidence repairs. |
| [frozen-candidate-02](runs/frozen-candidate-02/result.json) | PASS, 19/19 groups | 208 actions, 306.28 seconds, no code drift. Superseded by readable receipt summaries and receipt-only import feedback. |
| [frozen-candidate-03](runs/frozen-candidate-03/result.json) | PASS, 19/19 groups | Final candidate above. 208 actions, 273.35 seconds, no code drift; 5 sources, 126 revisions and 18 artifacts preserved. |

The intervening status/receipt repair checks remain available in [the 131-test frontend output](status-clarity-frontend.tap) and [13 queue/receipt checks](status-clarity-queue.log). They are superseded by the final complete suites, not separate acceptance claims.
