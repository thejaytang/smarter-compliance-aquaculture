# Native structure diagnostic and marker-order repair

## Outcome

The bounded repair is implemented as `material-structural-parser/3`. It changes only the order of a separate numbering/list marker relative to an unambiguous adjacent body on the same native row. It never merges strings, changes a block payload, removes evidence, promotes a heading or changes the relative order of nonmoved content.

On the frozen development windows, six Farm markers and twenty Interpretation markers were moved before their adjacent bodies. The other six PDF samples were unchanged. [Version 3 verification](v3-verification.json) confirms exact block-payload/source-reference preservation, unchanged source hashes, unchanged extraction states/scopes and unchanged nonmoved order for all eight samples.

The source-rendered-page [engineering relation subset](relation-subset-before.json) was frozen before implementation: eight positive marker/body relations on Farm p28 and Interpretation p19, plus one negative footer-version/page-label pair. Positive ordering changed from **0/8 to 8/8**. Negative abstention is **1/1**. These are deliberately bounded development checks, seeded by diagnostics and visually checked against the two original page images. They are not independent holdout, business Gold or the overall 90% structure-accuracy denominator.

Twenty targeted new/existing parser tests pass. The ordering tests cover exact payload preservation, idempotence, two-column body-order preservation and abstention for distant columns, separate rows, duplicate text layers, table boundaries and bare numbers. The remaining thirteen tests retain the earlier HTML-boundary, empty/partial PDF and reader/parser coverage.

## Diagnosis and source evidence

`NativeExtractor._extract_pdfium_positioned()` retains real character-derived line boxes. A numbered marker can have a slightly lower y0 than its same-row body because its glyphs have a different height. The material parser's global `(y0, x0)` sort therefore placed the body before its number. Examples visible in the original rendered pages:

- Farm p28: `1.1.1` follows the displayed body beginning `The UoC shall hold...` in the old candidate.
- Interpretation p19: `1.4.1`, `1.4.2`, `a.`, `c.`, `d.` and `e.` follow their corresponding body text in the old candidate.

[Pure-primitive results](results.json) retain the diagnostic, including unsuccessful reuse options. The initial broad detector found 21 apparent inversions but included three false footer candidates: version `1.0` paired with the distant page label. These were not accepted as positive annotations. The implementation uses a smaller local gap bound based on body height and page width, the existing native-fragment vertical-overlap criterion, unique nearest-body association and table/compound barriers.

`_stabilize_marker_order()` checks a fully matched marker token, same-row vertical overlap of at least 0.7, and a horizontal gap no larger than `min(page_width * 0.12, max(18, 6 * body_height))`. It abstains when a match is ambiguous, inside retained table geometry, or would cross a table, image or heading. Competing markers for one body also abstain. Only misplaced markers move; nonmarker content order cannot change by construction. No global column-order inference is introduced.

Each PDF run includes `pdf-order-repairs.json` with marker/body IDs, original source references and measured geometry. Native evidence retains the original native sequence. The candidate warning asks for source association verification.

## Existing code reuse assessment

| Existing primitive | Observed result on frozen development evidence | Decision |
| --- | --- | --- |
| `routing/text_layer.py::_merge_adjacent_line_fragments` | Useful same-row overlap criterion; its returned text introduces spaces, including `fines4 .` | Reuse the geometric reasoning only; retain strings and refs exactly |
| `domains/requirements/hierarchy.py::learn_requirement_hierarchy_profile` | Finds six explicit headings across real/synthetic samples, but confidently selects covered native text in Farm p28 | Do not promote headings automatically |
| `layout/marginals.py::detect_repeating_marginals` | Finds valid footers but also labels visible heading fragments `1` / `.1` as repeating marginal material in the two-page Farm window | Do not suppress or remove source content from these detections |
| `layout/reading_order.py::repair_fragmented_column_runs` | Changes zero tested pages; requires dense multi-column runs unavailable in the short synthetic example | Not evidence of a useful immediate repair |
| `assemble/paragraph_assembler.py::_score` / `assemble_paragraphs` | Finds plausible wrapped text, but pre-repair order also scores adjoining distinct clauses; join logic can change hyphens | Do not connect automatic paragraph assembly directly |
| `routing/text_layer.py::native_analysis_page` + `HeuristicLayoutDetector` | Existing local native-only bridge; retains line grouping but still sorts geometrically and applies broad heading heuristics | Candidate future controlled structural adapter, not a reason to activate the full domain pipeline |

The strongest overall legacy path includes native analysis, layout, marginal/list annotations, profile repairs and document assembly. Its components have useful primitives, but connecting the entire path would also introduce source-text and semantic behavior outside this bounded ordering repair.

## Material source-fidelity issue remains open

The actual rendered Farm p28 heading is `1.1 Legal Compliance`. The native layer also contains `Criterion 1.1 – Legal Compliance`, overlapping the visible heading. The candidate currently includes both in a 1×14 table, alongside `1 .1`; the native heading profiler selects the covered variant at confidence 0.99. The visible page is [Farm p28](../after-pdf/asc-farm/pdf-page-0028.png); native reference `native_p0000_fw000008` and the candidate table preserve the conflicting content.

This is a native/rendered discrepancy, not permission to delete text or accept the profiler's confidence. Hidden/covered text visibility, heading/table misclassification, full clause grouping, cross-page structure and genuine multi-column reading order remain open. Native ordering stabilization does not resolve those failures or establish general extraction quality.

## Reproduction

`probe.py` reads the existing frozen native/candidate artifacts through pure existing APIs. `stabilize_experiment.py` produced the preimplementation [proposal](stabilization-proposal.json). `../after-v3-pdf/` contains fresh real parser runs of the same eight fixed windows. No PA057 or CS010 reserved output was created, and no original/Gold/annotation history was changed.


## Local native backend resource diagnostic (2026-09-13)

Decision: **ADJUST the next experiment; keep `/4` frozen.** A single A/B/A resource-access experiment used only the existing Farm pp.28–29 development derivative. Installed `docling-parse 7.15.0` first failed on `Arial.afm`; a temporary copied package parsed the same window in 1.89s; the unchanged original installation then succeeded in 1.30s with identical native output. Historical Times-Bold and current Arial both contain `FontName` and match installed RECORD hashes. This does not support rewriting AFM content or declaring spaces in the path the cause. Resource-read/materialization state is a working explanation, not a verified OS diagnosis.

Crucial copy limitation: final hashes show 443/445 package files identical. Two temporary CMap `cid2code.txt` files became empty while installed originals remained nonempty. Every AFM, Python file and native binary matched. The temporary directory is therefore **not a complete package, installation, product load or deployment candidate**; it is preserved as failure evidence. Farm Latin-script success does not cover those CMaps. No dependency or original resource was changed.

| Two-page native evidence | Existing PDFium adapter | Docling native adapter |
| --- | ---: | ---: |
| Word objects | 66 whole-line fragments | 388 words |
| Text lines | 66 | 100 |
| Character objects | 0 | 2764 |
| Words with font name/key | 0 | 388 |
| Shapes | 0 | 0 |

The reusable interface is existing `NativeExtractor('docling-parse').extract(window_path)`, using `system2/.venv` and `PYTHONPATH=src`. Its word/character/font evidence can feed existing `native_analysis_page` and character-aware `native_spacing.coalesce`; paragraph, cell-assignment and order gains require the next isolated development comparison. This experiment did not measure those gains or modify material output.

Only **docling-parse**, not the full **docling** conversion/layout package, is installed. The positioned config still specifies heuristic layout. Existing Paddle layout/table weights are cached, but `paddleocr`, `paddlex`, `paddlepaddle` and `onnxruntime` are absent. GMFT is installed but no weights were found in the configured project Hugging Face cache. Tesseract exposes eng/osd/snum; no OCR/model inference was executed. Cached weights are not callable-backend evidence.

The Docling-fed heading profiler still marks the already-known covered Criterion strings at confidence 0.99. They remain **unverified hidden native text**, not passed source headings. No heading/table/order or quality gate is upgraded. See [inventory](backend-probe/inventory.json), [A/B/A summary](backend-probe/summary.json), [complete package-copy hashes](backend-probe/package-copy-hashes.json), native outputs and receipts in `backend-probe/`. No reserved samples were read. No further experiment was run after the original-path check.

### Follow-up native/assembly comparison not run

The planned Farm/Interpretation development comparison was stopped during read-only preparation under the coordinator's new resource-read stop boundary. The preparation command eventually returned normally (exit 0), so neither a specific blocked stack nor damaged annotation is established. No parser comparison, product edit, model installation or reserved-sample use occurred. New boundary/numbering/critical-phrase results remain **UNMEASURED**. The exact observation and preserved denominator references are in [NOT_RUN.json](native-assembly-comparison/NOT_RUN.json); the prior A/B/A evidence above is unchanged.

### Resumed comparison: import timeout, no backend decision

Small reads later completed normally, so the one Farm/Interpretation comparison resumed with explicit experimental backend provenance. Farm PDFium completed and exactly reproduces `/4`; Farm Docling reached the 60-second guard inside `numpy.random` native extension import through pandas/docling_core, before native output or candidate creation. Interpretation was not started. Source-preserving group reconstruction passed for the completed control; comparative structure/paragraph gains remain **UNMEASURED**. No product, dependency or source change followed. See the [resumed comparison report](native-assembly-comparison/RESULTS.md) and retained stack/partial output for the next controlled resumption.

### Import-only observation permits a new frozen DEV comparison

The [single import-only observation](native-assembly-comparison/import-only/RESULTS.md) completed in 42.856 seconds with progress and unchanged product fingerprints. The earlier `_philox` stall did not persist in this observation; a later stack paused in pandas code loading and then completed. Resume the already frozen DEV comparison only in a new preserved run that distinguishes import readiness from parsing. This is not a backend quality result or proof of an OS materialization cause; the earlier 60-second failure remains preserved. No parser was run in this diagnostic.

### Resumed comparison: readiness passed, constructor resource failure

[Run 2](native-assembly-comparison/run-2/RESULTS.md) preserved the original source/annotation freeze and completed both Farm import-readiness phases (0.309 s PDFium; 0.979 s Docling). PDFium reproduced the frozen 44-block control. Docling then failed at constructor resource loading (`Helvetica.afm`, no `FontName`) before native output; Interpretation was not started. Stop backend comparison without another retry or environment repair. Comparative quality remains `UNMEASURED`; no backend promotion is justified.

### PDFium character granularity is locally available

The [single-page PDFium granularity probe](pdfium-granularity/RESULTS.md) retained 1,269 characters and reproduced all 30 frozen Farm p28 line texts/bboxes exactly, while exposing 173 source-preserving whitespace words and font/size/box data for all 1,070 non-whitespace characters. This establishes a local evidence path independent of Docling, not a heading/table quality gain. The smallest next experiment is an isolated adapter feeding narrower word geometry to the existing table consumer while preserving line output; product code remains unchanged. Covered Criterion text remains unverified despite its font/render-mode signals.

### Richer PDFium words: preserved evidence, no downstream gain

The [two-window isolated downstream experiment](pdfium-granularity/downstream/RESULTS.md) preserved 8,097 native characters, 1,160 word partitions and all original line/ID/ref/order invariants. Fixed source/critical-text/marker diagnostics did not improve. Interpretation is identical; two Farm table payloads become further fragmented by the existing false fine grid. Do not promote naive word replacement: current content uses unchanged lines, and finer words only feed the unreliable table grid. The next useful target is general grid/boundary validation with source-line preservation. No product changes or backend promotion occurred.

### Grid/native-line consistency separates current DEV false headers

The [15-grid diagnostic](grid-consistency/RESULTS.md) found 50–100% line-crossing ratios in six wrong Farm/Interpretation fine grids, versus 0–11.11% across eight real table regions at 1 pt. A provisional >=25% rejection criterion is frozen for the next isolated-copy experiment; it is DEV calibration, not independent accuracy. Full per-line geometry and native fallback are retained. The 1×1 figure false table remains undetected, and any-crossing/absolute-distance rejection would harm valid Audit tables.

### Isolated grid fallback preserves source work

The [predeclared guard experiment](grid-consistency/fallback-experiment/RESULTS.md) on a preserved `/4` copy rejected six wrong fine grids, restored 14 exact native lines with six located unresolved ranges, and left eight real table regions unchanged. All nonrejected primitive payload/order/refs remain exact. Fixed content/critical metrics did not improve; the 1×1 figure false table and borderless 0/10 cell diagnostic remain. This is calibrated DEV recovery evidence, not product promotion or independent quality acceptance. A [standalone range preview](grid-consistency/fallback-experiment/unresolved-ranges.html) makes the unresolved source regions reviewable.

### Product /6 integrates the calibrated grid recovery guard

[Product /6](grid-consistency/product-v6/RESULTS.md) preserves the /5 HTML suffix fix and adds merge-aware grid rejection, full rejected evidence and located unresolved fallback. Missing/multiple ownership and zero native evidence reject the region without a whole-document exception. All 159 material-module tests and seven fixed DEV runs pass their bounded preservation checks, matching the isolated experiment. No full System2 regression or reserved quality rerun has occurred; fixed content scores and known failures remain unchanged. Normal Workbench loading is outside this subtask.
