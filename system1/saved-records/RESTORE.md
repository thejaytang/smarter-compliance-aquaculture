# Source records are delivered separately from application updates

The current first-installation seed is the [2026-09-17 source-data release](https://github.com/thejaytang/smarter-compliance-aquaculture/releases/tag/initial-source-data-20260917). It retains source authority revision 13, original files and source history, plus human assessment holds and source-review drafts. Materials test work is excluded.

Use the checked restore command in the [Windows colleague guide](../../workbench/docs/windows-colleague-guide.md). Restore only before first launch into a fresh installation. The script refuses existing source/Workbench databases and validates every file checksum. Normal updates use Git for code and Collaboration for work; they never restore a seed database.

The older revision-8 archive is retained in Git history and locally where previously downloaded. It is superseded for new installations, and no longer tracked in the application tree. Live originals remain under local `system1/Data/`, and generated Excel remains an output view. Do not reconstruct review decisions from an output workbook.
