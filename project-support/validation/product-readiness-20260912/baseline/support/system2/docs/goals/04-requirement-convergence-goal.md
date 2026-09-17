# Requirement-First Reliability and Iterative Convergence Objective

## Final objective

Converge on a Requirement-first PDF parser for English/Norwegian legislation, general regulations, standards and audit manuals. Recover nearly all Requirement-defining information faithfully as reviewable, traceable structured objects, rather than merely fluent Markdown.

This objective remains active until every completion gate is met. Accepted page windows, one successful template or visually convincing Markdown cannot replace those gates.

## Working definition of Requirement

A Requirement is a complete normative unit establishing obligation, prohibition, permission, applicability or a compliance criterion. It may arise from:

- Numbered Indicator/Requirement tables;
- Normative prose, lists or Appendix procedures;
- Short values such as `Yes`, `None` or `≤3` that complete an Indicator's meaning;
- applicability、scope、condition、exception、exemption；
- Footnotes, defined terms and cross-references directly changing its meaning;
- Nested clauses and `and/or` logic within the Requirement.

Guidance, rationale, evidence examples, client actions and auditor actions are not the Requirement itself. Where required by the source, retain them as separate linked fields; never mix them into `normative_text`.

Each Requirement must express at least:

```text
requirement_id
source_document / source_authority
criterion_path / hierarchy
indicator_text
requirement_value
normative_text
subject
modality
negation
applicability / scope
conditions
exceptions / exemptions
logical_structure preserving and/or and nested clauses
thresholds / units / dates
cross_references / footnote_qualifiers
client_actions[]
auditor_actions[]
source_segments[] with page, bbox and native/OCR evidence
source_anomalies[]
validation_flags[]
```

Equivalent Canonical field names are allowed, but all listed semantics must be preserved. Model inferences cannot overwrite original-evidence fields.

An accepted Requirement is correct only when identity, direct source text and every applicable critical semantic field match Gold. Matching only `requirement_id` counts as inventory match, not `accepted_result_precision`. Unnumbered units require stable identity from source location, normative boundaries and document structure.

## Current test corpus

The four current `data/inputs/` PDFs are English with native text layers, representing four structure families:

1. `ASC-STD-001-ASC-Farm-Standard-V1.0.1-Aug-2025.pdf`
   - Modern narrative standard: Indicators are Requirements, with long clauses, exceptions, exemptions, Appendix procedures and deep numbering.
2. `ASC-INT-001-ASC-Farm-Standard-Interpretation-Manual-V1.0-May-2025.pdf`
   - Repeated Requirement, interpretation, evidence, auditor guidance and resource sections, testing type separation and distant associations.
3. `ASC-STD-010-ASC-Salmon-and-Cod-Standard-V1.5-Oct-2025-1.pdf`
   - Legacy two-column tables: a complete Requirement often combines Indicator description, short right-column value, applicability and footnotes.
4. `download-module-691-ASC-Salmon-Audit-Manual_v1.4.pdf`
   - Audit matrix requiring separation of Requirements, Required Client Actions and Required CAB Actions.

Norwegian is part of final scope but absent from these four files. English work may proceed, but completion requires at least one real Norwegian regulatory/standard PDF passing holdout. Cover `§/§§`, `kapittel`, `ledd`, `bokstav`, `skal`, `må`, `kan`, negation, conditions and exceptions.

## Small-sample iteration constraints

1. Routine iterations must not parse complete files. Whole-document work is limited to inexpensive native/layout profiling, Requirement-number inventory and risk scans, without full rendering, OCR or block pipelines.
2. Test one explicit failure hypothesis per round using two to four windows, each one to four pages and usually no more than 12 pages total. A cross-page case may justify a six-page window.
3. Each round includes:
   - An active sample for diagnosis and repair;
   - A holdout not used to design that round's rules;
   - A cross-document holdout at least every third round;
   - Once prediction differences are inspected or used diagnostically, permanently reclassify that holdout as active regression and record it in the irreversible sample-history registry;
   - In the final three consecutive rounds, at least one PDF with no pages previously used in rule design. New pages from the same PDF show within-document generalisation only. Prefer the real Norwegian file as document-disjoint holdout.
4. Freeze window Gold before parser changes. Never manufacture success by editing Gold, lowering thresholds, removing difficult cases or routing every error to review.
   Final holdout and document-level acceptance Gold require independent second review, adjudication of disagreements and freezing. Revisions create new versions with reasons; never overwrite historical scoring evidence.
5. Use this cycle:

```text
Low-cost whole-document profiling
→ risk-driven sample selection
→ freeze Requirement Gold
→ run current parser
→ record symptom and error class
→ smallest discriminating experiment
→ root-cause diagnosis
→ general repair
→ active-sample and untouched-holdout regression
→ update convergence ledger
→ choose the next failure with highest information value
```

6. Do not repeatedly random-tune the same failure. Repairs require evidence, applicability boundaries, regression risks, minimal unit tests and real-PDF regression assertions.
7. Use native-first for native PDFs. OCR is for scanned pages, damaged text layers or independent-evidence conflicts. LLM/VLM is not the default text source and must not invent source content.
8. Critical-text repair requires at least two independent evidence sources. Otherwise return `review_required` / `abstain`, never silent acceptance.
9. Do not run generic external PDF benchmarks. Evaluate internal Requirement Gold, current real files and subsequent English/Norwegian regulatory/standard files only.
10. No commit/push, external transmission of document contents or overwriting `data/inputs/`.

## Initial risk-driven sample pool

Use only a small subset per round. Retain successful windows as regression or untouched holdout as appropriate; do not run the full pool each round.

| Document | Preferred PDF pages | Acceptance focus |
|---|---|---|
| Farm Standard | 28–29 | Basic Criterion/Indicator baseline and guidance separation |
| Farm Standard | 31–32 | Cross-page `1.4.2`, `a–f`, second-level bullets and applicability |
| Farm Standard | 65–66 | `≤34` / `>34`, negation, only, exceptions and symbol fonts |
| Farm Standard | 105–108 | Deep `4.1.1.*` numbering, page spans, scope and source anomalies without `shall` |
| Farm Standard | 198–200 | Appendix formulas and normative procedures without Indicator rows |
| Interpretation Manual | 19–21 | Long Requirements, several clauses per page and table boundaries |
| Interpretation Manual | 80–85 | Cross-page tables, local headings and Requirement/interpretation separation |
| Interpretation Manual | 103–106 | Values, percentages, comparisons, bullets and footnotes |
| Interpretation Manual | 324–327 | Deep `4.1.1.*` hierarchy and complex applicability |
| Salmon/Cod Standard | 18 | Complete Requirement requires `Indicator text + Yes` |
| Salmon/Cod Standard | 19–20 | Continuation without repeated headers, thresholds, units and multiple `or` clauses |
| Salmon/Cod Standard | 31–33 | Salmonids/Cod applicability and cross-page rows |
| Salmon/Cod Standard | 57–59 | Cell subitems, `None` / `≤3` and footnote qualifiers |
| Salmon/Cod Standard | 87–88 | Open/semi-closed/closed-system scope transitions |
| Audit Manual | 1–3 | Four physical regions, three semantic regions and cross-page continuation |
| Audit Manual | 11–12 | `Yes` / `<1.2` / formula `or` / `N/A` |
| Audit Manual | 17–19 | Dense Requirements and client/auditor-action separation |
| Audit Manual | 22–24 | Rapid Criterion transitions and short-value Requirements |
| Audit Manual | 29–30 | Additional Requirements, system applicability and internally numbered conditions |

## Fixed error taxonomy

Assign every failure to at least one stable category:

1. Requirement omission / false positive；
2. Requirement boundary split / merge；
3. Incorrect ID, Criterion or hierarchy;
4. Incorrect Indicator/short-value pairing;
5. Missing applicability, scope, condition, exception or exemption;
6. Incorrect modality, negation, only or and/or logic;
7. Incorrect thresholds, units, dates, formulas or comparisons;
8. Incorrect footnote/cross-reference association;
9. Mixing Requirements, guidance, client actions and auditor actions;
10. Cross-page table, row or repeated-header errors;
11. Missing/incorrect provenance;
12. English / Norwegian language-specific failure；
13. Unauthorised correction of source anomalies instead of faithful preservation.

## Per-round checkpoints

Conclude each round with one of:

- `CONTINUE`: active and holdout pass; move to the next failure class;
- `ADJUST`: the approach remains valid, but holdout reveals parameter/boundary issues;
- `BACKTRACK`: a repair causes regression; return to the last reliable implementation;
- `PIVOT`: the structural assumption fails and needs replacement;
- `STOP`: further work on this branch has insufficient information value.

Update a concise convergence ledger with samples, Gold counts, error classes, root cause, changes, active/holdout results, unresolved risks and next experiment. A chronological log does not replace diagnosis.

## Completion gates

All gates must pass before marking the goal complete:

### A. Gold coverage

- Stratified Gold across all four current English PDFs, covering at least 200 Requirement units: at least 25 in the 30-page Audit Manual and at least 40 in each other file.
- At least 20% of units are frozen holdout never used for rule design.
- At least one real Norwegian regulatory/standard PDF in Gold, with at least 40 units and Norwegian clause structures.
- Gold covers every applicable category in the 13-category taxonomy.
- Final holdout and document-level Gold have independent second review and adjudication.

### B. Requirement quality

- `requirement_instance_recall ≥ 99.5%`, with no document below `99.0%`;
- `accepted_result_precision ≥ 99.5%`；
- Accepted results achieve `100% exact match` for criterion_path/hierarchy, indicator_text, requirement_value, normative_text, subject, modality, negation, applicability/scope, conditions, exceptions/exemptions, logic, thresholds/units/dates, references, footnote qualifiers and applicable associated/client/auditor actions. Inapplicable fields must match Gold emptiness; empty fields cannot evade evaluation;
- No silently missing numbers in Requirement sequence/inventory;
- Zero mixing of Requirements, guidance and client/auditor actions;
- `100%` page, bbox, segment and original-evidence coverage for every Requirement;
- Explicit abstention for unreliable cases, with `100%` critical-conflict recall;
- At least `98%` automatic acceptance coverage on born-digital English samples; mass review routing cannot manufacture success.

### C. Generalisation and stability

- Three consecutive rounds of new frozen holdout satisfy all gates, covering at least three structure families and both English/Norwegian;
- Those rounds include at least one new PDF from another publisher never used for rule design;
- Every new real failure has targeted regression; full unit/integration tests have no unacceptable decline;
- Repeated runs produce identical Requirement structural fingerprints;
- No dependence on ASC filenames, fixed pages, fixed Criterion names or hard-coded Requirement text.

### D. Final document-level acceptance

Routine iterations prohibit full parsing. Only after A–C pass may one final document-level acceptance run process the four English PDFs and Norwegian holdout sequentially in sections, without parallel full-file processing. Reconcile with an independent inventory covering numbered and unnumbered prose/list/Appendix normative units, section coverage, source pages and stable identities. Number continuity alone is insufficient. Any silent omission, critical-field error or structural mixing returns the goal to iteration.

## Resources and stopping rules

- Prefer small samples with high **expected value of information**. Page counts and edit counts do not measure progress.
- Retain reusable native/OCR caches without accumulating redundant unused whole-page outputs.
- If verifiable account capacity is available, pause further heavy runs below 30%. If unavailable, do not guess or claim this threshold was applied.
- If an experiment exceeds expected duration, inspect checkpoints/caches before expanding work; do not automatically run the full file.

## Current operational state

Current checkpoints, unblinded samples, irreversible sample history and the next informative experiment belong only to `docs/reports/04-requirement-convergence-ledger.md`. This document owns stable objectives and acceptance contracts.
