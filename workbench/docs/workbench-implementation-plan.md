# Initial Local Workbench Implementation Plan | Completed Historical Plan

The initial entry-point switch and System1 integration are complete. This document preserves the original implementation sequence, not the current backlog. See [Workbench state](../PROJECT_STATE.md) for current scope, acceptance and next work, and the [user guide](../USER_GUIDE.md) for daily operations. Subsequent changes on 2026-09-07 hid both the Excel Dashboard and operation sheet while retaining them and updating Instructions.

Scope: repair Dashboard helper-column and hard-coded business-count assertions; provide one macOS launcher using the default browser; move daily System1 review to the browser. Excel retains business data and hidden review history without storage migration. Identify unaccepted System2/3 interfaces explicitly.

1. Inspect the starting state: completed. Initially there was interaction design only and a two-level command-menu launcher.
2. Build a narrow System1 adapter for real tasks, source evidence, named decisions, revision checks, receipts, existing locks and backups. Preserve unresolved human issues.
3. Build a separate local workbench with its own dependency-free environment, loopback service, operators, persistent queue, browser UI and single-instance launcher.
4. Validate on isolated data: ratings/selections, unresolved issues, replay, stale pages, Excel locks, restart recovery and invalid access. Use real production data only for read-only UI acceptance.
5. After validation, switch the entry point and hide the Excel operation surface. Archive retired launchers and update the shared contract, guides and state.

Initial implementation constraints: demos do not establish production readiness; do not simulate human decisions on production data; do not run full downloads, parsing or external models.
