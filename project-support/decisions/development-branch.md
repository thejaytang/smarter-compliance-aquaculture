# Product and development branches

Decision updated: 2026-09-25. The user requested exactly two branches, `main` and `developing`. The user chose the same public repository for complete development content and an Example-only product `main`. Earlier publication permissions remain historical; they do not keep full business snapshots on the current `main` tree.

Original decision date: 2026-09-17. The user explicitly selected the maintained development scope after reviewing the size and purpose of historical runtime backups.

- `main`: the shared Windows/macOS colleague product and only the permanent PE002 Example, its fresh seed and saved annotation package. On 2026-09-18, the user authorized promoting Windows commit `d1e8aab` and synchronizing the Mac development checkout. Product integration `2458352` includes those fixes and corrected worker diagnostics. See the [integration checks](../validation/windows-sync-20260918/RESULTS.md).
- `developing`: the product plus complete dated business snapshots, project state, design/decision/plan documents, development tools, tests, verification reports, diagrams and retained reference evidence. Both branches are public.
- Local only: environments, caches, private credentials, login state, retained recovery evidence and machine-specific fixture links. The user subsequently authorized cleanup of obsolete database copies, runtime backups and isolated test outputs on 2026-09-17. The latest verified complete recovery, original migration checkpoint, active data and referenced development fixtures are retained; see the [cleanup record](../validation/local-storage-cleanup-20260917/RESULTS.md).
- Active business files remain local. The complete four-store initial snapshot with originals and human history is versioned under `workbench/initial-data` only on development; normal updates never restore it automatically.
- Publish selected application changes to `main` through a separate checkout. Never merge this development branch wholesale into `main`, because its file policy and records have a different audience.
- Integrate product updates from `main` into `developing` while retaining development files. The old Windows and personal branch names are retired after confirming their tips are ancestors of the retained development version; colleagues use `main` for product updates.

The maintained development branch is now named `developing`. Earlier branch names and their commits remain traceable in historical records and retained Git ancestry.

Historical files retain their names and bytes; current product naming rules still apply to product files. Long archival paths require Git long-path support on Windows. Run `workbench/deployment/check_app_boundary.py --development` for this branch, and the default product check for a main-bound index.
