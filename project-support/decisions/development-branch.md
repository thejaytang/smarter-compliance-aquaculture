# Jay development branch

Decision date: 2026-09-17. The user explicitly selected the maintained development scope after reviewing the size and purpose of historical runtime backups.

- `main`: the shared Windows/macOS colleague product and the already authorized initial business snapshot. On 2026-09-18, the user authorized promoting Windows commit `d1e8aab` and synchronizing the Mac development checkout. Product integration `2458352` includes those fixes and corrected worker diagnostics. See the [integration checks](../validation/windows-sync-20260918/RESULTS.md).
- `developing-only-jay`: the product plus project state, design/decision/plan documents, development tools, tests, verification reports, diagrams and retained reference evidence. Both branches are public.
- Local only: environments, caches, private credentials, login state, retained recovery evidence and machine-specific fixture links. The user subsequently authorized cleanup of obsolete database copies, runtime backups and isolated test outputs on 2026-09-17. The latest verified complete recovery, original migration checkpoint, active data and referenced development fixtures are retained; see the [cleanup record](../validation/local-storage-cleanup-20260917/RESULTS.md).
- Active business files remain local. The complete four-store initial snapshot with originals and human history is already versioned under `workbench/initial-data`; normal updates never restore it automatically.
- Publish selected application changes to `main` through a separate checkout. Never merge this development branch wholesale into `main`, because its file policy and records have a different audience.
- Integrate product updates from `main` into `developing-only-jay` while retaining development files. `developing-win` remains the original Windows handoff reference; colleagues should use `main` for subsequent product updates.

Git does not permit spaces in branch names, so the requested name is represented as `developing-only-jay`. The old `codex/workbench-optimization-20260916` branch was renamed through GitHub's branch-rename operation.

Historical files retain their names and bytes; current product naming rules still apply to product files. Long archival paths require Git long-path support on Windows. Run `workbench/deployment/check_app_boundary.py --development` for this branch, and the default product check for a main-bound index.
