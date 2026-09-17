# Directory and minimal-code follow-up

2026-09-17. The user explicitly scoped the cleanup to the entire `05_Working area of requirements side` folder and requested Ponytail minimal-code optimization. The outer 01–04 folders were untouched.

## Changes

- The visible application root now contains exactly five entry guides, two launchers, `deployment.py`, `project-support` and `workbench`. Git metadata and `.python-version` remain necessary hidden support files.
- `project-support` now contains only `design`, `decisions`, `plans` and `validation`. Fifty existing entries were moved using same-filesystem renames, with destination-collision checks and no content deletion. `moves.json` and the [location mapping](../../../decisions/layout-20260917.md) record every move.
- Duplicate Workbench guides, old Copilot/cloud-workflow files, old examples and old development scripts are retained under `validation/legacy-layout`. Active local tests remain under `workbench/tests`; their retained fixture base path was updated centrally.
- Old npm/pytest/root Python caches and 49 generated cache directories beneath backend, deployment and tests moved into `workbench/runtime/cache`; the obsolete empty saved-packages directory is retained under runtime backups. The launcher routes new Python bytecode to `runtime/cache/python`. The active workspace's databases and originals did not move.
- Removed the redundant environment-rebuild wrapper; tests now call root `deployment.py` directly. Removed application migration fallback into private development archives. Existing older installations still use their original root paths or explicit migration arguments.
- Corrected recovery's shared worker-lock selection for both modern and legacy layouts. Modern backup no longer creates root `system2/runtime/workflow`, locks the actual System1 and material workers, and handles a stale service marker without replacing a filesystem Path with a dictionary.
- The generated source workbook now points to root `USER_GUIDE.md` and both platform launchers. Presentation versions invalidate derived Excel caches; governed source records are untouched.

## Verification

The backup/deployment/product-boundary tests pass (24). Tests include actual competing locks for System1, main System2 and a personal material worker, stale server metadata, no recreation of the old System2 root, and legacy backup/restore compatibility. Environment checks detect all three Python 3.12.12 environments; dependency reconstruction was inspected in dry-run mode without reinstalling anything.

System1 presentation/export tests pass (5), and relocated System2 Gold/native-assembler tests pass (31), bringing the focused total to 60. The first System2 run had two SHA mismatches because retained iCloud PDF placeholders returned empty reads; the existing four manifest inputs were requested locally, without editing originals or expected hashes.

The 704 product files exactly match their staged Git blobs, and the product boundary check passes. The visible root and the four project-support directories match the target. Source records (88), history (240) and source versions (73) match the retained pre-migration database row for row. See `product-check.json` and `preservation.json`.

The normal service was stopped gracefully and restarted through the unified launcher at http://127.0.0.1:62742/ (PID 97302); health returns 200 with no parent-source changes. No browser tabs were reloaded. No Git commit, push or cloud workflow was run. No real Materials edits, source decisions, external AI calls or live database migrations were performed in this follow-up. Native Windows execution remains unverified for the architecture.

## Platform-labelled launchers

The root files are now `Open Workbench (Windows).cmd` and `Open Workbench (macOS).command`. Current guides, the product allowlist, source workbook guidance and local handoff tests use these names; legacy recovery declarations preserve the names of older installations. macOS now prefers the existing Workbench interpreter, fixing a launch failure when Python 3.12 is installed only in the project environment. The renamed macOS launcher passed shell syntax, environment check and startup against the existing service. Five workbook presentation/export tests and the product index check pass. Windows launch was not executed natively.
