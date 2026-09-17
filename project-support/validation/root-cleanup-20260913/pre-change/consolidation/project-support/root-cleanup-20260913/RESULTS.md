# Root ownership correction, 2026-09-13

The user interrupted feature work because auxiliary artifacts had accumulated in the workstream root. The directory policy was not applied consistently: acceptance exports and browser traces were left at the top level, design-skill defaults created root context files, and importing the optional API recreated an empty cwd-relative database. This correction fixes those causes and retains the evidence.

## Relocation

| Previous workstream-root location | Current location |
| --- | --- |
| `PRODUCT.md`, `DESIGN.md` | [Shared design context](../design/) |
| `Excel验收副本-仅供检查.xlsx` | [Retained acceptance copy](retained/excel-acceptance-copy.xlsx) |
| `output/` | [Browser evidence](retained/browser-evidence/) |
| `.playwright-cli/` | [Browser traces and exports](retained/browser-traces/) |
| `runtime/` | [Unused empty root runtime](retained/unused-root-runtime/) |

All **114 files** retain their original bytes. [Relocation manifest](relocation-manifest.json) records old/new paths, sizes and SHA256. A browser console logger continued appending to one log during the move; the strict whole-file comparison detected it and stopped before document rewriting. [Preservation](preservation.json) proves every original byte prefix, including that log, was retained. No log was truncated or overwritten to force equality. Two design documents subsequently had relative links rebased; their exact preceding bytes remain in `pre-change/project-support/design/`. Frozen historical reports/manifests retain old path strings, resolvable through the relocation map; current entry documents point to the new ownership.

The archived root database had zero rows in `jobs`, `job_events` and `sqlite_sequence`, and no open handle was observed before its move. It is preserved, not deleted. Component runtime databases were not moved or restored over. Source files and the parent reference directories were not part of the relocation.

Root README, AGENTS, PROJECT_STATE, shared ENVIRONMENT, platform launchers, component directories, formal docs and project-support remain. ENVIRONMENT stays at root because the existing recovery contract requires it. Root PROJECT_STATE was reduced from 10,092 to about 3,900 bytes; the exact preceding snapshot is retained in [pre-change](pre-change/PROJECT_STATE.md), with current facts linked to owning evidence.

## Recurrence prevention and validation

- AGENTS names the auxiliary-output directory and canonical design paths, and explicitly prevents design skills from recreating root defaults. Cwd-relative capture tools must run from their designated auxiliary workspace.
- Importing the optional System2 API or calling `/health` no longer creates a JobStore. Its default database belongs to `system2/runtime/jobs.sqlite3`, independent of caller cwd; explicit database arguments stay authoritative. Deferred store initialization is locked. Existing explicit-store job history survives reopen.
- **12/12 API/environment/guarded-review tests PASS**, zero failed/skipped: [JUnit](api-junit.xml), [log](api-tests.log). The existing dependency deprecation warning is retained; no dependency was changed. The known unreadable legacy HTML test was not rerun or reported as repaired.
- Recovery declarations now include the relocated shared design context. **13/13 recovery tests PASS**: [log](recovery-tests.log). These targeted results do not constitute a new full product regression or Windows acceptance.
- Original launchers, normal business services, model configuration, schedules and reference documents were not changed. No commit, push, upload or external sending occurred.

## Paused feature work and recovery

The unaccepted confirmation-dialog delta and its test are [parked](../product-readiness-20260912/workflow/review-confirmation/PAUSED.md). Its focused run had one fixture failure; the prior verified `materials.js` was restored exactly. No unaccepted new dialog was loaded into the actual browser.

Recover a relocated artifact using the manifest and its retained bytes. Preserve append-only log additions. For design link changes or code changes, review the exact file delta against `pre-change/` before restoring; do not overwrite later edits or business stores. Restoring the prior API would also restore its import-time root-database defect, so it requires revalidation. [Final checks](final-checks.json) records current preservation, links, code hashes and absent obsolete root paths.
