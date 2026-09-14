> Current status, 2026-09-11: user-approved normal startup completed. http://127.0.0.1:62742/ is available; candidate 08 loaded and functional matrix 16/16 scoped PASS. Quantitative quality failures remain. Excel visual inspection stays Pending by user instruction. See workstream `docs/reports/stage-v2-20260911/checkpoint-15.md`; previous startup-approval/unavailable statements below are historical.

# Stage v2 normal-instance load review

Prepared 2026-09-11 00:12 UTC. This document proposes one protected local service start/load; it does not authorize or perform it.

## Observed state

The normal loopback endpoint on port 62742 now refuses connections. The saved service identity still names PID 78585, but that PID no longer exists. The service log is older than this stage and does not establish the exit cause. No stop, kill, restart or normal business decision was sent by this stage. All four separately owned isolated acceptance services remain available.

The earlier normal-entry browser check is historical. Current normal availability is **FAIL** until a fresh successful load is observed. Current source code now exposes a startup-source fingerprint and separate UI fingerprint at `/health`, states that System1/System2 workers are fresh subprocesses, and reports parent source drift. It does not label a filesystem snapshot as proof of all executed paths or quality. The current Handler's health and optional PDF-reference routes passed a temporary read-only HTTP probe. The probe has stopped.

## Concrete proposed operation

1. Verify the saved normal process is still absent and the service lock is available. If another valid normal instance has appeared, inspect and reuse it instead of stopping it.
2. Preserve the five owning databases, current output snapshots, source hashes, configuration and candidate identity. Recheck no queued or running submitted request requires recovery before startup.
3. Start the existing project launcher once, with its existing normal data/configuration and retained browser origin. Load the current workbench parent, including optional PDF-reference routes and runtime evidence. Preserve existing schedule/provider settings without enabling any new schedule or external model.
4. Inspect Overview, System1 history, A, B and the reference extension in the actual browser. Compare business-state/history/source fingerprints, inspect any method-version invalidation and confirm background Excel convergence.
5. On a startup failure, preserve the error and all decisions. Do not restore older business databases over later data. Use the retained candidate code/recovery manifests to diagnose a bounded repair; a data restore requires a verified no-new-writes recovery procedure.

## Prepared evidence and recovery

- [Current preservation audit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity/normal-preservation.json): business tables in all five stores unchanged; browser sessions alone differ. Managed files and Gold hashes are unchanged.
- [Runtime probe](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/runtime-review/runtime-evidence.json): current Handler verified separately from unavailable normal runtime.
- [Five local database backups](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/runtime-review/recovery-manifest.json), with current workbench source/UI copied alongside them. They are local recovery artifacts and are not presentation uploads.
- Workbench: 30 Python checks and 24 frontend checks pass. These checks do not establish normal runtime delivery.

Approval is required because the user's stage v2 objective explicitly retains the protected-service restart boundary. Ordinary local development remains authorized. Native Excel visual acceptance separately awaits Mac unlock.
