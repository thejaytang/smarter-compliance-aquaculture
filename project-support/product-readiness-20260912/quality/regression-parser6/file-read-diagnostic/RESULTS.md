# 1. Bounded local file-read diagnosis

**Environment blocker confirmed; full regression remains FAIL.** Both original failing inputs remain unreadable in independent direct reads. This is not a passing retry or a product fix.

## 1.1 Evidence and mechanism

1. The original img2table test failed before producing a table, during import of `numba/experimental/jitclass/base.py`. Its metadata marks it `hidden,compressed,dataless`. A separate owning-environment `Path.read_bytes()` process again returned `TimeoutError: [Errno 60] Operation timed out` in about 0.15 seconds.
2. The original REST test requested a real job's `/review/{id}`. Hash-verified API code returns a FileResponse of `static_dir/review.html`. That file is `compressed,dataless`. An independent direct read also returned the same errno60 in about 0.15 seconds. Thus failure occurs below the route's business assertions at file availability, not solely within pytest or its HTTP client.
3. A planned control with a newly created readable temporary HTML input could not reach the route: importing FastAPI failed reading a third `dataless` dependency, `anyio/streams/memory.py`. No control PASS is claimed. This further limits additional in-process diagnostics until the component's dependency files are reliably readable.

The observed immediate cause is unavailable local file bytes for dataless files. The underlying file-provider/OS cause is not established, and no claim is made that all product behavior is correct. Metadata alone was not used to declare failure: it is paired with actual read exceptions.

## 1.2 Scope and preservation

The relevant `api/app.py`, `parsers/table.py`, `test_scheme2.py`, and `test_scheme3.py` were byte-checked against the completed full-run manifest and preserved under `frozen-relevant-code/`. No code was changed for diagnosis. The failed original HTML bytes could not be snapshotted because they were not readable; the frozen source subset is explicitly not a full runnable environment.

Read-probe commands, metadata, durations and complete traces are in [read-probes.json](read-probes.json). The aborted route-control command and output are in [control-invocation.json](control-invocation.json) and [control.log](control.log); [additional-dependency-metadata.txt](additional-dependency-metadata.txt) records the third dataless dependency. Scripts are retained for reproducibility and must use fresh evidence roots before rerunning.

Do not repeatedly rerun the full suite or skip these tests. Restore reliable readability of the owning environment's files and the retained legacy UI from a verified source first, then run the two unchanged targeted tests in isolated data. No package installation, other-project environment reuse, product edits, normal service operations, or attempted file-provider reconfiguration occurred here.

## 1.3 Authorized exact-byte recovery and targeted retest

Two environment files were subsequently restored from this project's own cache after matching their bytes to installed wheel RECORD hashes: numba 0.67.0 `experimental/jitclass/base.py` and AnyIO 4.14.2 `streams/memory.py`. The original unreadable placeholders were renamed on the same filesystem into `environment-recovery-01/placeholders/`; no file was deleted. [journal.json](environment-recovery-01/journal.json) records exact sources, original/retained metadata and verified resulting hashes. No package version, lockfile or product code changed; no network or installation was used.

Only the original two failed tests were rerun in a new isolated directory. [targeted-recovery-01](../targeted-recovery-01/result.json) records **2 failed, 0 skipped in 11.25 pytest seconds** with unchanged relevant API/table/test hashes. The img2table test progressed beyond the recovered numba import and then encountered another dataless file, `img2table/tables/objects/row.py`. The legacy review.html FileResponse read still failed. The original full suite remains FAIL; this partial file recovery does not establish a healthy environment.

The project uv cache contains exact readable copies of the two restored files, but substantial other files in those package archives are themselves dataless. [recovery-source-audit.json](recovery-source-audit.json) and [recovery-summary.json](recovery-summary.json) preserve this distinction. An offline full rebuild is not established as feasible. No authenticated retained `system2/ui/review.html` was found in the current baseline or examined Windows/stage-v2 code archives; malformed historical archives were recorded without rewriting them. Do not replace this page with invented content or declare its test fixed.

To reverse the two dependency restorations, first retain the new readable file under a separate recovery name, then rename its paired preserved placeholder back to the exact target recorded in the journal. This rollback restores the previous unreadable state and is normally unnecessary. Any further recovery should use the same installed-RECORD checks and preservation mechanism.

## 1.4 Coherent bounded package recovery

[Three-package recovery](package-recovery-02/RESULTS.md) subsequently restored 180 additional exact-RECORD files in one preserved batch. Forty-one dataless files remain without readable project-cache sources, including the latest failing img2table row module. No repeat test was run after this batch; full-suite FAIL remains unchanged.

## 1.5 Exact locked-wheel recovery

[Locked-wheel recovery](locked-wheel-recovery-03/RESULTS.md) restored the remaining 41 files from exact official artifacts verified against uv.lock and installed RECORD. A complete subsequent read/hash check passed 907/907 package files across the three implicated packages. The old review.html remains a separate unresolved original-file availability issue; no full-suite PASS is implied.
