# 1. Parser /6 full System2 regression

**FAIL: 1089 passed, 2 failed, 1 skipped; 1092 collected tests.** The complete suite ran once with no deselections or retries. It completed in 343.26 pytest seconds (344.42 seconds including wrapper work). This is regression evidence, not extraction quality, UI, Windows, or frozen mixed-workload acceptance.

## 1.1 Failures and preserved boundaries

- `tests/integration/test_scheme2.py::test_links_notes_and_real_img2table_route`: `TimeoutError: [Errno 60] Operation timed out` while importing `numba/experimental/jitclass/base.py` through the existing img2table dependency. The table result was not reached.
- `tests/integration/test_scheme3.py::test_rest_api_and_release_gate`: `TimeoutError: [Errno 60] Operation timed out` while AnyIO read the existing review page for a FileResponse. The expected HTTP 200 check was not reached.
- The one skip remains the absent optional user `_PS3_副本.pdf` fixture. The warning remains Starlette's `httpx` deprecation.

Both failures are observed local file-read timeouts. Their underlying filesystem cause is not established here; no product defect or transient recovery is inferred from this run. No fix, retry, dependency installation, or test weakening was performed. These failures remain recorded even if a later diagnostic succeeds.

Code, tests, configuration, lockfile and Gold hashes were unchanged throughout the run. Default API import data was created only at the recorded isolated `/private/tmp/` root. The existing full-suite runner was reused with copied configuration, isolated caches and offline model settings. No normal services or business stores were operated.

## 1.2 Evidence

- [run-start.json](run-start.json): command, environment, platform, dependency versions, before hashes and Gold hashes.
- [code-after.json](code-after.json) and [run-result.json](run-result.json): after hashes and preservation comparison.
- [pytest.log](pytest.log), [junit.xml](junit.xml), [summary.json](summary.json): complete output, individual results and exact counts.
- [run.py](run.py): reproducible runner with an explicit parser hash guard; it refuses to overwrite this completed evidence directory.

Parser SHA256: `ae3745c920366edfb70934e540f2fbe745835ff772a16aa540b751713123388e`.

## 1.3 Follow-up diagnosis

[Bounded read diagnostics](file-read-diagnostic/RESULTS.md) reproduced both file-read errors outside pytest and recorded `dataless` file flags. A readable-input route control was itself blocked by a third unavailable dependency. This supports a local environment blocker and does not change the full-suite FAIL or establish product correctness.

## 1.4 Verified dependency recovery

Subsequent [exact locked-wheel recovery](file-read-diagnostic/locked-wheel-recovery-03/RESULTS.md) restored matching original dependency bytes and verified 907/907 files in the three implicated packages. The original img2table test then [passed 1/1 on unchanged relevant source](targeted-recovery-02/result.json). The original full-suite FAIL and the legacy review.html availability failure remain retained; no new full-suite PASS is claimed.
