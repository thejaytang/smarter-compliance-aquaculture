# 1. Bounded three-package recovery

**180 exact-RECORD files restored; 41 dataless files remain without a readable matching project-cache source.** Scope is only numba 0.67.0, AnyIO 4.14.2 and img2table 1.4.0. No package installation, version change, network use or other-project environment reuse occurred.

| Package | RECORD-listed package files | Dataless before batch | Restored and byte-verified | Dataless remaining |
| --- | ---: | ---: | ---: | ---: |
| numba | 808 | 196 | 164 | 32 |
| AnyIO | 44 | 7 | 3 | 4 |
| img2table | 55 | 18 | 13 | 5 |
| Total | 907 | 221 | 180 | 41 |

The 686 files that were not marked dataless at audit time were not exhaustively read or hash-verified. Consequently the table measures recovery coverage, not whole-package readability or environment health. The earlier two restored files are separate and remain retained in `../environment-recovery-01/`.

## 1.1 Verification and recovery point

For each restored file, its readable source in the owning System2 uv cache matched the installed distribution's RECORD hash and size. Verified bytes were staged before mutation. The unreadable target was renamed on the same filesystem into `placeholders/`, retaining original metadata and identity. A new file containing verified bytes was atomically installed at the original path and rehashed. No placeholders were deleted.

[audit.json](audit.json) records the complete bounded inventory and available cache sources; [prepared.json](prepared.json) records source/target hashes; [journal.json](journal.json) records every rename, verified replacement and metadata; [summary.json](summary.json) enumerates all 41 remaining paths. [verified-sources/](verified-sources/) retains the exact restoration bytes. To roll back a file, retain its new readable version separately, then rename the matching placeholder to the exact target in its journal. A rollback would intentionally restore the previous unreadable state.

## 1.2 Remaining blockers

Remaining operational files include numba `core/callconv.py`, `core/rewrites/registry.py` and `np/numpy_support.py`; AnyIO `_backends/_asyncio.py`; and img2table `tables/objects/{cell,line,row,table}.py` plus `tables/processing/borderless_tables/layout/image_elements.py`. Metadata and project-cache audit do not supply usable exact bytes for them. Some other remaining entries are optional/test/header files; none were silently excluded from the inventory.

No further tests were run after this batch: the already-observed failing `img2table/.../row.py` remains unrecovered, and the old review page is still unreadable. Repeating the same suite now would not resolve that missing source. The last complete System2 regression and its subsequent two-test retry remain FAIL.

## 1.3 Retained legacy page audit

The exact former project path `/Users/tang/Desktop/PDF Extraction Product` does not exist. `system2/docs/reports/06-workspace-relocation-20260907.md` states the directory was moved on the same filesystem and no old alias was retained. It records inode/size/mode equivalence, not a content hash for `ui/review.html`.

The current baseline does not contain this page and the Git index has no corresponding tracked file. The 9 examined Windows code archives and 8 earlier stage-v2 candidate archives yielded no usable page copy; malformed archives are preserved in the audit, not rewritten. See [the earlier archive audit](../earlier-candidate-archive-audit.json) and [cache/Windows archive audit](../recovery-source-audit.json). No authoritative exact-hash replacement was established, so review.html remains unchanged.

Next recovery requires verified original bytes for the remaining files, for example restoring local availability from the owning file provider or obtaining exact locked dependency artifacts with their lockfile hashes. Do not infer that a partial uv cache can perform a complete offline reconstruction. Do not manufacture the legacy page merely to make its HTTP assertion pass.
