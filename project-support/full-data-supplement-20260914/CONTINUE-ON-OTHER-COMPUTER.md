# Restore on the other computer

The full 2026-09-14 inventory backup is COMPLETE. Read RESTORE.txt and FINAL-VERIFICATION.json on https://github.com/thejaytang/smarter-compliance-aquaculture/releases/tag/full-workspace-20260914. Main contains source; the release contains the runtime and historical data packages.

Download and SHA-256 verify all numbered ZIP assets. Restore 01/02/03/04 into a fresh repository root, then restore 00-current-review-databases.zip LAST and handle matching WAL/SHM files exactly as RESTORE.txt specifies. The eight consistent stores include saved records for Ana Jokic, Daniel Restad and Weijie Tang; preserve separate save, draft, review and confirmation states.

Build Windows environments using ENVIRONMENT.md and workbench/deployment/setup_windows.cmd. Check original/Canonical path resolution through existing recovery mapping and test real reopening of saved decisions/drafts. Do not overwrite a running workspace, replace another computer's new review edits, rewrite historical absolute paths blindly or enable business schedules merely for testing. Further edits are separate increments handled with the existing conflict-aware snapshot workflow. Upload completion is not Windows acceptance.
