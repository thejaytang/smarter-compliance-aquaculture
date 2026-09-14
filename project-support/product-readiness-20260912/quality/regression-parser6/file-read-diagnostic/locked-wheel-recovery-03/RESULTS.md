# 1. Exact locked-wheel recovery

**All 41 remaining files restored, followed by 907/907 package-file verification.** numba 0.67.0 (CPython 3.12, macOS arm64), AnyIO 4.14.2 and img2table 1.4.0 exactly match both installed METADATA and the project's uv.lock.

Only the three exact wheels named by uv.lock were downloaded from `files.pythonhosted.org`, the artifact host associated with the lock's `https://pypi.org/simple` registry. Every downloaded wheel matched its complete lockfile SHA256 and byte size. Individual restored entries additionally matched both the installed RECORD and wheel RECORD hashes and sizes. No dependency version changed, package installation occurred, document content was uploaded, model was downloaded or other-project environment was used.

| Package | Files restored this batch | All RECORD-listed package files read and verified afterward |
| --- | ---: | ---: |
| numba | 32 | 808/808 |
| AnyIO | 4 | 44/44 |
| img2table | 5 | 55/55 |
| Total | 41 | 907/907 |

Across the three preserved recovery batches, 223 files were restored (2 + 180 + 41). Prior failed-test evidence remains retained. This result establishes exact readable bytes within these three packages only, excluding dist-info/pyc not listed as package files. It does not establish whole-environment or application health, current full regression PASS, extraction quality, or UI acceptance.

[downloads.json](downloads.json) records exact URLs, lock hashes, actual hashes, versions and per-entry checks. [journal.json](journal.json) records every original placeholder rename, metadata and verified installation. `placeholders/` retains every previous file; `verified-sources/` and the three verified wheels retain recovery bytes. [installed-file-verification.json](installed-file-verification.json) records the complete 907-file check. The scripts retain strict matching and fresh-directory safeguards.

## 1.1 Legacy page remains separate

`system2/ui/review.html` remains the original dataless, unreadable file. This wheel recovery does not contain or replace that page. [legacy-page-provider-metadata.json](legacy-page-provider-metadata.json) records its flags, an empty xattr-name list and unavailable Spotlight metadata. These observations do not identify which file provider owns it.

Apple's current [iCloud file status guidance](https://support.apple.com/en-au/guide/mac-help/mchlc994344b/mac) documents Finder's iCloud Status column and Download Now / Keep Downloaded actions for files actually managed by iCloud Drive. That is a possible supported recovery entry only after the specific file's provider is identified. No Finder download, storage setting, cloud-account change or provider command was executed here. The missing authoritative page cannot be replaced by invented HTML.

## 1.2 Targeted behavior check

After the 907/907 file verification, the unchanged original `test_links_notes_and_real_img2table_route` passed 1/1 with zero skips/errors in a new isolated fixture. [Targeted result](../../targeted-recovery-02/result.json), [JUnit](../../targeted-recovery-02/junit.xml) and [log](../../targeted-recovery-02/pytest.log) preserve the result and unchanged API/table/test source hashes. The process took 45.74 seconds. This fixes the evidence gap for that one observed dependency failure; no full-suite result was overwritten or reclassified, and the separate legacy-page test remains unresolved.
