# Stage v2 checkpoint 3: persistence, runtime and workload boundaries

2026-09-11. Decision: **ADJUST runtime delivery; CONTINUE report and Canva work.** The original eight-hour clock remains active. No overall completion claim.

## Verified

- All business tables in the five normal stores match their retained recovery baselines. Browser session rows alone changed during read-only navigation. All managed-file and Gold hashes remain unchanged. [Preservation evidence](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity/normal-preservation.json).
- Real original-note repair persisted under `related_content.role = notes` and `Notes / footnotes`; the workbook correctly retained `Not delivered`, unresolved A/B state and prior history. Saved and exported event are both **85**. The synthetic scan fixture's coherent event is **64**, with one available Requirement and zero pending units. [Snapshot readback](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity/loop-export-readback.json). The first readback assertion incorrectly searched for the literal word `footnote`; actual typed role is `notes`. The assertion was corrected to the exact contract and source-bound row; no workbook data was changed.
- The normal frozen inventory maps 15,120 queue items to explicit source scopes. Items include 13,751 content, 1,365 coverage and four structure checks; 1,051 are evidence-only. Exact shared references are recorded without treating them as independent reviewer tasks. Normal human outcomes and time remain unmeasured. Seven empty-body sources remain source follow-ups. [Mapping and workload](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/workload/summary.json).
- The UI now says **Pending review items** and explains overlapping content, table and coverage checks. A fresh actual isolated browser load displayed the corrected overview label. This changes no queue membership or threshold. Workbench Python: 30 pass; frontend: 24 pass. An initial Python test invocation lacked `PYTHONPATH=src`; the corrected project invocation passed without dependency changes.
- [Quantitative report](quantitative-report.md) and its [metrics](metrics.json) separately report natural, seeded, synthetic, performance and unmeasured qualifications. Current totals: 20 scoped PASS, 12 FAIL, six UNMEASURED. These are metric rows, not overall acceptance gates or independent samples.

## New runtime failure and proposed recovery

The normal endpoint on port 62742 now refuses connections and saved PID 78585 no longer exists. No normal stop/restart was issued in this stage; existing logs do not establish the cause. Earlier observed normal navigation is retained as historical, not current availability. Functional scenario 1 is now **FAIL**, while its loaded-build identity remains unmeasured. Four isolated acceptance instances remain available.

The current workbench now provides a source snapshot at parent import, separate current UI fingerprint and explicit parent-source drift in its health response. A short-lived read-only HTTP probe verified the current Handler and optional reference extension, then shut down. Five database backups and current workbench source/UI were prepared. [Concrete startup review](runtime-load-review.md) records exact operations and recovery boundaries. One protected normal start/load was requested asynchronously; do not proceed until authorized. This does not pause unrelated engineering or presentation work.

Native Excel final visual acceptance awaits Mac unlock, already requested. Open XML validation and selected cell/version readback are separate evidence and do not replace Office visual acceptance.

## Next checkpoint

Prepare one native editable Canva presentation from non-confidential engineering summaries; use 25 focused pages if needed to give weekly monitoring and optional API boundaries separate readable pages. Verify every final Canva page and native element editability. In parallel, complete candidate code/config hash binding, startup/recovery instructions and evidence links. If the normal start is authorized, verify the current normal runtime and preserved state before updating its matrix status. No new provider, schedule, source discovery or normal business review is authorized by these steps.
