# Workbench current state

Updated 2026-09-17. This is Jay’s `developing-only-jay` development branch. Naming and architecture cleanup is implemented and verified locally. The normal Workbench is running at http://127.0.0.1:62742/ with 88 retained sources.

## 1. Current result

- System1 now owns src/, deployment/ and its rebuilt local environment directly. Explicit Python packages separate application orchestration, shared utilities and System3. The unreferenced old implementation is retained only as local evidence.
- The four-pane workflow, four business databases, source IDs/history, saved-version semantics and platform-labelled launchers are preserved.
- File naming, Windows collisions and staged product/data boundaries are mechanically checked. Root guides and dependency paths reflect the current layout.
- The user explicitly authorized GitHub synchronization of product and sensitive business data on 2026-09-17. The public repository now contains 708 product files and an immutable initial-data ZIP, checksum, manifest and guide. Active data, credentials and environments remain local. Development support is now authorized for this branch only. Publication is confirmed: commit `31c4cf95f1a35a4356d4a045696acf19d771cc67` is on both `main` and `codex/workbench-optimization-20260916`. GitHub returned the same data-package blob hash and 65,565,379-byte size. See [publication evidence](project-support/validation/architecture-20260917/naming-implementation/publication.json).

## 2. Development branch handoff

The user authorized this branch to include code, design documents, tests, validation reports, diagrams and the complete initial business snapshot. Large historical database copies and runtime backups remain local, as explicitly confirmed. `main` remains at `31c4cf95f1a35a4356d4a045696acf19d771cc67`. Both branches are public. Development-only changes are not a whole-branch merge candidate for `main`. Development records are now included under this branch policy; exact publication commits are identified by the Git history and remote branch reference. The previously named development branch has been renamed on GitHub.

## 3. Verification and limitations

326 Workbench checks, 169 System1 checks and 26 frontend checks passed. The 1165 System2 checks have passing coverage across the full run plus corrected focused subprocess checks; two optional checks were skipped. Real migration/failure-retry, two-peer collaboration, Git update/data preservation and initial-package restoration were verified. Initial-package retry, overwrite refusal, exact restored database bytes and real source readback passed.

Native Windows execution of this revised layout remains unverified. No paid/remote model calls were made. This checkout is under iCloud Desktop; keep code, dependencies and databases locally downloaded. Interrupted iCloud-backed validation was rerun successfully after hydration with a temporary local Python cache.

## 4. References

- [Naming and implementation evidence](project-support/validation/architecture-20260917/naming-implementation/RESULTS.md).
- [Initial data and first-install commands](workbench/initial-data/README.md).
- [Environment and recovery](ENVIRONMENT.md), [Agent rules](AGENTS.md), [storage contract](workbench/contracts/storage-and-exchange.md).
- Consistent pre-change recovery: workbench/runtime/backups/naming-structure-20260917-ready. Outer workspace directories 01–04 are unchanged.
