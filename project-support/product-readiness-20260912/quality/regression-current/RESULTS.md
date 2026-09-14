# 1. Current System2 full regression

**PASS: 1072 passed, 1 skipped, 1 warning; zero failures/errors.** The complete existing System2 test suite collected 1073 tests and finished in 403.36 seconds on 2026-09-13. This replaces no historical result; the earlier 989-test run remains historical. Current extraction quality remains **FAIL** under the separate [reserved-window /4 evidence](../verification-after-v4/RESULTS.md).

## 1.1 Command and environment

The owning environment is `system2/.venv`, as declared by the root `ENVIRONMENT.md` and System2 `pyproject.toml` / `uv.lock`. The guide's test entry is `.venv/bin/pytest`; this equivalent module invocation uses that exact interpreter with the full existing `tests/` tree and no deselections. See [run-start.json](run-start.json) for the exact absolute argument vector, installed dependency versions, environment overrides, Python/platform and every code/test/config/lock hash.

The runner [run.py](run.py) starts pytest from `/private/tmp/smarter-system2-regression-a58dokew`. This isolates the API module's import-time default `runtime/jobs.sqlite3`. It copies the unchanged `config/` into that directory for existing relative-path contract checks, while code/tests use the current source tree. `--basetemp`, `TMPDIR`, pytest cache, and configured library/model cache locations point into the owned temporary root; Hugging Face/Transformers use offline mode. No Gold rebuild script, large PDF run, external benchmark, model installation, business service launch or business review was performed.

The full command, stdout/stderr and JUnit result are preserved in [run-start.json](run-start.json), [pytest.log](pytest.log) and [junit.xml](junit.xml). [run-result.json](run-result.json) records exit code 0, empty changed-file list, unchanged source/tests/config/lockfile hashes and unchanged Gold hashes. The temporary default API database is retained under this run's temporary root. Temporary evidence was not deleted.

## 1.2 Skip, warning and slow-test diagnosis

- One existing test skipped because the optional root `_PS3_副本.pdf` fixture is absent: `tests/integration/test_real_pdf_preflight.py::test_supplied_pdf_is_fully_preflighted`. No fixture was manufactured or removed to alter the result.
- One existing `StarletteDeprecationWarning` concerns `httpx` use in `starlette.testclient`. No dependency was changed.
- Initial collection was slow. A single isolated `--collect-only` diagnostic completed with all 1073 tests in 25.00 seconds; it did not run test bodies or report a collection error. [collection-diagnostic.json](collection-diagnostic.json) preserves its command and full output.
- The existing real `img2table` synthetic-grid test was the slowest at 218.768 seconds and ultimately passed. One import-only diagnostic completed in 4.61 seconds; it does not establish the cause of the slow detection/test path. No test was skipped/retried or changed to obtain PASS.

## 1.3 Candidate binding and acceptance boundary

Parser `/4` SHA256: `3696f3aab5aff829e7247418bd0b22cec1b5f3008c6419ac842f67ff7c38bce2`.

Classifier SHA256: `d4860751208b3bfdf68cc20c36359ff40ba91e784707da4e13b224ba333dc7d0`.

This is current functional, contract, integration and domain regression evidence for System2. It does not establish source-fidelity thresholds, end-to-end Requirement precision/recall, actual browser behavior, mixed-operation stability, Windows acceptance or colleague usability. The separate reserved-window failures remain authoritative for quality. No product changes were made during or after this run by this regression task.
