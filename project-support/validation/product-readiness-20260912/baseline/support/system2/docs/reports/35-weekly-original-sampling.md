# Checkpoint 35: original-side weekly monitoring

Date: 2026-09-10. Decision: **CONTINUE** for local engineering; **ADJUST** for acceptance. The monitoring workflow is integrated into the normal workbench with A/B activation disabled. The overall Requirement Workstream remains incomplete.

## Verified scope

The [sampling contract](../contracts/weekly-original-sampling.md) implements Monday targets 5/20/5, separate A original-side scopes and B positive/negative judgments, durable batch identity, explicit shortfalls, located findings, ordinary repair operations, guarded follow-up and coherent Excel output. System1's existing five-record generator and prior human decisions were preserved; its overview now accounts for unresolved QA follow-ups and samples below five. No new scheduler or external model was enabled.

The real-source development runtime was copied from the prior CS004 pilot, preserving its 89 original review units and paused parser. It used the same immutable 134-page source, SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. The frozen A batch selected 20 original pages from all 134. This draw contained unprocessed pages with no mapped extraction. B had only one eligible judgment; the interface correctly displayed a four-item shortfall and missing negative classification. We did not resample, invent negative decisions or fill the batch with unaccepted guesses.

Actual browser operations established:

- The original page 9 version-history table was visible beside an empty extraction result. Reporting this unfinished original coverage created `coverage:pdf-page:8` in the ordinary content workbench. An attempted premature follow-up was rejected. A visually checked header was entered as a location-bound supplement; the remaining table and footer stayed unresolved. This is an unprocessed-scope finding, not an accuracy measurement on processed pages.
- The sampled B result for 2.1.3 exposed a provisional counting concern: the phrase “that are not pollution indicator species” qualified the first fragment while both fragments counted separately. A developer reported the issue in the isolated workbench, rechecked the original criterion/footnote 7 and changed only the temporary counting policy to one complete parent. Both exact fragments were preserved. The repair remained pending until a separate follow-up. The item then moved to Review history, retaining its initial `INCORRECT` verdict and both inspection records. Peer granularity confirmation remains pending.
- The overview and weekly history retained the B shortfall after that one item closed. No perfect batch result was displayed. All 89 prior original facts remained unchanged; the only new A facts were the original-page coverage item and explicit header supplement.

These are developer integration judgments, not independent human reference labels. Natural/unprocessed findings above and seeded engineering tests below are reported separately. No held-out labels were created or changed.

## Database, recovery and output evidence

Local evidence is retained under `workbench/runtime/weekly-sampling-20260910/`: initial batches, page-9 preview, partial repair, B before/after follow-up, exact database/Excel readback, native copies and latency observations. `final-evidence.json` records event 55, unchanged prior originals, open A finding, completed B follow-up and matching exported histories.

The first Excel copy passed OfficeCLI schema validation and opened in native Excel without repair. Its Weekly checks sheet visibly retained A `finding_open` and B `complete` with the initial `INCORRECT` verdict. Native inspection exposed insufficient height for long evidence notes. Renderer 16 corrects that height. The final copy `/private/tmp/Weekly-Original-Checks-Final.xlsx`, SHA256 `223c84ecaa27788fa42aef2beef7cc217382a849343e6b3c3726a856bdee5543`, passed schema and data checks. **Its final native visual check is pending because the Mac locked before the corrected copy could be opened.** The user was asked to unlock it; no visual success is claimed for that final change.

The normal service was drained, backed up and reloaded on retained port 62742. Recovery evidence in `normal-recovery/` includes all five stores, the immutable System1 migration workbook companion, configuration, both output workbooks and hashes of all 73 original files. `normal-final.json` found no changed table in governance, workflow, assessments, Leader or workbench and no changed original file. Recovery requires draining writers and restoring related stores with their exact companion/configuration; do not discard later decisions by restoring the earlier Excel-authority model.

Actual normal browser reads showed the new weekly entry point, A/B “Activation pending”, no A/B batches, the existing System1 1/5 reviewed state and System3 off. The normal service remains a single shared human entry. No normal review or source decision was submitted in this experiment.

## Regression and operational observations

The complete System2 suite passed 713 tests with one skip before the final focused additions. The later 33-case sampling/subdivision/workbook check and 19-case final sampling/workbook check passed. The two new checks cover concurrent batch creation and frozen-history Excel readback. Workbench passed 28 Python and 17 frontend tests. Regression evidence establishes these mechanics; it does not prove source fidelity, independent classification precision/recall or subdivision semantics.

The seeded cases cover missing original regions, both B strata, shortfalls, source changes, request replay/staleness, premature closure, repair plus follow-up, week boundaries, disabled/read-only paths, concurrent creation, and original HTML/XLSX positions. Existing lock/retry and recovery paths remain in the workbook regression suite. Five local read observations per endpoint are recorded in `read-latency.json`; these are small-sample observations, not p95 acceptance or human-effort measurements. Device: Apple M4, 16 GiB, macOS 26.6.2 arm64; owning Python 3.12.12 / SQLite 3.50.4 environments. No external API was required.

## Remaining work and next useful experiment

1. Finish the corrected Excel native visual inspection after unlock. Verify monitoring workload and source-version follow-up on representative complete PDF/HTML/XLSX material. A full PDF page, 20 HTML positions and 40 cells are proposed inspection units; do not treat these as a validated human-time budget.
2. Keep normal A/B activation disabled until the activation decision is explicit. Legacy machine-only System2 history is retained; its historical measurements are not A/B target evidence.
3. Return to the first source-fidelity checkpoint: independent references, real scan coverage, complex/cross-page table and footnote relationships, validated confidence dimensions and user-set release thresholds remain open. Positive/negative seeded mechanics do not replace an independent real-source B sample.
4. Retain the separate peer decision on B splitting/counting and the independent reference-label owner/held-out split. No missing decision is inferred from silence, developer confirmation or green tests.
