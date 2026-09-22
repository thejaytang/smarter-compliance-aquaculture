# Windows compatibility verification

2026-09-22. Native Windows execution is pending. The user confirmed there is no available Windows machine or VM. No cloud workflow has been added or dispatched.

Current macOS evidence: 341 Workbench checks passed; both real integration scenarios passed (populated migration with interrupted promotion recovery, and a two-peer source/material/Requirement/interpretation round trip with update preservation and restart). The integration report explicitly records `platform: darwin` and `native_windows_cmd: false`.

The shared test runner previously discovered only `test_*.mjs`, omitting `*.test.mjs`. Its frontend entry now includes both naming conventions, deduplicated. The corrected entry executed all 395 then-current frontend tests successfully.

`windows-check.yml` is a reviewable, inactive proposal for a manual GitHub-hosted Windows run on this public repository. It requires an exact commit SHA, creates isolated declared environments on a short path, and runs existing tests with synthetic temporary workspaces. No full business seed is restored, real model request made, schedule enabled, or local workstation accessed. The integration suite uses the actual Windows `.cmd` launcher when running natively. This does not replace manual Windows browser/desktop rendering checks.

Root `AGENTS.md` prohibits cloud CI/execution workflows. Installing and dispatching this draft therefore requires an explicit exception from the user. Ordinary pushes would not trigger it; it has only `workflow_dispatch`. No permission exception has yet been received.


2026-09-22 local baseline follow-up: System1 169/169 and System2 1171 passed, with 2 conditional skips (native Windows counters on macOS and absent optional user PDF). The System2 fixtures were repaired to use their package import and current ComponentPool transport. Full logs are retained in the R3 validation directory. This still does not run Windows or activate the proposed cloud workflow.
