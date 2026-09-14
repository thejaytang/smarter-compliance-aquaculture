# Material extraction evidence, 2026-09-12

The current product parser is `/7`; [its final checkpoint](structure-diagnostic/source-line-fidelity/RESULTS.md) records 189 material tests and retained source evidence. **The user stopped further accuracy optimization on 2026-09-13.** This index retains diagnostic failures and denominators; they are no longer current completion gates. Further sample expansion, holdout campaigns, parser tuning and classifier integration are deferred. The preceding `/6` checkpoint follows. Its [grid-consistency recovery evidence](structure-diagnostic/grid-consistency/product-v6/RESULTS.md) records 159 passing material-module tests and isolated fixed-DEV validation: six wrong grids become 14 exact positioned lines with located unresolved ranges; eight real table regions remain unchanged. Content scores do not improve and the 1×1 false table remains. The `/5` [HTML section-numbering diagnostic](html-numbering/RESULTS.md) is retained: 42/42 PA001 source heading labels are complete, with non-numbering fields in all 412 blocks unchanged. These are exposed DEV results, not independent quality acceptance. PDF paragraph behavior retains [version 4 conservative grouping](paragraph-diagnostic/README.md); earlier versions and [isolated experiments](structure-diagnostic/README.md) remain preserved.

**Exposure update, 2026-09-13:** CS010 is now an explicitly exposed development/regression document for [source-line fidelity diagnosis](structure-diagnostic/source-line-fidelity/scope.json). Its historical reserved scores, annotation bytes and denominators remain retained. Future runs on CS010 cannot establish independent verification; any future accuracy phase would need a new unexposed verification scope; none is being established now.

## Scope and status

The frozen [manifest](manifest.json) contains **7 real development documents**, **4 synthetic mechanism documents**, and **2 current-round reserved, historically exposed PDF documents**. Reserved source annotations were frozen before prediction, then measured with unchanged rules on /2 and /4. There are nine real documents in total, within the requested 8–12 sampling target, plus four separate synthetic controls. Complete source-first reserved annotations currently cover only the two PDF windows; the other real formats lack equivalent independent acceptance annotations. No all-history untouched holdout is established. The latest [reserved /4 results](verification-after-v4/RESULTS.md) are **FAIL**: complete units PA057 30/33 and CS010 24/45; structural relations 35/57 and 7/55; critical substrings 18/18 and 46/54, with eight CS010 failures not located by product warnings. Other-format independent quality and end-to-end Requirement precision/recall remain **UNMEASURED**. These outcomes are now exposed; future tuning must record that exposure and select new verification scope.

The current changes improve source boundaries, truthful result states, adjacent marker order, conservative same-page paragraph grouping and explicit fallback for inconsistent PDF grids. General PDF hierarchy, table and multi-column fidelity still fail. The [classifier development report](requirement-dev/RESULTS.md) separately records /6 source-role improvements and the minimal adapter assessment; classifier rules and source-oracle tests do not establish end-to-end identification or semantic decomposition. The material processor remains disconnected. [Historical `/4` full System2 regression](regression-current/RESULTS.md): 1072 passed, one historical fixture skipped, one existing warning. It does not bind the subsequent `/5` or `/6` candidates; broader `/6` integration/full regression remains pending. The reserved `/4` PDF FAIL is not upgraded by HTML numbering or isolated grid recovery evidence.

## Frozen scope

| Material | PDF index, zero-based | Reader page, one-based | Purpose |
| --- | --- | --- | --- |
| ASC Farm Standard | 27, 28 | 28, 29 | Active annotated standard rows |
| ASC Interpretation Manual | 18, 19, 20 | 19, 20, 21 | Active annotated context/clauses |
| ASC Salmon Audit Manual | 0, 1, 2 | 1, 2, 3 | Active legacy tables |
| ASC Salmon and Cod Standard | 17 | 18 | Active annotated requirements |
| Four synthetic Gold PDFs | All existing pages, 1–2 per file | All | Scan, multi-column, table, cross-page mechanisms |
| PA002 HTML | Not applicable | Full local HTML | Lovdata boundaries and annex tables |
| CS001 HTML | Not applicable | Full local HTML | ASC text, table and footnote boundaries |
| GLOBALG.A.P. XLSX | Not applicable | `CL - IFA v6 Smart - AQ!A9:H24` | Independent fixed cell correspondence |
| PA057 PDF, reserved only | 4, 5 | 5, 6 | Source-selected; same document already diagnosed historically |
| CS010 PDF, reserved only | 2, 3 | 3, 4 | Whole document previously parsed; not independent |

The 174,604-byte XLSX was parsed in full; only the frozen cell window is measured. Its [source inventory](xlsx-source-window.json) was captured with openpyxl before prediction. Parser execution used isolated engineering Snapshot identifiers, not a business selection or human review decision. No original, Gold, existing baseline or live database was changed.

Existing ASC engineering annotations supply segment and Requirement evidence, but their complete content-unit and binary positive/negative denominators have not been validated for this task. All 13 historical entries in `system2/gold/requirements/sample-history.json` are already active. A filename containing `holdout` does not restore independent status.

## Preserved version 1 baseline and environment observations

- [Fingerprint before](fingerprint-before.json) records parser source, dependencies, lockfile and configuration hashes. Reader navigation was separately updated during the wider task; the material parser remained version 1 until the fixed pre-change runs completed.
- `before/asc-farm/` retains the first attempt's pinned source and exact two-page derivative. The owned run was interrupted with Ctrl-C, exit 130, after the docling import stalled inside pandas/importlib file loading. It produced no candidate and is not a successful baseline.
- A separate 30-second import probe timed out at 30.007 seconds in the same import chain. Once dependencies were warm, the bounded [exact-route retry](before-retry/) completed all eight PDF windows. **Every exact-route PDF used PDFium through the pre-existing RuntimeError fallback.** The [backend error](docling-backend-error.json) records a missing usable FontName in docling's Times-Bold.afm resource.
- [before-guarded](before-guarded/) retains exact-route HTML/XLSX execution with per-sample subprocess receipts. PA002 produced 373 blocks; CS001 produced 16,105; XLSX produced 16.
- [pdfium-diagnostic](pdfium-diagnostic/) is an explicitly separate experiment forcing the existing local PDFium native backend. It is not relabelled as original configuration execution.
- [Exact baseline diagnostics](exact-baseline-diagnostics.json) retain bounded observations. Segment substring counts are **not recall**, because fragmentation, ordering and denominator completeness are not independently resolved.

Each guarded development process has a 45-second operational limit and retained stdout/stderr. This is a runaway-process guard, not a work-duration or acceptance requirement. Reserved samples are excluded by the harness.

## Preserved version 2 change and fixed-sample comparison

`material-structural-parser/2` selects the existing positioned PDFium backend directly for the material route. The legacy positioned YAML remains unchanged. Native evidence records both the material backend policy and retained legacy configuration. This removes the unnecessary cold docling import path; it does not improve PDF layout quality or supply a universal native execution timeout.

The parser distinguishes processed scope from scope containing usable text/table content. Image-only or blank PDF pages retain source images and locators but create unresolved scope. An image-only document reports `empty`; mixed usable and native-empty pages report `partial`. A table-only native page remains usable. `covered_scope` retains its historical processed-range meaning for compatibility; consumers should use `usable_scope` to describe usable extracted scope.

HTML source text now retains `<br>` and block boundaries without inserting spaces inside inline text. For example, `must<br>not` retains a boundary, while `H<sub>2</sub>O` remains `H2O`.

[Before/after comparison](before-after-comparison.json) and [after-pdf](after-pdf/)/[after-nonpdf](after-nonpdf/) retain exact artifacts:

- Synthetic scanned-critical changed from `candidate_available` with one image and zero usable text to `empty` with a located unresolved page. Original/image blocks remain identical.
- All eight fixed PDF samples retained identical text, table values and block identities. This is bounded regression evidence, not proof that the unchanged content is accurate.
- PA002 and CS001 retain their block counts, with source text boundaries updated. Global source-fidelity quality remains unmeasured.
- The frozen XLSX window retains **128/128 exact unique cell correspondences**, comprising **113 nonempty and 15 empty cells**. This is an engineering cell check only, not global workbook or Requirement acceptance.

Six source-authored regression tests were added. The pre-change run had 5 failures and 1 pass, exposing missing breaks, image-only false completeness, mixed-page false completeness, unavailable usable-scope metadata and unwanted docling invocation. After repair, the six new tests and seven existing reader/parser tests passed, **13/13**, in the owning System2 environment. The new tests cover image-only, blank/native mixed, table-only, inline breaks, nested lists and backend invocation boundaries.

At the version 2 checkpoint, [preservation](preservation.json) confirmed unchanged frozen source/annotation hashes, absent reserved candidates and unchanged legacy configuration. Later reserved runs are recorded separately; this historical absence statement does not describe the current evidence directory.

## Current boundary and continuation

Automatic accuracy work is paused by explicit user instruction. Preserve all samples, errors, Gold, exposure records and denominators for a future phase. Current work follows the [human-review execution entry](../execution.md): readable source independent of candidates, visible unchecked ranges, durable manual corrections and decisions, conflict recovery and review provenance. Do not treat missing/unreviewed content as negative training labels or machine output as confirmed human annotation. Model training is future work.

`measure_baseline.py`, `run_guarded.py` and `analyze_baseline.py` document the measurement approach. They use exclusive output creation and must not be rerun into existing evidence directories. They are engineering helpers, not product launchers or background schedules.
