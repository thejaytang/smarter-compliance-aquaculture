# Settings and full workspace synchronization

Implemented and activated locally on 2026-09-14 after the parallel UI task completed. Work was developed in `sandbox/`, then 27 explicitly listed files were copied with hash verification. The final source inspection ordering and upload controls from the other task were retained. [Activation manifest](activation-manifest.json) and `before-activation/` retain the previous code; no business database was replaced.

## Delivered behavior

- The sidebar has one Settings entry, displaying the selected reviewer name. Existing reviewer switching remains. Collaboration, Runtime status, Automation and secondary tools open global native dialogs.
- Collaboration exports a full logical ZIP: registered originals deduplicated by SHA-256, source facts, all saved material branches, retained human revisions, proposals and shared synchronization events. Software, environments, caches, previous export ZIPs and local schedule/session settings are excluded. Export does not consume saved work.
- Import validates the archive, original hashes, version ancestry and domain structure before preview. Independent changes merge; overlapping/unrelated changes require an explicit choice. Missing records do not delete local work. Revision guards reject intervening edits. Durable per-record requests resume interrupted writes; an owning-store conflict allows a fresh comparison. Imports are not a single cross-database transaction: already saved records remain visible if a later record needs retry or comparison.
- Each completed synchronization records importer, package sender, exact completion time and per-record contributors. History travels in subsequent snapshots. This is offline exchange, so other installations receive history when they import a later package.
- No separate administrator merge-save step exists in the new flow. Any approved reviewer on a full installation can confirm source work and Archive reviewed material. Archive still saves first and requires the exact saved-content declaration. Received exact-content confirmation preserves its original reviewer/time; stale sources, source problems and unresolved local candidates prevent it from becoming a current completed review. Changed composite content needs renewed confirmation.
- Source records apply through the owning governance database with original protection, revision checks and additive audit. Imported source task/history evidence is retained, not automatically executed; existing local open gates remain. Offline reviewer installations retain their no-business-scheduler boundary.
- Automation contains existing confidence policy controls plus interval, sample size, assignee and timezone. Saving an enabled schedule starts its next interval; it does not immediately dispatch a check. Normal scheduling remains disabled unless the user enables it.

## Verification

- Workbench: 207 tests passed; after the final source-evidence projection change, the 8 source workflow tests and 4 real peer tests passed again.
- Frontend: 238 tests passed, including preservation of save-before-Archive, failed-save blocking and renewed declarations after edits.
- System2: 33 targeted real material/collaboration tests passed. Four peer tests cover two-store full return, original deduplication, named Archive and confirmation provenance, valid re-export, pending-candidate blocking, and simultaneous edits to different blocks with both reviewers preserved.
- System1: 59 source snapshot/collaboration/workflow checks passed on isolated owning stores, including stale rejection, original preservation and exact replay.
- Browser on isolated 59217: reviewer selection, full import/explicit apply, shared history, export, actual download to Downloads, byte-for-byte equality to the server ZIP, and re-import preview showing all records unchanged. No synthetic business write was applied to normal 62742.
- Native global dialog rendering verified at 1280px and 640px. The 640px Automation dialog had 622px client and scroll width, no horizontal overflow. Initial focus after asynchronous load was corrected and verified on Close. Collapsed sidebar retains Collaboration text. Runtime and Automation dialogs were read in the normal service; confidence inputs and the disabled 7-day schedule are present. The normal Material review list also loaded (37 pending records); no material was edited during that read. The isolated service was stopped after acceptance.
- Design detector reported two inherited shell warnings (body overflow and existing shadow). The scoped native dialogs rendered without clipping; no unrelated shell restyling was made.
- Normal 62742 restarted as PID 41735. Health reports an empty parent source-change list. Source governance and System2 workflow database file hashes were identical before and after activation. [Runtime evidence](activation-state.json).

## Size and limits

An export of isolated copies of the then-current normal stores produced **21,722,576 bytes (20.7 MiB)**, **70 deduplicated originals**, **176 logical records**, in **21.42 seconds**. [Measured result](real-package-size.json). This is a measured local snapshot, not a size guarantee as histories and materials grow. Validation retains the existing bounded transport limits: 256 MiB compressed request, 512 MiB uncompressed total, 128 MiB per file and 2,048 ZIP entries.

The verified browser download was a synthetic 2,864-byte one-original package, not a transfer of real business material to another person. Real Windows/colleague acceptance and long-running reliability have not been established by this change. No remote upload, release, automatic schedule enablement or new extraction was performed. Originals, prior revisions and conflicting proposals remain retained.
