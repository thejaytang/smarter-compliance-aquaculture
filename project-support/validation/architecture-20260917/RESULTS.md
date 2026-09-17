# Workbench architecture validation

Date: 2026-09-17. Scope: local implementation of the attached architecture/migration request. No new UI/Requirement semantic design, paid AI call, cloud CI, commit, push, tag or release. The pre-existing publication at HEAD `6149f9901a4a278d0771efd183babf5ca7b0a9cc` is unchanged.

Directory consolidation after this checkpoint is recorded in [the follow-up](directory-followup/RESULTS.md). Historical evidence paths remain as originally recorded; [the location mapping](../../decisions/layout-20260917.md) locates relocated material.

## 1. Implemented layout and data ownership

| Before | Current product or local owner |
| --- | --- |
| `workbench/ui` | HTML under `frontend/pages`, JavaScript under `frontend/components`, CSS/vendor/demo resources under `frontend/assets` |
| `workbench/src/local_workbench` | `backend/application/local_workbench`, `backend/system3`, `backend/shared`; one import path, no duplicated implementations |
| `system1/Code/src`, deployment helpers | `backend/system1/Code/src`, `backend/system1/Code/deployment` |
| `system2/src`, config, UI and dependency declarations | `backend/system2` |
| Root/component installation and launcher code | Root `deployment.py` and two thin platform launchers, with `workbench/deployment` helpers |
| Old tests and development guides | `workbench/tests`, `project-support/validation/legacy-layout`; retained locally, excluded from product index |
| System1 governance/assessment DBs | `workspace/databases/system1.sqlite` |
| Main/personal System2 workflow DBs | `workspace/databases/system2.sqlite`; stable branch table namespaces |
| Workbench Requirement tables | `workspace/databases/system3_requirements.sqlite` |
| Workbench interpretation/history/origin/citation tables | `workspace/databases/system3_scd.sqlite` |
| Actors, sessions, execution receipts and local support | `runtime/state/workbench.sqlite`; not a fifth business authority |
| Private source/AI settings | `runtime/settings`; excluded from business packages |
| Original materials/retained processing attachments | `workspace/sources` |
| Replaceable source-check/Excel markers and locks | `runtime/state/system2/<branch>` |

Detailed table/schema counts and exact source preservation are in `preservation-final.json`. Current maintained contracts are `workbench/contracts/storage-and-exchange.md` and `review-workflow.md`. Historical loose runtime and superseded layouts remain in `runtime/backups/legacy-runtime` and `project-support/validation/legacy-layout`.

The original bundled PDF demo contained real source pages. Those old assets are retained locally in `project-support/validation/legacy-layout/demo-assets`; shipped demonstration PDF/images and associated cases are now wholly synthetic. No actual Materials work was created by this change.

## 2. Evidence and protections

### 2.1 Real workspace preservation

Compared every row with the stopped-service pre-migration snapshots, not only counts:

- 88 sources, 137 operations, 240 source history records.
- 73 source versions, 76 artifacts and 4 assessment holds.
- All 73 original-version files passed their recorded SHA-256 checks.
- Existing real Materials, Requirements and S/C/D were empty before this request; no development example was inserted into them.

The normal service was restarted on `http://127.0.0.1:62742/`. Its health evidence and source count are recorded in `runtime-final.json`. The browser independently displayed 88 sources and the material queue without console errors. Original user tabs were not reloaded or edited.

### 2.2 Versioning, failures and exchange

`architecture-migration-markers.log` exercises populated legacy data through real adapters, injected failure after the first database promotion, retry, replay, exact row/JSON/author/time comparison, original hashes and fixed delivery validation. It proves S/C/D remains bound to split v3 after split v4 and keeps human wording.

`architecture-handoff-latest.log` exercises two independent local workspaces: initial restore, real source/material/Requirement/SCD exchange in both directions, continued editing, explicit merge and service restart. A temporary local Git remote tests a fast-forward product update and verifies local database/original/config fingerprints. It does not contact or update the project's GitHub repository.

Unit/integration coverage additionally checks cross-store rollback, missing origin rejection, branch SQL literal preservation, conflicts, duplicate requests, invalid package/reference handling and stale asynchronous responses. Collaboration snapshots reserve all database writers and use SQLite backup. Incoming snapshots remain read-only evidence; only validated logical records enter owning stores.

### 2.3 Browser journey on macOS

Synthetic CS901 only, via the in-app Chromium browser:

1. Opened the migrated four-pane material; original HTML and saved source text were readable.
2. Switched reviewers and observed shared Requirement data with the existing source-version read-only guard.
3. Opened S/C/D saved against split v3; the v4 split produced a stale-source warning and retained the exact prior human text.
4. Edited Demand logic, tried leaving, saw the strong unsaved-loss dialog, and continued editing without losing the draft.
5. Explicitly refreshed source context, retained the text, manually saved and reloaded. The value persisted.
6. Verified both immutable S/C/D histories: original bound to v3, explicitly saved continuation bound to v4.
7. Used Collaboration → Export for downstream; the UI reported a ready fixed delivery. Package `74107c62-990d-45f9-851c-5b592c62f517` passed full package validation and excludes operational marker files.

`browser-verification.json` records this scope. Both temporary browser tabs and isolated test services were closed. The normal service remains available.

## 3. Regression results

| Area | Result | Evidence |
| --- | --- | --- |
| Workbench backend | 322 passed in the final full run | `architecture-backend-local-cache-final.log` |
| Frontend logic | 371 passed | `architecture-frontend-final.log` |
| System1 | 169 passed | `architecture-system1-final.log` |
| System2 | 1165 passed, 2 skipped; one dependency deprecation warning | `architecture-system2-verified.log` |
| Runtime marker/storage refinement | 14 Workbench tests + 10 System2 workbook tests passed | `architecture-runtime-markers.log`, `architecture-system2-markers.log` |
| Interpretation timeout/stale rerun | 16 passed | `architecture-interpretation-rerun.log` |
| Migration/fault/replay/delivery | Passed | `architecture-migration-markers.log` |
| Real two-workspace exchange/update/restart | Passed on macOS | `architecture-handoff-latest.log` |
| Full recovery restore and four-store inspection | Passed | recovery/restore logs and integrity JSON |

The first post-refinement full backend run had one asynchronous mock-timeout timing failure under concurrent filesystem activity; the interpretation suite and a clean complete 322-test run then passed without a product change. A separate wrongly broad discovery run tried System2 tests in the Workbench interpreter and was discarded; components are tested in their own declared environments. Neither failure is treated as Windows or real-model evidence.

Local reproduction uses Workbench Python with `PYTHONPATH=workbench/backend/application:workbench/tests` and top-level `test_*.py` module loading (do not recursively discover the separate System2 package). Frontend tests run with Node against `workbench/tests/*.mjs`. System2 runs from its owning directory with `PYTHONPATH=src:../application:../../tests .venv/bin/python -m pytest ../../tests/system2 --import-mode=importlib -q`. System1 uses its own locked environment and local tests under `workbench/tests/system1`.

## 4. Recovery and Git boundary

- Original code/database recovery: `recovery/`, including `code-6149f99.tar`, consistent old stores, source/config inventory and manifest.
- Resumable migration evidence: `workbench/runtime/backups/architecture-v1/`, including immutable prepared hashes, old stores and promotion report.
- Full four-store recovery: `four-store-recovery/`, schema `workbench-recovery-v3`, 184 data/support files and 708 matching code files. Six SQLite stores include four business stores and two local support stores. Credentials are excluded.
- Fresh recovery validation: `restored-data/`, restored without rewriting DB bytes, then complete four-store reference/hash inspection. This is an isolated recovery, not an overwrite of normal work.
- 1901 old paths were retired from the Git index with index-only removal. Their local data/development copies remain in place or under the listed local archives. No old Git history was rewritten.
- The product allowlist/index contains 708 files. All 708 current files match their exact staged Git blob hashes, with zero differences (`product-index-verification.json`). Product boundary validation passed. Git connectivity validation passed; the earlier `git diff --cached --check` completed without findings. Final repeated diff checks were stopped after waiting for cloud-only old Git objects; they are not reported as passed. The final staged/current product hash comparison passed independently.

The recovery code inventory is bound to the recovery creation time; subsequent final marker handling changes remain in the current staged product and local validation record. Do not mix arbitrary old/new database files. Restoration and import are distinct operations.

## 5. Remaining verification boundaries

- **Native Windows execution of this new architecture is unverified.** The platform launchers, setup selection and Windows-sensitive paths/locks are covered locally where possible; earlier Windows evidence belongs to the former layout. A Windows machine is still needed for clean install, migration, restart and colleague exchange acceptance.
- macOS component environments were rebuilt from their declared locks and used successfully. This is not a clean-machine installation of every optional OCR/parser/model dependency.
- No real paid/remote AI service was called. AI timeout/error/candidate behavior uses loopback mocks.
- This checkout resides on iCloud Desktop. Some files, including bytecode and Git objects, repeatedly became cloud placeholders during validation. Exact existing files were downloaded locally; no global iCloud setting or project location was changed. Use a nonsynchronized local directory for live SQLite operation, as documented in `ENVIRONMENT.md`.
- Downstream packages describe check designs. They do not contain executed Site Model compliance conclusions.
- Changes remain local/staged. Publication requires the next applicable user milestone authorization.
