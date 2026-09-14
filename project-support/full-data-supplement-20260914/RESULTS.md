# Full-data upload completion evidence

Verified at 2026-09-14T16:53:34.554741+00:00. The original 05 upload inventory contains 260,759 regular-file/symlink paths, 18,826 directories and 59,160,003,237 regular-file bytes. All original paths are covered by the source tree, priority packages, first-pass packages and recovered-cloud packages. No original path remains missing.

The 766 ZIP archives comprise one consistent database package, five priority data packages, 178 remaining-data packages, 581 cloud-recovery packages and one directories/inventory package. Their combined compressed size is 12,849,799,576 bytes. Every expected asset's GitHub SHA-256 digest and size matched the local upload index. Archive generation performed ZIP CRC checks; file-level manifest sets reconcile with the uploaded path indices. All 8,681 original source paths were confirmed present in the remote source tree. See FINAL-VERIFICATION.json for the verified source commit and exact fields.

Eight SQLite owning-store snapshots were made using online backups while writers were briefly reserved, and each passed integrity_check. The snapshots retain source decisions, review/draft state, history and personal workspaces, with saved records naming Ana Jokic, Daniel Restad and Weijie Tang. The 00 database ZIP is extracted last during restoration to provide consistent database state over raw runtime backups.

## Recovery and interruption record

The first publication omitted ignored runtime data; the user explicitly required all omitted 05 content, including environments/caches, to be published to the public repository. Supplemental assets completed that broader scope. An initial log reconciliation recovered 475 already-uploaded part-033 manifest records by downloading its ZIP, verifying its whole SHA-256/CRC and each recorded file hash, then restoring the missing log rows.

Later GitHub connection failures exhausted upload retries and stopped the earlier coordinator. On final inspection, 140 files were ready locally and 1,539 remaining cloud-only files were historical crop images under system2/outputs/baselines/asc-int-001-full-before-document-profile/crops (23,924,096 bytes). The ready files were uploaded in part 570. A sandboxed native download diagnostic returned FileProvider service error 159; the same authorized request was then issued with approved system access. All remaining images materialized and were uploaded in parts 571-581. This observation does not attribute all earlier download latency to the sandbox.

Original files and human decisions were preserved. No synthetic substitute was used for missing historical images. The final missing-path list is empty. The repository remains public and unarchived; the data release is published. Full file transfer does not establish Windows acceptance, parsing accuracy or production acceptance. Edits made after the captured inventory/database snapshot are separate synchronization work.
