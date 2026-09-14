# Provisional B subdivision and workbench checkpoint

Date: 2026-09-10. Decision: **CONTINUE** for bounded engineering implementation; overall Requirement Workstream acceptance remains incomplete.

The [B subdivision contract](../contracts/requirement-subdivision.md) is implemented in the owning workflow database, the unified workbench, counted delivery projection and the generated Excel register. It preserves accepted A source items and distinguishes B subitems from A structural repairs. Peer confirmation of granularity, parent delivery and counting is still pending. The two implemented counting choices are temporary, versioned decisions.

## Verified bounded behavior

- Exact original quotations, Unicode offsets, original parent numbers, separately bound optional original subitem numbers, parent regions and complete shared context are preserved. Unsupported, overlapping, invented or stale spans are rejected atomically.
- Full parent and subitems remain linked; counts use either one parent or the subitems. Tables with original row items cannot also contribute another whole-table requirement count.
- A/context changes suspend affected B decisions. Reaccepting A alone does not revive stale subitems. Policy replacement, explicit removal, restoration, guarded request replay and restart persistence retain old decisions and monotonic subdivision revisions.
- An unfinished B draft suspends B while preserving A acceptance; an A draft cannot be hidden by prior human acceptance. Failed requests remain unfinished.
- The original `CS004` page-20 table, numbered item `2.1.3`, and footnote 7 were used in the existing isolated repair workspace. The source table and both footnote image lines were inspected locally. This is developer-observed engineering evidence, not independently confirmed reference labels.

The browser created two exact criteria spans: the numeric/taxa condition and its original negative qualifier. The complete original `2.1.3` body and footnote remain shared parent context. The browser saved the decision, removed the row from Pending and displayed its history. The persistent database and Excel readback both counted two subitems, with the parent counted zero. This particular subdivision demonstrates the mechanism; its semantic granularity is not independently accepted.

An additional guarded HTTP exercise through the same workbench reopened footnote 7, observed dependent suspension, resolved the explicit reopen, reaccepted A, and verified that B remained pending with `requirement_subdivision_stale`. A new B review changed counting to one parent, repeated the same request without another decision, removed the subdivision, then restored subitem counting at subdivision revision 3. No original source wording was changed by this exercise. All 89 original unit-fact records and Canonical hashes remained intact. The final isolated event cursor was 44, with two counted requirements.

## Failures and corrections

The first browser load exposed an unserved new JavaScript module. Its helpers were moved into the existing served extraction module; the shared entry loaded normally again. The first B submission then exposed the existing HTTP field allowlist. The new fields were explicitly admitted and the isolated service was gracefully reloaded; the rejected submission remained a draft until a successful receipt.

Browser key-based selection produced a whole-field selection during the exercise. Overlap rejection prevented a duplicate subitem. An additional exact-quotation input now supports a unique original occurrence, while repeated quotations require selecting the original occurrence. The successful browser exercise used that exact-quotation path. The automation-key selection behavior is not claimed as verified native mouse-selection behavior.

Inspection of existing draft handling found that prior human acceptance could override the presence of a draft. Explicit draft blockers and A/B draft stages now enforce the target's unfinished-work rule. These are completion-state protections, not new confidence claims.

One test invocation used the System2 import path while invoking Workbench tests and failed to import the owning module. Repeating it with the Workbench environment and import path passed. Earlier failed command/test logs were retained; no independent reference labels were changed.

## Excel and runtime evidence

The final isolated Excel snapshot SHA256 is `cedbec8afcc621aa0d9284a96f39f2c1a77db2f41e7308f7c3d99a41440298cd`. OfficeCLI reported no structure errors. A byte-identical local copy was opened in Microsoft Excel without a repair prompt. `CS004` rows 63–65 showed the complete parent, two generated labels, separate original numbering and count values `0, 1, 1`. It was closed without saving. Long provenance remains available through the formula bar or row expansion; this is not whole-register layout or printing acceptance.

On the existing Apple M4, 16 GiB, macOS 26.6.2, project CPython 3.12.12 environment, six isolated guarded operations took 0.499–1.527 seconds each. These single observations exclude human review time and do not establish a latency percentile or budget. No external API was enabled.

The fresh full System2 suite passed 706 cases with one skip. Subsequent focused subdivision/workbook checks cover the small prefix-number/Level-field extension. Workbench's 26 tests and 17 frontend tests passed. Tests establish these engineering behaviors, not source correctness, B precision/recall, calibrated confidence or final acceptance.

After a verified empty write queue and graceful writer drain, the normal service was backed up and reloaded. Current normal endpoint remains `http://127.0.0.1:62742`, PID 70994, instance `DZjjq5b5A3nYRiSsHH1fcaw8OM1VDVsV`. Live checks retained 87 sources, 30 Pending tasks, 70 stored snapshots, 38 INCLUDE sources and 24 EXCLUDE sources. System2 retained 15,120 actionable units, event 71 and zero published requirements; normal business review decisions were not submitted. All governance, workflow, assessment and Leader tables, all source originals and existing history were unchanged. The generated exports were synchronized.

Local evidence is under `workbench/runtime/requirement-subdivision-20260910/`: the initial SQLite snapshots, `prepare-row.json`, `browser-applied.json`, `excel-first-subdivision.json`, `reversal-and-invalidation.json`, `pending-after-a-recheck.json`, `final-evidence.json`, native copy metadata, validation/test logs, `normal-before-reload.json`, `normal-recovery/` and `normal-final.json`. System2 regression logs are `system2/runtime/subdivision-regression-final.txt` and `subdivision-final-targeted.txt`.

## Remaining acceptance and next useful work

Independent source/relationship labels, real scanned-body and cross-page error-loop evidence, calibration and held-out samples, B precision/recall and granularity labels, representative human workload, and user release thresholds remain missing. One contiguous interval per subitem and prefix-only explicit subitem numbering are the current binding scope. The first multi-format checkpoint is still incomplete. Weekly original-side A sampling and balanced B judgment sampling remain engineering work; actual schedule activation retains its authorization boundary. No model, external material transfer, discovery expansion, source rereview batch or System3 ontology work was enabled.

The next independent engineering checkpoint is durable weekly sampling with explicit shortfalls and unresolved findings in the same workbench. It can proceed while independent reference ownership and collaborator decisions remain pending. It cannot replace held-out acceptance or justify an accuracy percentage.
