# Workbench current state

Updated 2026-09-18. This checkout is Jay's `developing-only-jay` development branch. The shared product baseline is `main`, including Windows source commit `d1e8aab` and product integration `2458352`.

## 1. Current result

- Windows startup, URI/storage, background scheduling, persistent component and save-readback improvements are integrated into the common Windows/macOS product. The Mac checkout uses the same product implementation while retaining development documents and tests.
- The user authorized synchronizing `main`, this Mac checkout and GitHub's `developing-only-jay` on 2026-09-18. `developing-win` is retained as the original incoming reference. Colleagues should use `main` for future application updates.
- The normal Mac service is running at http://127.0.0.1:62742/ with the updated source snapshot. Browser checks show 88 sources, 38 material source choices and no archived materials.
- Four business stores, source IDs/history, Requirement/SCD bindings, manual-save semantics and both platform launchers are preserved. No initial seed reimport or database migration was required. The existing initial-data ZIP is unchanged.
- The prior uncommitted Mac idle prototype is historical evidence under [its earlier report](project-support/validation/material-idle-20260917/RESULTS.md); it is no longer an active parallel implementation.

## 2. Verification and recovery

331 Workbench checks, 374 frontend checks and 51 focused System2 checks pass. Two isolated peers passed real source/material/Requirement/interpretation exchange, Git update preservation and restart readback on macOS. Full database integrity and source bindings pass; 137 System1 governance operations and 240 history entries remain. See [current integration evidence](project-support/validation/windows-sync-20260918/RESULTS.md).

The stopped-service recovery package `workbench/runtime/backups/windows-sync-20260918-before` contains 190 data/support files, 709 code files and six retained stores. All four business databases and private configuration, 11 protected files, remained byte-identical through integration and restart checks. Credentials, active workspaces, environments and backups stay local.

Windows performance is reported fixed by the user; this Mac has no native Windows execution environment and did not repeat that acceptance. Real AI/OCR, large-document performance and every four-pane pointer interaction were not rerun. The live-source read checks are distinct from the isolated save/collaboration tests.

## 3. Project and delivery boundaries

- [Branch policy](project-support/decisions/development-branch.md): `main` carries the product and authorized immutable initial business snapshot; `developing-only-jay` adds development materials. Never merge development-only records wholesale into `main`.
- [Environment guide](ENVIRONMENT.md), [user guide](USER_GUIDE.md), [Agent rules](AGENTS.md), [storage contract](workbench/contracts/storage-and-exchange.md).
- [Architecture/naming evidence](project-support/validation/architecture-20260917/naming-implementation/RESULTS.md) and [authorized historical storage cleanup](project-support/validation/local-storage-cleanup-20260917/RESULTS.md) remain retained history. The original migration checkpoint and prior complete recovery remain local.
- Outer workspace directories 01–04 are unchanged. This checkout is under iCloud Desktop; keep code, environments and databases locally downloaded.
