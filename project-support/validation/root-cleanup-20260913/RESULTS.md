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

At the first cleanup checkpoint, root README, AGENTS, PROJECT_STATE, shared ENVIRONMENT, platform launchers, component directories, formal docs and project-support remained. The subsequent consolidation below supersedes that layout. ENVIRONMENT stays at root because the existing recovery contract requires it. Root PROJECT_STATE was reduced from 10,092 to about 3,900 bytes; the exact preceding snapshot is retained in [pre-change](pre-change/PROJECT_STATE.md), with current facts linked to owning evidence.

## Recurrence prevention and validation

- AGENTS names the auxiliary-output directory and canonical design paths, and explicitly prevents design skills from recreating root defaults. Cwd-relative capture tools must run from their designated auxiliary workspace.
- Importing the optional System2 API or calling `/health` no longer creates a JobStore. Its default database belongs to `system2/runtime/jobs.sqlite3`, independent of caller cwd; explicit database arguments stay authoritative. Deferred store initialization is locked. Existing explicit-store job history survives reopen.
- **12/12 API/environment/guarded-review tests PASS**, zero failed/skipped: [JUnit](api-junit.xml), [log](api-tests.log). The existing dependency deprecation warning is retained; no dependency was changed. The known unreadable legacy HTML test was not rerun or reported as repaired.
- Recovery declarations now include the relocated shared design context. **13/13 recovery tests PASS**: [log](recovery-tests.log). These targeted results do not constitute a new full product regression or Windows acceptance.
- Original launchers, normal business services, model configuration, schedules and reference documents were not changed. No commit, push, upload or external sending occurred.

## Paused feature work and recovery

At the first cleanup checkpoint, the unaccepted confirmation-dialog delta and its test were [parked](../product-readiness-20260912/workflow/review-confirmation/PAUSED.md). Its focused run had one fixture failure; the prior verified `materials.js` was restored exactly. No unaccepted new dialog was loaded into the actual browser at that checkpoint. The next turn resumed the candidate and corrected the test fixture: four focused tests now pass; browser acceptance remains pending.

Recover a relocated artifact using the manifest and its retained bytes. Preserve append-only log additions. For design link changes or code changes, review the exact file delta against `pre-change/` before restoring; do not overwrite later edits or business stores. Restoring the prior API would also restore its import-time root-database defect, so it requires revalidation. [Final checks](final-checks.json) records current preservation, links, code hashes and absent obsolete root paths.

## Follow-up: one shared auxiliary directory and one root launcher

The user identified the remaining duplicate process-document ownership and three root launchers. Root `docs/` contained project-authored design, plan, report and visual artifacts, with no evidence that an OpenAI harness required that location. Its 184 files now live under the matching `project-support/design/`, `plans/`, `reports/` and `visuals/` directories. `Open Workbench.command` is the only daily entry at this Mac workspace root. The two Windows launchers live in `workbench/deployment/`; their project-root resolution, current instructions and recovery/handoff declarations were updated. No runtime, original, Canonical, Gold or human-decision store moved.

[Consolidation manifest](consolidation-manifest.json) records all 186 moves and exact preceding bytes for changed links/code. Historical ZIPs and report content are retained; Markdown navigation is rebased with prior bytes preserved. The Windows checklist identifies older ZIPs as predating this path change. Live validation scripts now use project-support paths rather than recreating root docs.

[Checks](consolidation-checks.json): all relocated original bytes preserved; no missing Markdown links in the changed documents; root has one Open entry and no docs directory. Mac launcher syntax passes. All **13 recovery tests pass** ([log](consolidation-recovery-tests.log)). A temporary **466-entry** code handoff passed the packager's full byte readback and separate checks for relocated launchers, included goal/design files and generated Windows instructions. The temporary bundle was removed after verification; no new distribution or business service was started. **Actual Windows execution remains pending.**

For recovery, use each manifest entry's old/new path and prior-byte backup; reverse only the selected delta after checking for later edits. Do not overwrite newer code or review data. Current ownership is recorded in root AGENTS and README; this report is evidence, not a second current-state source.
