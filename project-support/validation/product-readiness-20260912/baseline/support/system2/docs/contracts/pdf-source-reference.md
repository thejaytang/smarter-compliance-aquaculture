# PDF source reference and error assessment

Status: the bound diagnostic evaluator, source-first reference collection and frozen source/output/finding assessment are implemented in the shared workbench. Complete-reference confirmation/revision and matched-finding assessment have isolated engineering-browser evidence. Independent qualification, actual independent-human references and representative quality acceptance remain unverified. The user paused the goal after checkpoint 46; do not begin further implementation without explicit resume. No file field or ordinary confirmation confers independent-reference or release authority.

## Evidence sequence

1. Bind a study case to the governed original hash/version, selected PDF page and any supporting context pages. Record document family, purpose, selection rule and previous exposure. Keep natural, seeded and synthetic cases separate. Existing development pages and exposed Gold do not become held-out by changing a label. Qualification for calibration or final acceptance needs its own exposure/source-family evidence.
2. Prefer a source-first reference pass in the existing workbench. Show the full original without extractor-position overlays or machine-filled reference answers. Capture original content regions, exact text, role, table cells/grid/spans, printed note markers and typed relations, including content with no extraction record. Preserve photos/diagrams as original images with caption/location; scanned body remains in text scope. Record prior output exposure/assistance, unresolved ranges and the actual operator. Prior exposure is disclosed, not erased.
3. Save drafts in System2's owning database. A submitted source reference must freeze a version with source hash, selected/supplementary scope, operator, time and evidence. Revisions append history and invalidate dependent assessments. A correction to a reference is a documented revision requiring reassessment; it cannot silently replace a previously scored answer.
4. Audit extraction against that source reference before revealing verifier findings where practical. Record all errors, including errors without output records or machine alarms. Audit content, structure and relationships; counts of cells/merges or matching text bags do not establish their correctness. Record correct/incorrect/unknown scope and supporting context explicitly.
5. Adjudicate every frozen verifier finding against the error inventory: primary match, duplicate, false positive or unresolved; separately record whether its location lets the reviewer find the error. Generic or localized unverified scope is reported as scope/workload, not automatically credited as an error detection. Resolve disagreements with an identified adjudicator and retain prior interpretations.
6. Authenticate the reference and assessment receipts from the owning database before independent evaluation. Verify actor/source/revision, completeness, assistance/exposure, sample qualification and any necessary adjudication. Workbench events record the declared human action; Agent-authored engineering controls are not actual human confirmations. Ordinary content approval, Excel output, local JSON fields or a claimed reviewer name are insufficient substitutes.

Steps 1–5 now have the bounded development-task implementation described below. Step 6 remains the independent qualification and acceptance gate. The shared workbench remains the only normal human entry point. Engineering JSON fixtures are not human confirmations or Gold.

## Shared-workbench reference collection

In System2 Content proofreading, **PDF reference samples** opens a source-first editor. Tasks bind one primary PDF page and up to two supporting pages to a current governed source hash. All new tasks are `development` and `unqualified`; no held-out or calibration assignment is inferred. The editor shows the original alone, with only the reviewer-entered reference regions highlighted. It supports exact text, roles, tables/cells/grid/spans and footnote, caption, continuation, reading-order and context links.

`GET /api/system2/references` reads task lists or details without creating reference tables or exporting Excel. `POST /api/system2/references` uses the named workbench session and actions `create`, `save`, `confirm` and `revise`. Source-reference tasks/events belong to System2's workflow database; ordinary review units, decision/delivery history, Canonical and Gold are not rewritten. The request UUID and payload bind saved receipts. Guards reject changed references; new writes recheck eligibility, source bytes and selected-page geometry. A saved receipt can be replayed without reacquiring an unavailable original.

The browser retains unsaved edits and uncertain requests, while **Save reference draft** persists incomplete forms in the database. A draft from an older saved version is retained separately for comparison. Confirmation rejects unfinished editor fields, incomplete table grids, inconsistent links, missing required text, unknown exposure, incomplete original survey or unresolved questions. It creates a versioned candidate and an append-only before/after event. **Reference saved · assessment pending** does not mean independent reference qualification, A/B acceptance or delivery. A reasoned new revision preserves the prior candidate, clears the survey and marks assessment stale.

The source image remains available by its managed original/hash/page association rather than duplicating or replacing original bytes. Reference operations are study records, so they do not enqueue A/B Excel publication; normal correction/delivery operations retain the existing one-way Excel behavior. The assessment workflow is described below; independent qualification remains unfinished. [Checkpoint 45](../reports/45-source-reference-workbench.md) records actual browser scope, recovery tests and unverified interactions.

## Bound error inventory and finding adjudication

From a saved source reference, **Assess extraction and verifier findings** starts an assessment from the owning database and retained verification evidence. `GET /api/system2/assessments` reads lists/details; `POST /api/system2/assessments` accepts guarded `create`, `save`, `freeze_inventory`, `confirm` and `reopen_inventory` actions through the named workbench session. Browser fields cannot replace the frozen reference, effective records, verifier report, evidence class or actor. The original source and retained evidence digests must match; current checks must match the present effective output.

The `inventory` stage withholds the frozen verifier findings while the operator accounts for all original regions and output records, records errors including those with no output/alarm, and confirms the three scope dimensions. `freeze_inventory` checks completeness before exposing findings and entering `adjudication`. Each finding requires an error match, duplicate, false-positive or unresolved decision and an explanation, with location correctness for matches. `confirm` requires a complete diagnostic evaluator result and creates `assessment_saved`. Saving is not A/B acceptance or independent qualification.

Reopening a frozen/saved inventory requires a reason, retains prior body/report/history and keeps `findings_exposed` true. Reference/output/report changes make old assessment views stale and block new writes against them. Start a new assessment from current evidence; do not overwrite the older evaluated answers. Saved operation replay remains available if the original subsequently becomes unavailable. Assessment operations are separate study events and do not publish Excel. Diagnostic metrics remain distinct from independent metrics, which are still null.

[Checkpoint 46](../reports/46-bound-source-assessment-workbench.md) owns the actual synthetic-browser sequence, failures, separate control classes and preservation evidence. The user requested a pause after that checkpoint; further qualification/calibration work has not started.

## Bound diagnostic input

The offline entry point is:

```bash
PYTHONPATH=src .venv/bin/python -m pdf_extraction.evaluation.source_assessment_cli \
  --original /path/to/registered-original.pdf \
  --reference /path/to/frozen-reference-candidate.json \
  --assessment /path/to/error-assessment.json \
  --records /path/to/frozen-effective-records.json \
  --verification /path/to/frozen-page-report.json \
  --output /path/to/new-assessment-report.json
```

The command hashes the actual original, checks exact reference/output/report bindings, reads inputs and creates an exclusive output file. It does not write originals, annotations, Gold, workflow state or prior reports. It does not re-run the extractor or OCR. The existing [original-page verification](original-verification.md) remains the machine comparison entry point.

`pdf-source-reference/1` contains `source_sha256`, one evaluated page in `pages`, optional `supporting_pages`, `status`, located `regions` with unique IDs and a `page_survey`. Positions use zero-based page indices and positive PDF-point boxes in top-left origin. A complete page survey covers `content`, `structure` and `relationships`, with explicit unverified regions. Supporting regions supply context; a context-only error cannot enter the evaluated page's error denominator. This first evaluator is single-page; a future window aggregator must preserve unique cross-page error ownership instead of double-counting the same relationship.

`pdf-source-assessment/1` binds `source_sha256`, `reference_sha256`, `records_sha256` and `verification_sha256`; it records `evidence_class` as `natural`, `seeded` or `synthetic`. It contains all reviewed region/output IDs, reviewed dimensions, unresolved questions, located `errors` and `finding_decisions`. A finding decision's `id` is its ID in the frozen verifier report. Critical token errors cannot be downgraded below critical. Each error has a supported region and/or output identity plus an explanation; a missing original region can have no output identity.

The evaluator rejects changed originals/reference/output/report bindings, duplicate IDs, unknown error/finding associations and primary double-credit for one error. An incomplete original survey, omitted output/region review, unresolved finding or draft yields null diagnostic metrics. Source/assessment completeness declarations are checked for consistency; their truth and human independence are not authenticated by reading files.

## Metrics and denominators

| Diagnostic metric | Definition |
| --- | --- |
| Finding relevance precision | Primary matched findings plus duplicates / all adjudicated findings |
| Actionable finding precision | Primary matched findings / all adjudicated findings; repeated alarms receive no extra useful-issue credit |
| Verifier recall | Unique matched error IDs / all errors in the complete assessed original/output scope |
| Localized error recall | Unique error IDs with a correctly located matched or duplicate finding / all errors |
| False-positive and duplicate workload | Separate finding counts, alongside the number of unverified scope items |
| Per-category recall | Unique detected / all reference errors within each category; absent categories have null recall |
| Critical errors and misses | Explicit IDs for every critical error, and for those without any matched finding; an average cannot hide them |

A duplicate with better location can improve localization without increasing detection or useful-issue count. Empty denominators are null, not 1.0. Error inventory, original regions, output records and machine findings are distinct counts. There is no inferred negative-population denominator, automatic-processing rate, human-time estimate, CER/WER, extractor precision, source-grid accuracy or population confidence interval from this event inventory alone. Those need complete independently confirmed references and their appropriate units/design.

The report always keeps `independent_metrics: null` and `independent_acceptance: "not_assessed"` in this diagnostic implementation. Even an input claiming a named human and independent receipt cannot override that. Independent workbench qualification is a separate unfinished gate; a named local operation alone is insufficient. No release threshold changes are made; the current default threshold is not observed accuracy.

## Legacy evaluation

The generic feature evaluator remains a legacy regression mechanism. Its report/CLI explicitly labels independent source accuracy as not assessed. It excludes header/footer text, uses unpositioned cell/span collections and counts cross-page merged blocks; none of those establishes the corresponding source fidelity. Preserve existing historical metrics and synthetic regression uses. Do not feed them to this goal's independent quality acceptance as reference evidence.

[Checkpoint 44](../reports/44-pdf-assessment-denominators.md) records the observed perfect-score blind spot, implementation and incomplete real-source diagnostic. The [active rolling plan](../plans/pdf-verification-reliability.md) owns the next shared-workbench experiment.
