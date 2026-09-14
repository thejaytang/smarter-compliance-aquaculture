# Product parser /6: inconsistent-grid recovery

**Implemented in source and verified in isolated System2 workers.** Parser `/6` preserves the `/5` HTML numbering fix and adds the reviewed native-line grid consistency guard. It rejects an inconsistent grid into unchanged positioned-text fallback, retains the full rejected proposal and source evidence, and exposes a located unresolved range. It does not change the native backend, use richer word substitution, add models, or adopt business content.

## Product behavior

The policy/configuration hash explicitly includes `native-line-grid-consistency/1`, **1 point** of geometry tolerance and a **>=25%** crossing-line rejection ratio. The denominator remains original nonempty native lines whose centers belong to an actual merged cell. Boundaries hidden inside a merged cell are ignored. This DEV-calibrated rule is a consistency check, not a source-visibility or universal table classifier.

Zero evidence or missing/multiple cell ownership causes **single-region rejection with uncertainty**, not an exception that loses the rest of the document. The rejection artifact retains the entire candidate table, cell rectangles, raw line payloads, ownership uncertainty, crossing measurements and exact fallback lines. Accepted grids retain compact decision summaries. Rejection data is passed directly to the caller before being written; the parser does not reread a newly written artifact just to construct its result.

Every rejected region has `code: table_grid_inconsistent`, a specific reason, source bbox/page references, rejected-candidate ID, evidence-file reference and readable warning. Original source bytes and the native evidence remain untouched. New candidates stay separate from existing personal/master work and require the existing explicit adoption/confirmation flow.

## Verification

**159 tests passed, zero failures/errors/skips**, across all 12 `test_material*.py` modules, using an isolated temporary root. Nine new cases cover true merged cells, the exact 1-point rounding boundary, the inclusive 1/4 ratio boundary, zero/missing/multiple ownership, and an actual two-page PDF where rejected-grid text/refs survive while a real table on the second page remains usable. Existing HTML suffix, reader, material-service, collaboration, provenance and recovery checks remain green.

The same seven frozen DEV documents and 15 proposed grids reproduce the reviewed isolated-copy outcomes exactly:

- Six wrong fine header grids rejected; **14 exact native positioned lines restored**.
- Eight real table regions retained with identical payloads.
- All original native page evidence and all nonrejected primitive payloads/order/refs preserved.
- All candidate blocks exactly match the corresponding isolated-guard candidate; the revised uncertainty messaging/provenance is explicit.
- All six rejected ranges have located unresolved entries and matching warnings.
- The known 1×1 figure false table is retained as a failure.

Existing engineering matches remain unchanged: source segments Farm **18/25**, Interpretation **8/12**, Audit **48/79**, Salmon/Cod **20/21**. Fixed critical/marker matches and formal/clause checks do not improve or regress. Audit retains 22 unlocated critical labels as `UNMEASURED`; Salmon/Cod has no labelled critical-phrase denominator. Synthetic table-cell diagnostics remain multicolumn **6/6**, cross-page **12/12**, borderless/figure **0/10**. All source and annotation hashes remain unchanged.

These results establish bounded recovery/retention behavior, not the overall extraction-quality thresholds. General PDF structure, missed borderless tables, erroneous rows inside otherwise retained tables and hidden native Criterion text remain open. No reserved output was inspected or used for tuning. Last measured `/4` reserved quality remains **FAIL**; independent `/6` verification is **UNMEASURED**.

## Version, loading and recovery

Current parser SHA and all receipts are in [summary.json](summary.json). The exact prechange `/5` parser and existing quality-test bytes are retained with hashes in [prechange.json](prechange.json). The only changed product functions are `_inspect_pdf_table_grid` (new), `_pdf_tables` and `_pdf_blocks`; `/5` HTML functions have identical ASTs. A new test module owns the guard regressions.

The code has been loaded by isolated parser workers. This subtask does not restart or switch the normal Workbench service, mutate its state, or replace an existing candidate/main revision. No Workbench/UI file was changed. Restore the prechange parser from its retained bytes only as a reviewed rollback, preserving this report and new candidate evidence; do not replace business originals or history.

**Full System2 regression has not been rerun**, pending the coordinator's integrated source freeze. The historical 1072-test result binds `/4`, not `/6`. Browser integration, independent quality verification and Windows acceptance remain separate checks.

Evidence: [targeted test command/environment](targeted-start.json), [complete test log](targeted.log), [JUnit](targeted-junit.xml), [fixed DEV source/config freeze](outputs/freeze.json), [loaded source fingerprints](outputs/experiment-freeze.json), [primitive/ref/order verification](outputs/verification.json), [fixed annotation assessment](outputs/assessment.json), [summary and isolated-copy comparison](summary.json). The earlier [six-range preview](../fallback-experiment/unresolved-ranges.html) illustrates the matching fallback blocks but is explicitly an isolated `/4` preview, not a `/6` browser check.
