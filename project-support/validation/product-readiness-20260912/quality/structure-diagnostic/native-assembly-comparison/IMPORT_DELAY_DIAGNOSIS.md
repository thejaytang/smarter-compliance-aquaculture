# Import-delay metadata diagnosis

Read-only check, 2026-09-13. Scope: the existing failed native comparison, with no parsing retry, native dependency imports, binary-content reads, dependency copies, environment repair, installation or network access.

## Result

The saved stack identifies **native extension loading/initialization**, not a slow PDF structure algorithm. The operating-system cause remains **UNKNOWN**. Current metadata provides no distinguishing evidence for cold file materialization: all 15 regular files inspected have allocated bytes at least their logical size, and none of the 17 inspected paths has `SF_DATALESS`. Package files share `UF_HIDDEN | UF_TRACKED` (32832), including the successful controls; this is not a dataless flag. Flag definitions were read from the installed SDK `sys/stat.h` lines 324 and 359. Directory and symlink zero block counts were excluded from the regular-file comparison.

## Exact targets and controls

| File | Logical bytes | Allocated bytes | Evidence role |
| --- | ---: | ---: | --- |
| `numpy/random/_philox.cpython-312-darwin.so` | 115648 | 118784 | `numpy/random/_pickle.py:4` imports this extension at the saved Docling stack |
| `numpy/random/_pcg64.cpython-312-darwin.so` | 133456 | 135168 | The previous import at line 3 had returned before the observed stack |
| `numpy/random/_generator.cpython-312-darwin.so` | 651136 | 651264 | Earlier import at line 1 had returned |
| `cv2/cv2.abi3.so` | 44350464 | 44351488 | PDFium control stack paused in native `create_module`; its enclosing sample later succeeded |
| `numpy/_core/_multiarray_umath.cpython-312-darwin.so` | 3450392 | 3452928 | Same-environment NumPy core control |
| `pypdfium2_raw/libpdfium.dylib` | 7191008 | 7192576 | Same-environment backend that completed the saved control |

All targeted package files are regular files inside the owning System2 virtual environment, owned by `tang:staff`. `pyvenv.cfg` has `include-system-site-packages = false`; the virtual-environment Python symlink resolves to its configured uv-managed CPython 3.12.12. That base-interpreter arrangement is not evidence of loading another project's packages. No absent target or permission discrepancy was observed.

`bit_generator` has metadata-change time **11:14:12.173 UTC**, and `_philox` **11:14:13.305 UTC** on 2026-09-13, while their modification times remain September 1. These fall inside the Docling attempt, approximately 25 to 27 seconds after the preceding 40.801-second PDFium control completed (run start 11:13:06.319 UTC). Other inspected NumPy random binaries and `cv2` retain September 1 metadata-change times. This is a concrete difference consistent with file-state activity during the stalled import, rather than latency alone. It does **not** identify the operation: there is no before-timeout flag/residency snapshot or actor/change attribution, so materialization, metadata bookkeeping and other causes cannot be separated. It does not demonstrate corruption or prove that this metadata change caused the delay.

## Decision and limits

**STOP this diagnostic.** Do not choose or reject a parsing backend based on this import timeout, and do not repair the environment from these observations. The original comparative quality result remains `UNMEASURED`. Only a future separately justified observation during an actual recurrence could distinguish dependency loading/initialization from transient file access; elapsed time alone cannot identify an OS mechanism.

The current metadata snapshot cannot reconstruct residency at the timeout. Allocated blocks do not prove stall-free reads or mapping. No native stack, dyld event or filesystem IO trace was captured during the delay. Current metadata does not support an assertion that Desktop/cloud storage, spaces in paths, file-provider materialization or the PDF algorithm caused it.

Evidence: [import-file-metadata.json](import-file-metadata.json), the preserved [Docling receipt](run-1/asc-farm-docling-receipt.json), [PDFium receipt](run-1/asc-farm-pdfium-receipt.json) and [comparison report](RESULTS.md). The existing quality README entry remains unchanged because the next action has not changed.
