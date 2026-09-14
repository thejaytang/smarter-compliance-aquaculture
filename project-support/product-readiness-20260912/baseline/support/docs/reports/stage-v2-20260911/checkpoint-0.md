# Stage v2 checkpoint 0: frozen baseline and actual entry

Date: 2026-09-11 Europe/Oslo. Decision: **ADJUST, then CONTINUE to CP1**. Clock remains the original 00:26:35 local start; no new execution window. The goal is incomplete.

## Verified scope and evidence

- Frozen run: `system2/outputs/runs/requirement-acceptance-20260911/stage-v2/`. `sample-manifest.json` binds 91 source/output/configuration files and a consistent copy of the owning review database. No normal decisions were submitted.
- CS004 physical pages 19, 20, 116, 117, 118, 119, 120 and 128: all original rasters inspected and all 275 source regions inventoried, including blank cells, headers and footers. Source-first Agent reference has 243 nonempty units, 12,860 characters, 2,011 words, 125 body-table cells, 20 order claims and 12 title/footnote/continuation claims. Three logical tables retain their full selected page windows. Reference SHA256: `08f27aaa25f6d64c85775e5ff755e59e2f5097a35ce2fef23f52b545ad1fc593`. This is development diagnostic evidence, not independent human acceptance.
- B initial 60 complete source judgments: 40 PDF, 20 HTML across CS001, CS002 and PA001. There are 41 positives, including 11 advisories, and 19 negatives. One original HTML heading was frozen as a separate supplement before tuning, reaching 20 negatives without changing the initial cohort.
- Inventory retains 38 documents: 31 parsed, seven empty-body follow-ups, 15,120 internal extracted units and zero normally published Requirements. Internal units are not assumed to equal distinct human tasks.
- The normal browser retained 45 displayed source review records and source saved/exported revision 1. Historical migration and original/history preservation evidence is reused from the 2026-09-10 functional delivery report. Reuse is not a new full migration.

## Hard main-entry defect and repair

The normal backend returned HTTP 200, but the browser remained at “Loading requirement workspace…”. Its cached server did not serve `/pdf-references.js`; a newly added static import made this optional extension block the entire page. `workbench/ui/extraction.js` now imports the extension on demand and reports a specific unavailable-feature error. The fresh test reproduces the absent-module failure before the fix (`extension-before.txt`), then all 24 frontend checks pass (`workbench-frontend-after.txt`). The actual normal browser reload opened Overview and System1 Review history. The normal service was not restarted. The reference extension itself remains a separately declared unloaded feature.

## First diagnostic observations and next experiment

The unchanged geometric diagnostic reports 378 located character edits / 12,860 characters and 39 / 125 cells with correct grid dimensions. Mapping ambiguities and format artifacts remain explicitly flagged pending adjudication; these are not final acceptance percentages. Major observed causes are missing four-column table structure/cross-column text ownership on pages 117–119, the incorrect 24-by-8 grid on page 120, and 28 blank-form cells containing OCR artifacts on page 128.

The unchanged local B rule, run on source-complete diagnostic A inputs and original context, gives initial-cohort TP 39, FP 1 and FN 2. Precision is 39/40; recall is 39/41; decisive judgments are 40/60. This controlled classifier diagnostic does not claim normal A-to-B release or end-to-end machine acceptance. The supplement is reported separately.

CP1 checks all natural error/finding matches, all sampled unalarmed areas, critical-token occurrences and 12 paired challenges. A bounded current-code rerun uses only the eight frozen PDF pages, to distinguish stale machine output from present parser limitations before selecting at most two interventions. No threshold reduction, source changes, model calls or normal business review.
