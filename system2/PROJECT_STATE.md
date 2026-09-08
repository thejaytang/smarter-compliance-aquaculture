# System2 Project State

## Process-diagram delivery | 2026-09-08

The user rejected the original Canva whiteboard's visual quality: crowded text and crossing connectors made it difficult to read. The current [Canva diagram set](https://www.canva.com/design/DAHUmF-8SUQ/edit) replaces that layout with four fixed pages: format overview, PDF page/region routing, table/cross-page processing, and evidence/Canonical/review. The original whiteboard is retained as a superseded draft.

All four imported pages were inspected in the Canva editor and full-screen view. Canva returned all diagram text as rich text and confirmed four 1920 × 1440 pages. Local checks found no node text overflow or connectors crossing unrelated nodes. This verifies the revised artifact and layout, not user acceptance. The [format-pipeline architecture](docs/architecture/06-format-pipelines-and-human-conversion.md) and [delivery record](docs/reports/15-system2-canva-flowchart.md) link to the current version.

This is a visual/documentation update only. Production review integration and the human-conversion channel remain pending. PDF accuracy work remains deferred; no parser, original source, workbook, Gold or historical baseline was changed.

## Current workflow-design checkpoint | 2026-09-08

Decision: `ADJUST`. The user confirmed three independent internal pipelines after format routing: HTML, XLSX and PDF,
converging at the result index. Other formats require a dedicated human-conversion channel in the existing workbench,
then completeness checks and traceable original/copy relationships before re-entering one of those pipelines. Only INCLUDE sources are processed.

This update covers diagrams, design boundaries and the next plan only. Existing parser branches are unchanged.
Conversion tasks, the converted-copy contract and re-intake are not implemented. Other formats still return unsupported/not implemented through existing code.
No inputs were converted, originals rewritten or business state changed. PDF accuracy remains pending.

See [format pipelines and human conversion](docs/architecture/06-format-pipelines-and-human-conversion.md) for the design and branch diagram.
The next experiment defines conversion tasks, evidence and receipts alongside workbench interfaces, validating traceable intake from original to converted copy.
The content-mapping acceptance below remains valid and does not establish implementation of this new human channel.

## Current HTML / Excel content-completion checkpoint | 2026-09-07

Decision: `CONTINUE`. Content mapping for the five current HTML template families and original-field acceptance for GLOBALG.A.P. XLSX
are complete. The user restricted this round to sources already INCLUDE in System1. Non-INCLUDE sources and
Excel files are neither parsing tasks nor current completion blockers. PDF accuracy remains pending.

- Default `source-records/2` adds ASC Indicators, paragraphs, headings, attachment tables, lists, footnotes,
  non-text evidence and Canonical structure references. The v1 model and explicit projection entry remain; existing Canonical is not migrated.
- Production rerun of 37 INCLUDE HTML sources: the 30 with bodies passed source and mapping checks; all seven previously unsupported
  non-Lovdata projections are now supported. Independent comparison of 86,252 original-text references and 10 frozen windows found zero differences;
  nonempty body residuals were zero. Metadata, controls and navigation remain retained.
- ASC CS001’s 454 records and 1,362 fields matched original HTML, including 14 alternative appendix layouts. All 36
  not-in-use records remain; 13 appendix records without a separate applicability field remain missing. Existing fields for 1,096
  Lovdata clauses are unchanged. Passing coverage does not resolve table geometry or untranscribed-image issues.
- The reference XLSX’s 257 records and 2,313 fields matched the original and v1; the source hash was unchanged. No XLSX is currently effectively
  INCLUDE. The reference remains `local_diagnostic`; the user is not required to include other Excel files.
- Root cause confirmed for seven failed INCLUDE sources: PA011/PA012/PA039/PA041/PA042/PA044/PA058
  contain Lovdata directory snapshots with empty `documentBody`; the page contains a separate full-text link ending in `/*`.
  System1 must obtain complete snapshots for these already-included sources, without repeating eligibility review. This round did not download
  or modify upstream data. It does not establish completed parsing of every INCLUDE full-text source.
- Full regression: **529 passed, 1 skipped**. Independent originals, nesting/ownership/omission negative controls, scope and exact
  run evidence are in [this report](docs/reports/14-nonpdf-content-completion.md). The stable output contract is
  [source-content mapping v2](docs/contracts/source-records-v2.md). Originals, Gold and historical outputs are retained.

Next: system-side queue/evidence/decision/receipt integration with the existing workbench. Retain the seven INCLUDE full-text
acquisition issues. This round did not authorize upstream retrieval or workbench changes. Checkpoints below are historical and do not replace this section.

## Clause mapping and System1 intake checkpoint | 2026-09-07

Decision: `CONTINUE`. GLOBALG.A.P. XLSX and Lovdata HTML have read-only clause-consumption mappings. System2
consumes final source selections through System1’s existing read-only interface. The user assigned source judgments and human eligibility review to System1;
review states here concern parsed text, structure and field ownership only, without repeating source review.

- Added `source-records/1` and independent mapping verification. Source IDs, bodies, Criteria/Level, footnotes and section
  context preserve original locations. Unmapped content enters residuals; audit answers are not treated as standard requirements. Upstream
  Canonical, source verification and projections bind through hashes; mapping cannot write back to Canonical.
- All 257 records and 2,313 original fields in the reference XLSX matched. Mappings passed for 1,096 clauses across 23 historical
  Lovdata sources; seven other HTML sources explicitly lacked that domain projection. The reference XLSX remained `local_diagnostic`,
  without acceptance for registered production Excel intake.
- The normal `--system1` entry uses System1 `effective_selection`, preserves source/bridge revisions
  and configuration/registry hashes, and rejects version changes during intake. Offline `--registry` compatibility remains.
  No source scoring was copied, review writes invoked, downloads performed or cycles scheduled.
- Following the user’s additional request, System1 review-save formula/chart cache synchronization and one cache-only
  update of the current register were completed. Exact evidence belongs to [System1 state](../system1/PROJECT_STATE.md). Intake no longer
  misinterprets missing caches as missing human review.
- After synchronization, production PA001/PA002/PA047 passed source and mapping checks for 88 clauses. All 37 HTML sources
  were eligible; interface and offline-cache manifests matched exactly, and original hashes were checked. All parsed results remain pending review.
- Full regression: **509 passed, 1 skipped**. Source windows, missing/swapped/reordered/stale-version negative controls and current
  run records are in [this acceptance report](docs/reports/13-nonpdf-source-records.md). Gold and historical outputs were unchanged.

Next experiment: complete paragraph/table consumption fields and section/attachment residuals for non-Lovdata templates, then System2’s
pending queue, evidence, versioned decision application and receipts for the existing workbench. Legacy XLS, image text, dynamic HTML
and generic header inference remain incomplete. Seven empty-body sources retain source-completeness issues. PDF accuracy remains pending;
this round performed no new PDF accuracy experiment. Lower checkpoints are historical.

## Excel / HTML structure-verification checkpoint | 2026-09-07

Decision: `CONTINUE`. This round completed non-PDF structural-relation and missed-verification fixes. The user’s order remains Excel/HTML → existing compliance workbench integration → joint PDF accuracy improvement. No new human-review entry was built; PDF accuracy remains pending.

- HTML `html-dom/2.1.0` correctly restores `rowspan=0` within its row group; cross-group and overlapping spans retain explicit issues. Independent verification checks document/table/cell/list confidence and review policies plus the complete issue list. Deleting issues or inflating confidence no longer passes. Original DOM attributes and text are unchanged.
- XLSX `xlsx-ooxml/1.1.0` locates shared strings through actual workbook relationships, rejecting missing, ambiguous or invalid references instead of reading a potentially unrelated fixed-name part. XML comments do not enter string indexes; original evidence remains. Added missing/ambiguous/out-of-range shared-formula and invalid/overlapping merged-range issues. The independent verifier rebuilds them from original XML and checks the issue list.
- Eighteen new failure cases reproduced defects before repair and passed afterward. Full regression: **477 passed, 1 skipped**. After the final table row-group calculation changed to a linear scan, 45 relevant tests passed. Gold and historical outputs were unchanged.
- Of 37 eligible HTML sources, 30 passed machine verification and seven failed with empty original bodies. Ten fixed source windows passed. Body Canonical for all 30 matched the prior round except parser_version. The GLOBALG.A.P. reference XLSX passed checks for 6 sheets / 11,561 cells / 1,838 formulas; its Canonical also matched except parser_version. Input hashes were unchanged.
- The real XLSX remained `local_diagnostic`, ineligible for production intake. All HTML/XLSX results remain pending review; structural verification does not establish Requirement semantic acceptance. Full evidence: [this report](docs/reports/12-nonpdf-structure-integrity.md).

Next experiment remains P0: inspect real GLOBALG.A.P. headers/clause rows and Lovdata clauses/footnotes, then build clause-consumption mappings and coverage checks retaining original locations. Legacy XLS, image transcription, generic business-header inference and production workbench decisions remain incomplete. Seven empty bodies remain source-completeness issues. Do not resume PDF accuracy work on that basis.

## Previous non-PDF checkpoint | 2026-09-07

Decision: `ADJUST`. The user’s latest order is **Excel / HTML parsing → System2 integration with the existing local compliance workbench → joint PDF accuracy improvement**. PDF accuracy is explicitly pending, superseding historical next experiments below. No PDF accuracy experiment occurred in this round. See [completion priorities](docs/plans/03-system2-completion.md).

- Ordinary XLSX moved from a placeholder to `excel-document/1`, retaining original cell values, formulas/caches, sheet/cell locations, merges, hidden state, styles, comments, header parts, relationships and VML evidence. Independent ElementTree verification does not execute formulas, macros or external links.
- Reran all 37 eligible HTML sources: 30 passed machine verification; seven failed with empty original bodies. Ten existing source windows passed; all 37 source hashes were unchanged. Empty-body IDs: PA011/PA012/PA039/PA041/PA042/PA044/PA058. Another 26 ineligible sources were not bypassed.
- Read-only diagnostic of the project’s GLOBALG.A.P. reference XLSX: 6 sheets, 11,561 stored cells and 1,838 formulas. Independent verification passed; openpyxl matched 2,556 texts, 1,586 explicit formulas and 252 shared-formula dependent cells item by item. OfficeCLI source windows were retained. The original hash was unchanged.
- This reference Excel is absent from the current effective System1 Excel list. It uses explicit `local_diagnostic` provenance without fabricated INCLUDE or source/snapshot IDs, and cannot represent production-connected intake. Batch intake still enforces the original selection gate.
- Full regression: **459 passed, 1 skipped**. Evidence and exact input hashes: [non-PDF report](docs/reports/11-nonpdf-priority-pass.md). HTML/XLSX remain `review_required`; Requirement semantics were not extracted. No overall-completion or release-acceptance claim was made.

Next remains P0: complete HTML/XLSX structure-to-clause consumption mappings and real-sample acceptance. Legacy XLS is unimplemented, image text is untranscribed, and seven empty bodies need source-completeness handling. The normal human-review entry is the existing local compliance workbench. System2 owns system-side queues, evidence, versioned decision application and receipts. Existing guarded PDF transactions cover only some actions; HTML/XLSX decisions and a unified queue remain unimplemented. Workbench integration is incomplete. Do not resume PDF accuracy work.

## Previous completion checkpoint | 2026-09-07

Decision: `ADJUST`. The user authorized prioritized work across System2 under [completion priorities](docs/plans/03-system2-completion.md). Older checkpoints remain historical; this authorization superseded the previous pause awaiting user-provided error examples.

- P0 fixes cover failure propagation, false passing for unreadable/reject, text decisions improperly closing structural issues, misaligned span replacement, invalidated semantics after source-text changes and inconsistent secondary-evidence states.
- P1 added guarded PDF review transactions with version/hash checks, request replay, locking, backups and atomic publication; the standalone review page uses them. Legacy interfaces, shared-workbench operator binding, HTML review and structural/supplemental/page decisions remain incomplete.
- P2 restored locked docling-parse 7.15.0 and added `config/pdf-intake-positioned.yaml`. Low-cost pypdf is not accuracy-equivalent. The lockfile was unchanged; the environment added its declared docling extra.
- Interpretation Manual pages 80–82 ended at 100% for 3/3 IDs, body text, page/segment/bbox, critical fields and nonempty critical fields. Strict overall remained 0/3 because shared context, footnote-instruction ownership and reference representation were incomplete. Machine accepted status does not replace these acceptance gaps.
- Audit pages 17–18 produced 13 Requirements identical to historical active22. The current evaluator gives both 12/13 strict exact, so the historical 13/13 claim is not reused. The existing 5.1.6 evaluation discrepancy needs investigation.
- PA001 was eligible and passed new HTML verification for 1,045 nodes and 632 atoms. Both verification types passed while retaining `review_required`. CS003/CS005/PA057 were unselected and still rejected at intake. System1 was not rewritten.
- Final regression: **439 passed, 1 skipped**. Synthetic browser checks, transaction failure tests, real windows and hash evidence belong to [this report](docs/reports/10-system2-priority-pass.md) and [machine record](docs/reports/system2-priority-20260907.json). No new holdout-success or release-acceptance claim was made.

Next experiment at that checkpoint: complete shared context / footnote instruction / reference identity and trace the Audit 5.1.6 evaluation difference, then HTML Requirement consumption interfaces. Overall priorities and later stages are in the execution plan.

## HTML code merge | 2026-09-07

With user authorization, HTML v2 and source-intake code were merged into the saved project, preserving workbench state and history. Regression in the saved project’s own environment: 75 passed, 2 deselected. All 56 merged files matched their hashes; dependencies were completed from the lockfile. The worktree records below are pre-merge validation. Run artifacts remain in the original worktree; exact paths and post-merge checks are in `docs/reports/html-merge-20260907.json`.

## HTML v2 implementation and verification completed | 2026-09-07

Decision: `STOP`; this HTML implementation goal was complete. Defaults: `html-dom/2.0.0` / `html-document/2`, covering five current page families with explicit v1 access retained. Of 37 frozen snapshots, 30 with bodies passed DOM structure and independent original-text verification; seven empty bodies correctly failed. Ten preselected source windows passed; non-PDF contract tests: 75 passed, 2 deselected. Results remain `review_required`, without Requirement semantic acceptance.

Final checks found all source hashes unchanged but an external System1 register change made the 37 selection_status values ineligible; PA001 sampling showed missing formula caches. New intake was blocked and could not bypass the selection gate. Completed run evidence was retained without writing to the saved project or register. Exact versions and details: [completion report](docs/reports/09-html-parser-completion.md). Older checkpoints below do not describe current HTML capability.

## System1 HTML multi-template experiment | 2026-09-07

Decision: `ADJUST`. Twelve INCLUDE/STORED/CURRENT HTML files were explicitly selected by source and structure. Four Lovdata samples produced reviewable structure (105 clauses); seven agency/ASC templates were unsupported, and PA039 failed with empty documentBody. PA010 was PENDING and correctly rejected without reading its snapshot. Successful artifacts did not establish complete full-text structure.

PA047’s many tables exposed repeated section-heading searches. These were reduced to once per section in `lovdata-html/0.1.2`, improving this sample from approximately 43.5 seconds to 1.77 seconds. Canonical for the four supported samples was identical except the version; all review notices remained. Non-PDF/shared-contract regression: `48 passed, 2 deselected`. No PDF parsing or quality verification ran.

New evidence changed priorities: restore Lovdata tables/attachments first, then develop an ASC-specific template from existing CS001/CS002 content; distinguish government content pages from navigation. PA039 needed System1 source-completeness review, without changing selection or downloading again in this round. See `docs/reports/08-html-template-matrix.md`. All changes remained in the worktree; the saved project was not updated.


## Focused non-PDF module regression checkpoint | 2026-09-07

Decision: `ADJUST`. Failure-driven tests for HTML/Excel identification, source lists, CLI and JSON output reproduced and repaired nine defects. Final shared-contract/non-PDF tests: `48 passed, 2 deselected`. No PDF parsing or real PDF quality verification ran.

Four explicitly selected real HTML sources yielded 203 clauses, with zero field differences from the original script and DOM text-location checks passing 203/203. CS001 was an explicit template-mismatch negative control. New completeness notices exposed unstructured section-revision notes and attachment coordinate lists. HTML still needed out-of-section/attachment structure and could not be called full-text complete. Excel remained `not_implemented`; this round repaired type detection and batch exits only.

Parser: `lovdata-html/0.1.1`, retaining previous fields and schema. Defects, evidence and next experiment: `docs/reports/07-nonpdf-module-regression.md`. Results remained worktree-only; the saved project was not updated. The 78-test result in the preceding historical section describes a broader earlier set, not tests repeated this round.


## Independent-worktree HTML intake checkpoint | 2026-09-07

Status: `CONTINUE`. These were new facts for that worktree; the saved project was not yet updated. Migration records and PDF metrics below were imported history and did not mean the worktree contained originals, Gold or historical outputs.

- Read-only import of 198 root-contract/System2 engineering files from the saved project. Origins and per-file SHA-256: `docs/reports/worktree-import-20260907.json`. Old environments, caches, originals, Gold and historical results were not imported.
- Created the worktree’s `system2/.venv` from the lockfile, adding BeautifulSoup/lxml/openpyxl dependencies without using another system’s environment.
- New entry `python -m pdf_extraction.orchestration.source_batch` generates an explicit source-ID list from System1 register fields, preserves human selections and version provenance, checks boundaries/hashes and routes HTML/PDF/Excel independently.
- HTML provides pure template parsing, configuration, Canonical structure and failure results. PA001/PA002 yielded 62 clauses with zero differences from original script fields; DOM text locations passed 62/62. CS001 explicitly failed template matching. HTML Requirement extraction was unimplemented; confidence remained uncalibrated and pending review.
- The PDF adapter retained existing entries/schema and ran on CS003 page 1. Page data, Canonical, five Requirements and two review items existed; schema validation returned zero errors. Mixed table columns and a pdftotext subprocess exception meant source fidelity did not pass. Existing PDF accuracy issues were not repaired in this round.
- Targeted contract/model/structural-export tests: 78 passed. Real samples and differences: `docs/reports/06-source-intake-engineering.md`.
- Excel returned `not_implemented`. The shared index was not a unified fine-grained Canonical schema. Existing review APIs still covered block/span/cell only, without a new workbench, login, Requirement decisions or Excel console.

Next stages and merge boundaries: `docs/plans/02-source-intake-engineering.md`, `docs/reports/source-intake-handoff.json`. Do not blindly overwrite the saved project with the entire imported directory. This round did not commit/push, enable automation, run Full Source Check or fully parse a large PDF.



Documentation entry points (2026-09-08): [README.md](../README.md) and [AGENTS.md](../AGENTS.md) are at the `05_Working area of requirements side/` root, alongside the three systems. This system no longer has a separate entry contract. That README links usage and design guidance. Historical entry locations describe their original state. Integration state is `../PROJECT_STATE.md`; the shared launcher is also at the `05` root.

## Workspace migration checkpoint | 2026-09-07

Decision: `CONTINUE`. The former `PDF Extraction Product` moved intact to `05_Working area of requirements side/system2`, preserving architecture, independent `.venv`, inputs, Gold, historical outputs and caches. All 145,822 migration entries matched inode, size, permissions and symbolic-link target before and after the move. Old paths in 53 environment launch files were subsequently corrected.

At the new path, `PYTHONPATH=src .venv/bin/python -m pytest -q` passed all non-skipped tests, with one skip and one existing Starlette/httpx deprecation warning. This validation did not establish new real-PDF fidelity or release acceptance.

Current integration state is `../PROJECT_STATE.md`. The former desktop path is absent; tools or Codex project entries using it must point here. Migration did not create automatic System1 handoff or define a System3 implementation. The older “no .git” record below describes the pre-migration state. This directory now belongs to the parent project’s working tree; no independent Git repository, commit or push was created.

## Current direction

Workbench design checkpoint (2026-09-07): unified-workbench PDF review interactions and pending integration contracts are in [Workbench design](../workbench/docs/local-workbench-design.md). This round used two pages of historical PDF/Canonical evidence to verify source-page boxes, text correction and the distinct completion scope of integrity review. It changed neither this system’s production code nor historical outputs. Production integration still requires structural, missing-content and page-level decisions, sparse page-index mapping, and unreadable semantics that retain source-fidelity blockers. The frontend demo does not establish completion of these backend fixes.

Build a Requirement-first, highly reliable parser for English/Norwegian legislation, general regulations, standards and audit manuals. The goal is near-complete, faithful and traceable recovery of each Requirement’s direct text, applicability, logic, values, footnotes, associated actions and source evidence, prioritizing silent omissions and silent field errors rather than generic PDF-to-Markdown conversion.

## Current inputs

`data/inputs/` contains four English native-text PDFs:

- `ASC-STD-001-ASC-Farm-Standard-V1.0.1-Aug-2025.pdf`
- `ASC-STD-010-ASC-Salmon-and-Cod-Standard-V1.5-Oct-2025-1.pdf`
- `download-module-691-ASC-Salmon-Audit-Manual_v1.4.pdf`
- `ASC-INT-001-ASC-Farm-Standard-Interpretation-Manual-V1.0-May-2025.pdf`

The ongoing iteration goal is in `docs/goals/04-requirement-convergence-goal.md`. Routine experiments use small risk-selected windows, not whole PDFs. English work may proceed first, but no real Norwegian input is available, so the Norwegian completion gate is unmet.

## Modular engineering checkpoint | 2026-09-01

Status: `CONTINUE`. This modularization round is complete; later migration follows a rolling horizon.

- The project uses a modular monolith, not microservices. Stable module boundaries and dependency directions are in
  `docs/architecture/05-module-boundaries-and-directory-layout.md`; the rolling-horizon migration plan is in
  `docs/plans/01-modular-migration-plan.md`.
- Public entries now exist for `contracts`, `preflight`, `evidence`, `extraction`, `canonical`,
  `verification`, `domains`, `delivery` and `orchestration`.
- The actual `ExtractionPipeline` moved from the root module to `orchestration/pipeline.py`; the old
  `pdf_extraction.pipeline` remains a lazy compatibility facade. Runtime artifact ownership/
  hashes, region normalization, critical-conflict routing, `RunContext/RunPaths` and
  `FinalizationStage` were extracted from the large pipeline, reducing it from 1,605 to 1,299 lines.
- Added `VerificationSettings`, `AtomicAssessment` and a deterministic review router.
  Verification depth controls machine evidence depth only. At every depth, low or missing confidence,
  evidence disagreement or incomplete provenance routes to targeted human
  review. EvidenceSpan production routing is connected; schema 1.5 records thresholds,
  reason codes and evidence-path IDs. Minimum evidence-path requirements fail
  closed. Unified calibration for Requirement fields and table cells remains incomplete.
- The top-level package, orchestration facade, schema validator and ontology delivery now load on demand,
  so lightweight contracts do not initialize the full parsing and ontology dependencies.
- Root `.venv` was rebuilt from `uv.lock` with `dev` and `table-fallbacks`. The old dataless
  environment `.venv.dataless-backup-20260901` was deleted after user confirmation.
- Targeted regression: `34 passed`; new machine-depth/atomic-routing regression: `10 passed`.
  The first full run returned `337 passed, 1 skipped, 1 failed`; the only failure was the declared
  `img2table` extra missing from the rebuilt environment. Installing it made that case pass. Final full results are recorded in
  `docs/reports/05-模块化重构实施记录.md`: `340 passed, 1 skipped`.
- The fixed one-page pytest sample passed through the production pipeline, generating schema 1.5 Canonical and
  `verification-report.json`, with three atomic assessments, automatic coverage 1.0,
  0 review、0 Canonical validation errors。
- Source-tree fingerprint at this checkpoint:
  `7b0af6ce9ad83a16a89121dd399b6cb15af9b9978c765ed491aead92e24f27d2`. This hash
  identifies source-code state only and does not establish fidelity acceptance on real target PDFs.
- At this checkpoint, the directory had no `.git` metadata, so `git status` and version-control rollback were unavailable. This round did not change
  `data/inputs/`, Gold annotations/manifests, `outputs/baselines/` or historical run artifacts.
- Next checkpoint: establish before/after artifact comparison on one fixed small real-PDF window,
  then move page extraction, assembly and reconciliation into explicit runners in stages. Extend the same
  atomic policy to Requirement fields and table cells. An independent verifier must not be presented as complete
  before it has a real independent evidence path.

## Directory-ownership consolidation checkpoint | 2026-09-01

Status: `CONTINUE`. Migration of loosely coupled directories is complete.

- Canonical implementations of Requirement and Regulatory IR moved into `domains/`.
- Exporters, ontology and the derived-artifact writer moved into `delivery/`.
- Old `requirements/`, `regulatory_ir/`, `export/`, `ontology/` and `derived.py`
  retain compatibility facades only, without parallel business implementations.
- Tests are organized under `contracts/`, `unit/`, `integration/`, `domains/requirements/` and
  `support/`. Test-file nesting no longer implicitly determines the project root.
- The namespace-layout contract prevents new business files appearing in compatibility directories and prevents internal implementations
  from depending again on old facades.
- Domain/delivery import-identity smoke checks passed; migration-focused regression: `312 passed`; contract
  tests: `12 passed`; full regression: `343 passed, 1 skipped`. Full evidence:
  `docs/reports/06-目录职责收敛实施记录.md`.
- Source-code fingerprint at this checkpoint:
  `c21bf802011608877772a0661d10bfce35b452dfb56838fddef392a3b0cab591`.
- Input PDFs, Gold annotations/manifests, historical baselines and run artifacts were neither changed nor moved.
- The next directory migration is limited to page-extraction routing/layout/parsers/assemble/reconcile.
  Establish fixed real-PDF artifact comparison first; do not mix it into this loosely coupled migration round.

## Historical Requirement convergence checkpoints

Status at these checkpoints: `ADJUST`.

- Canonical Requirement schema, four native-template assemblers, inexpensive full-document template profiles and Requirement-derived Regulatory IR are established.
- Round 1’s 25 cross-structure samples improved inventory recall from `12%` to `100%`.
- Farm Standard pages 64–65 headerless continuation improved from `3/10` to `10/10`. `Indicator applicability`, superscript footnote markers and list glyphs were separated from semantic normative text while retaining original evidence.
- The new untouched Salmon/Cod pages 27–28 holdout recovered `6/6` IDs on its first blind test, demonstrating cross-document generalization of continuation inventory recovery. Complete fields, provenance and accepted coverage still failed the completion gate; the sample permanently became active.
- Before scoring, Interpretation Manual pages 103–106 exposed inline cross-references mistaken for IDs. Document-learned anchor geometry/style and row-pair evidence fixed this: duplicate `2.6.13` disappeared, recovering `4/4` IDs and `100%` direct-text/page provenance.
- Round 4’s untouched holdout was Audit Manual pages 11–12. First blind test: `6/7`, precision `100%`, strict accepted result `0%`. Missing item: page-top continuation row `3.4.4`. After unblinding, the sample became active.
- Round 5 active checks recovered Audit pages 11–12 at `7/7`. Across three active windows and 17 Requirements, ID recall/precision, page provenance and action separation were all `100%`.
- Round 5’s untouched one-page holdout was Audit Manual page 5. First blind test recovered `3/3` IDs, with direct normative/Indicator/value/page/action all `100%`; critical fields and segment/bbox were each `66.67%`, while strict accepted result remained `0%`. Prediction and parser hashes were locked before unblinding. The sample permanently became active diagnostic.
- Implemented basic English condition/negation/date/threshold extensions, an exact-marker footnote linker, source-backed `clauses[]`, full-document Principle/Criterion profiles and a partial-window supporting-evidence contract.
- Priorities at that point were bracketed-footnote ownership, promotion of Audit instruction/Note qualifiers, quantitative bare `0`, source-explicit subjects, composite cross-references, and independent typography/bbox evaluation. A 100% ID recall must not obscure these field gaps.
- Round 6 completed the footnote, bare `0`, source-subject, field-boundary and evidence-scoring fixes: active IDs 20/20, with direct page/bbox/actions all `100%`.
- Round 6’s untouched Farm Standard page 55 holdout scored `5/6`, precision `100%`. The sole omission was page-top `2.6.13`, continued from the previous page. A partial selection starting on a continuation page still lacked the prior Requirement identity. The sample permanently became active diagnostic.
- Next checkpoint at that time: fix first-row continuation identity with a minimal halo/assembly experiment and establish a consistent source-backed Gold v4 contract. Concurrency and output frequency were reduced.
- Round 7 active fixes add only one previous-page halo to selected runs. Bottom-page geometry, consecutive IDs and consecutive letter markers jointly recover page-top continuation. Projection back to the selected window retains supporting `continuation_anchor` only, without copying outside-window normative text.
- Farm page 55 improved from `5/6` to `6/6`. The body, ID, direct page, three segments and bbox for `2.6.13` exactly match Gold. It remains `review_required` because its governing modal clause is outside the window.
- Inventory stayed `10/10` for Farm 64–65, `6/6` for Salmon/Cod 27–28 and `4/4` for Interpretation 103–106, with no observed halo spillover. Full tests: `296 passed, 1 skipped`.
- Round 7 parser state: `55d489e3a2913216daef4d5278839b71d9b9c39d4ad46e02c600647345f2bd76`. The next checkpoint was a new untouched holdout’s first score under that frozen state. Round 7 remained `ADJUST`; the completion gate had not passed.
- Round 7’s new holdout was Audit Manual pages 17–18, containing 13 Requirements. First blind test: `0/13`. After `docling-parse` failed, fallback produced geometry-free whole-page `pypdf` objects, leaving template learning with zero supporting rows. The sample permanently became active diagnostic.
- Added `pypdfium2` character-box fallback and repaired outside-window supporting footnotes, lowercase CAB markers, `Note Indicator` row contamination and nested-action bullet contracts. The same window then recovered `13/13` IDs; Requirement/Indicator/value, segment, bbox and action separation were all `100%`. Critical fields reached `81.20%`; strict accepted result remained `0%`.
- Repaired parser state: `8f5e5c5f6ab210ea78654555f5fc0dc45e26ca91e0083a08c05da6faa1f35953`. The 194 Requirement-focused tests and new targeted tests passed. Two long-running dependency-import tests blocked full regression, so an all-tests-passed claim was unavailable.
- Next checkpoint: repair dates, threshold relation/scope, conditions, modality scope and logical structure in order, then blind-test a new small document-position-disjoint holdout.
- Round 7 semantic follow-up added production-cycle/frequency/deadline dates and made Audit semantic fragments prefer dedicated field regions. `5.2.3 Requirement: 100%` changed from ambiguous `other` to value-cell-backed `eq 100%`; the item became `accepted`.
- Parser state: `fa4549fd84fe13650f1608572a813bedcdf2c8667a17f9bb64f08964286b3e2e`; 138 relevant cross-document tests passed. Several existing Gold `applies_to` values were human summaries, not source substrings. The next step required a v4 source-backed scope contract and immutable evaluation correction, not hard-coded summaries.
- Established `docs/contracts/requirement-semantic-scope-v4.md` and backward-compatible `scope_ref` for modality, negation, condition, exception, exemption, threshold and date. Every anchor must reference an existing source segment with a character range exactly matching original text. Older v2/v3 results still load.
- Audit Manual pages 17–18 active output: `outputs/runs/goal04-round7/audit-manual-p017-p018-active9-scope-v4/`. Across 13 Requirements and 25 semantic items, all `25/25` scope references are source-backed. Canonical validation: `0` errors. All Requirement-focused cross-document regression tests passed.
- Parser state: `51519ef2fb5e77373c273efe4b586c6ae81f8570c1ac4cff160f9a71aab7c8f4`. Next: connect v4 to immutable Gold revisions and the evaluator, then resolve qualitative-threshold/logical-structure differences such as `5.2.7`. Status remained `ADJUST`.
- Implemented the v4 Gold schema, immutable-revision integrity and source-anchor evaluator. v4 scoring uses source-exact `scope_ref` and text evidence, no longer treating free-form summaries as parsing targets.
- Audit Manual pages 17–18 active output advanced to `outputs/runs/goal04-round7/audit-manual-p017-p018-active15-footnote-provenance/`. Qualitative thresholds, `until` conditions, `need to` modality and modal boundaries were restored. All 13/13 Requirements were `accepted`; Canonical validation returned zero errors. The sole retained source anomaly was lowercase `a.` in the `5.2.9` CAB action. Explicit auditor-column geometry supported recording it without blocking.
- Fixed false provenance failures for bracketed footnote markers: check unmodified source-exact formal evidence first; only after comparison fails, try removing a bare footnote number attached by the PDF text layer. Relevant model, Gold, semantic and Canonical tests passed. Parser state: `c0477449a70c26725c7f77e6365bc5b1b5beb55f57e4dee94f35a6eedb23ceef`.
- These are post-unblinding active diagnostics and do not change Round 7’s first blind-test failure. Next: complete the immutable Round 7 Gold v4 revision and scoring, then select a new small document-position-disjoint holdout. The completion gate still cannot be claimed as passed.
- Round 7’s immutable Gold v4 revision is `gold/requirements/annotations/audit-manual-p017-p018-round7-holdout-v4.json`. Revision 2 binds predecessor path and SHA-256 while preserving all 133 frozen source segments, sample window and excluded regions. The v4 integrity gate rejects any source-segment or exclusion drift.
- `gold/requirements/manifest-round7-v4.json` explicitly uses `active_diagnostic` mode. Evaluation forces `completion_gate_eligible: false`, preventing a false new-holdout success claim. Report: `outputs/runs/goal04-round7/requirement-evaluation-v4-active15.json`.
- v4 active scores: Requirement recall/precision `100%/100%`, critical-field exact `88.89%`, critical-nonempty exact `75%`, action separation `100%`, strict accepted-result `0%`. Thus 13/13 `accepted` did not mean complete semantic correctness. Main gaps: dates `53.85%`, thresholds `76.92%`, conditions `84.62%`, modalities/logical structure each `92.31%`.
- Parser state: `28f942e47e11a9f43296fa489384543930cfc07e8573680c6613b07a234e899c`. All eight focused Requirement Gold/manifest/model/semantic/Canonical suites passed. Next: repair date, threshold and condition scope against v4 differences before freezing another holdout.
- Round 7 v4 active18 raised all nine critical-field categories, including dates, thresholds, conditions, modalities and logical structure, to `100% exact`. All 13/13 Requirements remained `accepted`; Canonical validation returned zero errors, and 204 cross-structure targeted tests passed.
- General fixes included role-aware applicability/value anchors, duplicate applicability-threshold removal, modal/action/date scope, footnote scope kind, Audit subject isolation, and disambiguation of Audit inline numbered lists from Appendix Roman references. Report: `outputs/runs/goal04-round7/requirement-evaluation-v4-active18.json`. Parser fingerprint: `361ed934830355daf0e9ef70a1d38725bc6341d844817cdd77b0df9e259ab9dd`.
- A low-token single-thread checkpoint stabilized semantic `criterion_path` while retaining complete heading evidence. Ancestor footnotes explicitly naming a Requirement became `semantic`; Appendix references no longer consumed final punctuation. active19 strict accepted-result rose from `0/13` to `5/13`; remaining differences concerned cross-references, instruction ownership and one supporting-page boundary. The next round was restricted to these relationships without expanding samples.
- active22 completed source-backed instruction, footnote-marker, Indicator-dependency and supporting-page provenance contracts. All 13/13 Requirements on pages 17–18 reached strict exact, with every reported metric at 100%. The full suite passed with one environment-related skip. This unblinded window remains active regression only; the next step must freeze a new position-disjoint holdout.
- Round 8 locked Interpretation Manual pages 80–82 as a position-disjoint holdout before source inspection and prediction, then generated source-only native evidence. Gold freezing and hash registration preceded parser prediction.
- Round 8 Gold was frozen before prediction and received its first blind test. All 3/3 Requirement inventory, direct pages and bboxes were correct; explanatory modal prose did not create spurious Requirements. Only 1/3 was accepted and strict accepted-result was 0/3, exposing cross-structure gaps in explicit subjects, quote spacing, footnote semantic scope, condition/clause boundaries and composite references.
- Initial Gold v4 scope annotations also contained errors. Immutable revision 2 corrected them while preserving original blind-test evidence. Adjudicated active-diagnostic critical-field exact was 62.96%; critical-nonempty exact was 35.71%. Round 8 permanently became active diagnostic and cannot support a new holdout-success claim.
- Round 8 active2 separated attached footnote markers from the semantic source view while preserving `native_text` completely. All 3/3 normative texts on pages 80–82 and modality anchors for `2.5.1`/`2.5.2` became source-exact. Critical-field exact rose to 74.07%, critical-nonempty exact to 57.14%. The next round was limited to footnote 11 qualifier semantics.
- The user requested pausing optimization after the final footnote 11 repair. active4 made `2.5.2` accepted, with critical-field exact 85.19% and critical-nonempty exact 71.43%. Hashes for Round 7’s 13/13 strict-exact output were unchanged.
- All four English PDFs in `data/inputs/` were fully parsed into `outputs/runs/four-file-review-20260828/`, with `REVIEW_INDEX.md` as the human-check entry. Each has nonempty Markdown, Canonical JSON, Requirement IR and a quality report. Two are `failed` and two `review_required`; they are not release-passing evidence.
- At that checkpoint, work paused for the user’s requested human verification. The goal remained incomplete, awaiting new error examples from Markdown/source comparison before resuming iteration. Later authorization above supersedes this historical pause.
- Strict accepted-result remained `0%` because criterion paths, cross-reference/footnote/instruction ownership and direct/supporting-page contracts were not aligned. Status remained `ADJUST`; those strict fields needed resolution before another position-disjoint holdout was frozen.
- Irreversible sample state: `gold/requirements/sample-history.json`. Round-by-round evidence and next experiments: `docs/reports/04-requirement-convergence-ledger.md`.
- This goal cannot complete before adding a real Norwegian PDF and passing a document-disjoint holdout.

## Preserved baseline

`outputs/baselines/asc-int-001-full-before-document-profile/`

- 511 pages and 9,260 blocks.
- Status: `review_required`.
- The `Indicator / Requirement` template has intermittent misses.
- This baseline compares structural recovery before and after refactoring; do not overwrite it.

## Historical page-level checkpoint

Implemented lightweight full-document Document Profile Learning and page-level text-layer routing, then parsed pages 6–28:

1. All 511 pages contributed feature learning; production output contained only human page numbers 6–28, totaling 23 pages.
2. Twenty pages used reliable native text; three used native text with visual supplementation for embedded images. Zero pages used full-page OCR.
3. Learned 294 `Indicator / Requirement` template instances. Multiple same-page templates produce separate tables. Single-clause tables recover as `2×2`; multiple clauses in one physical table use multiple rows with two fixed columns. `1.1.1`, `1.2.1`, `1.4.1/1.4.2`, `1.4.6` and `1.4.7` were correctly restored.
4. Headerless cross-page continuation rows `c`–`e` for `1.4.3` rejoin the same Requirement cell through template columns and consecutive numbering. Internal `a./b./•` lists are no longer flattened into one paragraph.
5. Headers and footers follow independently learned templates; different top-of-page candidates are no longer merged. Page 20 body text `The UoC may decide...` was restored from a false header, with a repeated-header text-consistency gate added. Numbered bottom notes became `footnote`; `Useful Resources N/A` split into a heading and content value.
6. Line-end word breaks, compound words and URLs use distinct joining rules. `up-to-date` and cross-block `(Indicator 1.4.2(d))` were restored.
7. Requirement quality gates now require exactly two columns, an exact ID on the left and nonempty text on the right. Malformed multi-column tables no longer pass. Header background colors no longer cause completeness false positives.
8. Five native superscripts were restored as `[^1]` through `[^5]` using glyph height and baseline position, including table-cell links. Each footnote definition has exactly one real anchor; page, Indicator and Appendix numbers no longer link incorrectly.
9. Markdown and HTML place footnote definitions at the document end. HTML preserves nested lists and table-cell line breaks. RAG uses depth-first Canonical-tree traversal, excluding headers/footers, footnote physical positions and empty image blocks.
10. Regulatory IR prioritizes formal clauses in `Indicator / Requirement` tables. All 18 formal IDs entered IR; missing clauses trigger critical review rather than replacement by explanatory prose.
11. Non-resume overwrite runs clean only parser-owned artifacts. Completion recursively removes numbered duplicates generated by Finder/File Provider, leaving unknown user files untouched.
12. Pages 6–28 had status `accepted`, with `review_queue` and `review_items` both zero. The full suite passed with one environment-related skip.

Results at that checkpoint: `outputs/runs/asc-int-001-p006-p028-native-routed/`. The old 511-page result remains a pre-refactoring baseline only.

## Historical decision

`CONTINUE`: document adaptation, native/scanned routing, repeated Requirement templates and cross-page continuation were supported by the evidence. No template overwrite of ordinary prose or reading-order regression was observed.

The most useful next experiment at that point was cross-document regression on a new user-provided regulation/standard PDF to determine whether fixes generalized beyond ASC templates. Insufficient evidence must retain review, without automatic guessing.

## Principle 2 guarded-processing checkpoint | 2026-08-27

An overwrite rerun completed human pages 29–159 of the same production PDF (Principle 2, 131 pages). Results:

`outputs/runs/asc-int-001-principle-2-p029-p159-native-routed/`

Additions and validation in that round:

1. Added local `pdftotext -bbox-layout` as a second native-evidence path. It checks critical tokens within the same page/bbox, without replacing primary native text or sending document content externally.
2. Automatic text repair requires exact secondary evidence in the same bbox. Nineteen repairs included `≥1 5% → ≥15%`, `firstorder → first-order`, `peerreviewed → peer-reviewed` and `noncertified → non-certified`. Primary `native_text` remains unchanged; repairs are recorded in block operations.
3. Numeric, modality, negation and comparison-operator differences unresolved by two evidence paths enter critical review. Identical critical-value sets in a different extraction order no longer trigger false alarms.
4. Tiny duplicate glyphs at table right edges are suppressed using table geometry plus duplicate text/punctuation fragments. Isolated `,` and `a` were removed in this round; native objects remain in raw evidence.
5. Isolated same-page conjunctions `and/or` and reference tails `p./pp.` rejoin the previous logical list item.
6. Visual `o/○/◦` bullets in Requirement cells become semantic bullets rendered as `<br>•`.
7. Eight local headings consisting of a short noun phrase immediately followed by a same-page list became level-four headings. Figure 1’s caption attaches to the figure block, and explicit body references to `Figure 1` produce `content_links`.
8. Native-only pages are no longer marked low-confidence because unrun OCR defaults to `0`. The release gate fails closed when accepted-result precision evidence is missing instead of defaulting to `1.0`.
9. Results: `quality.status=accepted`, `review_queue=0`, `low_confidence_block_ids=0`. The full suite passed 104 tests with one environment-related skip.

Acceptance boundaries:

- `accepted` means these 131 pages passed current document-level completeness, conflict and structural gates. It does not mean the complete 511-page file was verified.
- `accepted_result_precision` was not yet calculated from Gold, so the release gate correctly refuses formal publication.
- Canonical hierarchy still mainly uses one root section; a complete Criterion/Indicator semantic section tree is not yet built.
- The Principle 2 cover retains multiple independent visual objects. Stable distinction between decorative visuals and composite figures needs cross-document validation before automatic merging or suppression.
- Local validation and CLI require `PYTHONPATH=src`. An older installed package previously existed in the environment; direct `import pdf_extraction` loaded its old schema and produced false validation errors.

Decision at this historical checkpoint: `CONTINUE`. Next was cross-document regression on a new user-provided regulation/standard PDF, plus Criterion/Indicator semantic sections and internal Gold evaluation of accepted-result precision.
