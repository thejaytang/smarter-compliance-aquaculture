# File recovery and GitHub refresh, 2026-09-14

## Recovery result

The user paused publication until anomalous files were recovered, then authorized diagnosis and accelerated recovery. Recovery is complete for the publication inventory: 8,597 regular files passed complete reads with SHA-256 recorded in `file-verification.json`. The 79 original symlinks were inventoried separately. The initial reads recorded 297 timeout or short-read anomalies: 203 in project-support, 70 in System1 and 24 in System2. Every one now passes; see `recovered-anomalies.json`.

The supported cause is iCloud on-demand content availability. An initial metadata pass found 694 dataless files (92,747,325 logical bytes). The sampled baseline manifest was marked `compressed,dataless`, and File Provider reported uploaded=true, downloaded=false, downloadRequested=false and syncPaused=false. Its logical length was 168,882 bytes, but independent cat/pread attempts returned zero bytes. After Apple's `startDownloadingUbiquitousItem(at:)` request, its full 168,882 bytes were readable and valid JSON, with SHA-256 `94d0ea5b5108c8d578733bbe584d889659e6d8278e38b47bf21d66344918417b`.

Ordinary reads also caused some placeholders to arrive. The subsequent explicit batch requested the 408 placeholders still present at its inventory time; all requests were accepted. After downloads, no original publication-inventory file remained dataless. Five manifest sections covering 2,584 archived file entries matched their existing hashes, including previously unavailable files. `historical-hash-checks.json` records these checks.

No original content was rewritten, regenerated or replaced by a guessed copy. Download requests restored local availability through iCloud. No cloud account setting, sync policy or global storage configuration was changed. This evidence does not prove recovery of ignored environments, runtime databases or generated outputs. File-size/hash checks do not establish application or document-extraction quality acceptance.

## Publication scope and packaging

Target: `https://github.com/thejaytang/smarter-compliance-aquaculture`, branch `main`. Live preflight verified owner `thejaytang`, ADMIN permission, PUBLIC visibility and isArchived=false. Contents of the workstream are placed directly at repository root, without the `05` wrapper or parent `01`–`04` directories. Replacement preserves Git history through a normal successor commit.

Existing ignore rules exclude local environments, caches, runtime stores, generated parsing outputs, secrets and local provider settings. The broad build exclusion accidentally omitted required PDF.js runtime files; narrow vendor exceptions now retain ten build assets across current and preserved workspaces. All ten were verified. Eleven environment symlinks and the local coordination lock remain excluded; 68 internal symlinks are made relative in the publication copy for portability. No source symlink was changed.

The 116,250,063-byte historical workbook `system2/System2_Requirement_Register 2.xlsx` uses Git LFS to preserve the full original file beyond GitHub's ordinary 100 MiB limit. Git LFS was used from a checksum-verified temporary binary and configured only in the isolated publication checkout. It was not installed globally.

## External status

Recovery and package verification are complete. Publication is pending the final commit/push and remote verification; this paragraph must be updated after actual external confirmation.

## Sources

- [Apple: download cloud files to a Mac](https://support.apple.com/en-ie/guide/mac-help/mchl1a02d711/mac)
- [Apple: startDownloadingUbiquitousItem(at:)](https://developer.apple.com/documentation/foundation/filemanager/startdownloadingubiquitousitem(at:))
- [GitHub: large file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
