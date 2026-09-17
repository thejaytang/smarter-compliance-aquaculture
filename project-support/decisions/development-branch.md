# Jay development branch

Decision date: 2026-09-17. The user explicitly selected the maintained development scope after reviewing the size and purpose of historical runtime backups.

- `main`: the colleague product and the already authorized initial business snapshot. It remains at `31c4cf95f1a35a4356d4a045696acf19d771cc67` for this branch-organizing task.
- `developing-only-jay`: the product plus project state, design/decision/plan documents, development tools, tests, verification reports, diagrams and retained reference evidence. Both branches are public.
- Local only: old database copies, historical runtime recovery trees, environments, caches, private credentials, login state, generated test-run directories and machine-specific fixture links. These are not deleted.
- Active business files remain local. The complete four-store initial snapshot with originals and human history is already versioned under `workbench/initial-data`; normal updates never restore it automatically.
- Publish selected application changes to `main` through a separate checkout. Never merge this development branch wholesale into `main`, because its file policy and records have a different audience.

Git does not permit spaces in branch names, so the requested name is represented as `developing-only-jay`. The old `codex/workbench-optimization-20260916` branch was renamed through GitHub's branch-rename operation.

Historical files retain their names and bytes; current product naming rules still apply to product files. Long archival paths require Git long-path support on Windows. Run `workbench/deployment/check_app_boundary.py --development` for this branch, and the default product check for a main-bound index.
