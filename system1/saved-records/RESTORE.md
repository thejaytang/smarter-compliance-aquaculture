# Restore saved System1 human records

This is the selected 2026-09-16 System1 authority checkpoint, revision **8**: 88 sources, 136 operations, 232 history rows, 74 artifact identities and 71 source-version links, plus 4 named human assessment holds. Human decisions remain in their original database context, including imported historical records and program changes that explain later decisions. Do not filter the database by actor name: doing so would discard imported human decisions or break historical context.

- Archive: [governance-20260916-r8.zip](governance-20260916-r8.zip).
- Archive checksum: [SHA-256](governance-20260916-r8.zip.sha256).
- Contents: `governance.sqlite`, its hash-matched `governance-migration-input.xlsx`, `logs/source-assessments.sqlite` with the 4 named human holds and its policy (no machine results/events), and `manifest.json` with per-file hashes, counts and source-version references.
- Required originals remain under the repository's `system1/Data/`; the manifest records their expected SHA-256 values. They are not duplicated into this small archive.

This protects applied System1 human records. Unsubmitted Workbench proposals/drafts, material extraction state, machine-generated assessment results, sessions, caches and environment directories are not included. It is not a complete running-workspace backup or a Workbench Import work package. Exclusion from Git does not remove existing local data.

## New-computer restore

1. Clone this repository including its source files, and run `git lfs pull` for existing LFS-managed artifacts.
2. Rebuild environments using [ENVIRONMENT.md](../../ENVIRONMENT.md). Do not start the coordinator yet.
3. Check the archive SHA-256 against its `.sha256` file. On macOS use `shasum -a 256 system1/saved-records/governance-20260916-r8.zip`; on Windows PowerShell use `Get-FileHash system1/saved-records/governance-20260916-r8.zip -Algorithm SHA256`.
4. In this **fresh clone only**, extract the ZIP contents directly into `system1/Code/runtime/`. Keep the database and immutable workbook together. Do not overwrite an existing database, its WAL files or an existing runtime. Existing installations require a separate deliberate restore/merge decision.
5. The existing `system1/Code/config/config.json` points to `../runtime/governance.sqlite` and `../../Data`. Keep these relative paths. Use the System1 Doctor in ENVIRONMENT.md to check the restored installation, then start the normal launcher and inspect Source review/history.

The source Excel is an output view; never rebuild human decisions by importing the current output workbook. Workbench stores initialize independently. To retain or move Workbench work, export a full workspace ZIP into `workbench/saved-packages/` and use the application import preview on the destination.

## Updating this checkpoint

Use a consistent SQLite backup of the configured governance authority, including committed WAL state, and retain the immutable workbook named by the database's `state.archive`. Verify its hash against `state.import_sha256`, database integrity, foreign keys, table counts and the source-version hashes. Package the snapshot and a new manifest under a new revision/date filename. Publish the required new source files with it. Do not zip a live database file directly or replace a prior archive without an explicit retention decision.

The 2026-09-14 all-runtime release is historical and is not the default restore for this narrower retention policy. This change does not remove that release or clean local runtime.
