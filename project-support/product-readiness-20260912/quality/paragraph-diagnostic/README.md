# 1. Development-only paragraph and table diagnosis

**Implemented:** `material-structural-parser/4` now includes the conservative same-page grouping described below. Final outputs are `../after-v4-conservative-pdf/`; verified source/code fingerprint and per-sample results are in `v4-conservative-verification.json`. The original proposal and rejected first `/4` outputs remain evidence, not the final candidate. This was isolated local validation; integration loading is owned by the root task.

The first `/4` run incorrectly grouped synthetic borderless labels `Combined category` and `Item`. Final code adds a general short-label abstention: automatic continuation needs at least five words in its preceding fragment. Explicit marker/body attachment retains its independent geometry rule. It also excludes the top/bottom 10% page bands, explicit header/footer/margin roles, structural blocks, and image intersections. This conservative guard can leave valid short continuations unresolved.

Final all-eight PDF regression restores every original `/3` block payload and order from candidate plus fragment artifact, with exact group text/newlines/references, unchanged originals/status/scope and successful material block validation. Final counts: Farm 66→44; Interpretation 151→115; Audit 14→14; Salmon/Cod 25→16; synthetic borderless 16→16; multicolumn 9→9; cross-page 7→7; scan 1→1. The table above/below uses the same formal/clause denominators and its gains remain unchanged. The final 85-test parser, reader, material service/store, collaboration and provenance selection passed; see `test-receipt.json`.

## 1.0 Preserved proposal

The following describes the preserved pre-implementation proposal experiment, not a product release or acceptance result. Inputs are the frozen `/3` material candidates and native evidence for ASC Farm pp. 28–29 (zero-based 27, 28) and ASC Interpretation pp. 19–21 (zero-based 18, 19, 20). No reserved source, prediction, or annotation was inspected. Product code was not edited in this experiment.

## 1.1 Reproducible evidence

`probe.py` loads retained candidates, runs the existing pure local paragraph score and native Requirement assembler, and writes `proposal-results.json` exclusively. `summarize.py` writes `summary.json`. Existing engineering annotation hashes are captured. Both use the declared System2 environment, no OCR, model downloads or external services.

The subset consists of every formal normative text and every annotated clause in the two existing engineering annotations. Exact text containment is checked after whitespace normalization only. Formal-text and clause checks overlap and must remain separate. This is single-editable-unit containment, not source-unit recall, independent quality, or Requirement precision/recall. These annotations were already active regression material before this goal.

| Existing engineering subset | Before /3 | Proposed grouping | Denominator |
| --- | ---: | ---: | ---: |
| Farm formal normative text in one block/group | 1 | 6 | 6 |
| Farm annotated clause body in one block/group | 2 | 7 | 7 |
| Interpretation formal normative text in one block/group | 0 | 1 | 3 |
| Interpretation annotated clause body in one block/group | 5 | 13 | 13 |

Farm decreases from 66 blocks to 43 groups; Interpretation from 151 to 114. Flattening all group members reproduces every original block payload and order exactly, including tables/images. No native token, source reference, original fragment, hyphen or punctuation is deleted/replaced. Joining uses newlines only.

## 1.2 Smallest proposed product change

Keep `/3` native extraction and marker order. Add a same-page paragraph grouping step afterward:

1. Combine an adjacent, geometrically proven marker/body pair, using the existing marker grammar and overlap/gap guards; expose the exact marker through the existing `numbering` field.
2. Reuse `assemble/paragraph_assembler.py::_score` for subsequent line continuation, while retaining explicit marker/page/table/image/heading boundaries. Do not run the full `assemble_paragraphs`, because it globally sorts fragments, drops merged blocks and rewrites line-ending hyphens through `_join_text`.
3. Preserve every fragment ID/text/source reference in an audit artifact (and retain source references on the resulting editable group). Preserve deterministic IDs derived from members; never apply this grouping to an existing human overlay.
4. Abstain on cross-page continuation or uncertain marker attachment. Do not infer headings or list parents in this change. The material schema only permits heading parents, so it cannot safely encode a full nested-list tree by setting `parent_id` to a text block.

Required regressions: numbered multi-line clause remains one group; adjacent separate numbered clauses stay separate; nested markers and colon-led child lists stay separate; page/table/image/heading boundaries; two-column separation; distinct paragraphs separated by sentence punctuation/gap; original hyphen/number/negation strings and individual refs preserved; repeated parse stable. Frozen dev comparison must check all source-fragment multisets and ordering, plus the above separate denominators. Root must approve product implementation based on this proposal first.

## 1.3 Existing stronger assembly path and why it is not a drop-in

`domains/requirements/native_assembler.py::NativeRequirementAssembler` detects layout families, derives ID anchors and assembles bounded row bands directly from native words. On the same frozen native evidence it returns all six Farm IDs and three Interpretation IDs. Its normative text exactly matches whitespace-normalized engineering annotation in 6/6 Farm and 2/3 Interpretation cases. These are active-dev comparisons, not Requirement precision/recall.

It restores full 1.4.3 across pages with four retained spans. However, it intentionally selects formal Requirement regions, filters semantic markers, separates applicability and excludes surrounding explanation. Replacing raw material extraction with this route would omit required source content and couple the first layer to the second-layer definition. It is suitable evidence for an explicit second-layer adapter, not a wholesale source-candidate replacement.

Interpretation 1.4.2 and 1.4.3 remain multiple groups in the proposed generic first-layer repair. Their child clauses and cross-page relationship remain unresolved. The proposal improves editable paragraphs without claiming full Requirement grouping or hierarchy.

## 1.4 Table structure remains a separate failure

Visual inspection of retained Interpretation p. 19 confirms a two-column `Indicator:` / `Requirement:` header and rows with numbered left cells and multi-paragraph right cells. Current candidate instead has a header-only 1×16 table with two nonempty cells; the body is emitted as independent text lines. The second header on p. 20 has the same 1×16 failure. Farm also produces 1×8 tables for the single `Indicators:` band, and 1×14 / 3×18 tables for colored criterion headings. One Farm heading includes hidden native text documented in `../structure-diagnostic/README.md`.

Mechanism: `_pdf_tables` uses raster `detect_table_boxes` crops and `_grid_positions` whose vertical morphological kernel is `max(10, crop_height//6)`. Shallow colored headers admit glyph-height strokes as alleged column rules. The crop never covers the borderless body; `_merged_cell_specs` cannot recover body rows outside that crop. Simply applying table continuation assembly cannot repair a fabricated 16-column header.

Existing `assemble/table_assembler.py::_recover_captioned_header_only_tables` requires an explicit `Table N` caption and an already-correct two-column grid. `parsers/table.py::_split_profile_requirement_spans` also requires exactly two columns and a learned profile. Their preconditions fail here, so they are not a safe automatic reuse. A next table experiment should prove stable rule geometry independently of glyph strokes and preserve all native fragments; it must not delete hidden text or infer a table solely from a domain keyword. No table product edit is proposed from this evidence alone.
