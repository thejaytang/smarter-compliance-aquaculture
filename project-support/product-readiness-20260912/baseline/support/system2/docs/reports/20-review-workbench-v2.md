# Review workbench v2 acceptance record

Date: 2026-09-09. Scope: human review organization, evidence presentation, indexed persistence, full-text Excel and the System1 handoff. PDF extraction accuracy is excluded.

## Delivered behavior

System1 and System2 each expose Pending review and Review history. System2 Pending review has two primary queues: **Content proofreading** and **Requirement judgment**. Counts are mutually exclusive; the second queue requires content and dependency acceptance. Waiting dependencies have their own count. Task subtypes cover text fidelity, structure/location, classification, coverage, and an original-source issue handoff to System1. Weekly checks remain accessible inside review.

The task question, primary reason, actual confidence/threshold and machine proposal precede the comparison and action. Missing scores remain unknown. Normative wording in titles, notes and context is not excluded by format alone. Editors open for the selected action; applied corrections require another content check. Source-region corrections preserve original text and references. Each resolved checklist finding is retained separately; unresolved findings stay pending. Drafts, requests and application receipts remain separate. The System1 rating buttons no longer auto-submit. Original-source reports reuse an existing open source task, retain prior reports and return the same receipt on replay; an isolated check retained 31 pending tasks before and after replay.

HTML evidence comes from the hash-bound original with scripts, remote resources and active embeds stripped, CSP restrictions and an opaque sandbox iframe. Optional local Chrome screenshots are cached by original hash, location and renderer version. Missing resources and first-viewport limits are disclosed. PDF crops use explicit coordinate names and full-file context remains available. XLSX ZIP-part cell locations resolve through the original workbook relationships; previews include formulas, saved caches, merged ranges and hidden state. These previews do not claim independent parser accuracy.

## Migration and preservation

The production-copy migration verified all **38 source identities, 33,563 original units and prior human history**. Every old unit is retained directly or mapped to a complete source-position group member with unchanged literal fields. The resulting production database contains **14,986 grouped units and coverage checks**. CS002 changed from 9,135 fragments to 1,698 grouped/coverage units. PA001 has 140 units. All production human decisions and published Requirements remained zero; browser test acceptances exist only in isolation.

Writers were stopped at a checkpoint with no running/queued parser task. Worker and export locks were held during backup/migration. Evidence:

- `runtime/workflow/migration-20260909T144910Z/before.json`
- `runtime/workflow/migration-20260909T144910Z/receipt.json`
- `runtime/workflow/workflow-before-v2-*.sqlite` exact database backup referenced by the receipt
- `tmp/review-v2-final/migration-validation.json` production-copy preservation checks

The normalized database uses indexed review units, local dependency edges, history and deliveries; document rows hold metadata. It was integrity-checked and compacted to approximately 328 MB. Existing originals, Canonical files, Gold and baselines were not modified. A display-only refresh replaced 271 stale PDF table JSON titles with literal cell text; old/new titles are retained in `runtime/workflow/migration-20260909T144910Z/derived-title-refresh.json`, with unit data and decisions unchanged. System1 source and historical business sheets are unchanged; Instructions now describes explicit submission, and Machine confidence was added. The old runtime/acceptance statements in earlier reports are historical, not current state.

## Performance and runtime evidence

Actual loopback HTTP reads on migrated production data, 20 requests each while the background service was running:

| Operation | p95 | Median |
| --- | ---: | ---: |
| CS002 paged list | 0.353 s | 0.300 s |
| Single-unit detail | 0.355 s | 0.306 s |
| 50 distinct details sampled from 14,986 units | 0.647 s | 0.226 s |
| Ordinary guarded draft persistence, isolated copy | 0.542 s | 0.506 s |

The isolated decision benchmark replayed all 20 requests and received identical receipts. A separate 30,001-row test prevents fallback to whole-document hydration and asserts bounded list/detail read time. Current real grouped data contains 14,986 units; the original fragment corpus contains 33,563. Do not describe the grouped real benchmark as 30,000 independent grouped items.

Lists contain 50 summaries and chapter metadata, not body/structure/images. The measured CS002 list was approximately 82 KB. A detail cache is bounded to 32 entries, prefetches the adjacent unit, and discards stale navigation responses. Cached render timing is exposed as a DOM diagnostic for browser verification; PA001 § 1 measured 0.80 ms for cached text rendering. Original evidence has a separate eight-entry client cache. The mixed-detail benchmark is retained in `tmp/review-v2-validation/benchmark_mixed.json`. Single-unit writes update only changed rows and real dependent records. Excel runs in a separate background worker; the normal download returns the last generated, version-labeled snapshot. The compatibility fresh-export route is retained.

## Validation

- System2: 602 tests passed, one missing PDF sample skipped; new row-store, original-hold, stage-routing, partial-issue and evidence-location regressions passed. Exact outputs in `tmp/review-v2-validation/system2-regression-final.txt` and targeted test runs.
- System1: 83 tests passed; Workbench: 21 tests passed; frontend: 17 tests passed.
- Browser on isolated PA001: original snapshot, correction, content acceptance, Requirement classification, receipt and history; one incremental `add` event and source still incomplete. Dependencies were prepared as explicitly labeled test-only decisions, not production fidelity acceptance.
- Browser on production: 2-stage queue counts, source/chapter navigation and read-only evidence. CS002 content=1,698, Requirement=0, waiting=0 immediately after migration.
- Original HTML sanitization, exact XLSX worksheet/range and PDF crop tests; independent/stale edits, repeated requests, protected drafts, threshold changes and delivery invalidation are covered by regression.
- Excel: 40 worksheets (38 sources plus index/guide), full-text order and continuation rows; Open XML validation passed. Native Excel opened the final isolated export and displayed the source index and CS002 sheet. Final file approximately 4 MB. Technical IDs/counts reference the database rather than repeating entire dependency/member JSON for every table row.

## Boundaries that remain explicit

Seven registered HTML originals still lack usable bodies: PA011, PA012, PA039, PA041, PA042, PA044, PA058. They remain failed/blocked and can be reported to System1; this release does not fetch replacement originals. Production Requirement acceptance is not complete. Uncertain grouping or footnote relationships remain reviewable; grouping does not assert source correctness. Initial confidence thresholds remain 95%, and uncalibrated results require human review.

XLSX evidence tests use a reference/isolated fixture; the current 38-source INCLUDE batch has HTML and PDF, not XLSX. No excluded XLSX was started as a production task. Real Norwegian PDF extraction accuracy, independently labeled score calibration, live provider effectiveness and a System3 consumer remain unaccepted. System3 only exposes the input/status contract and is not marked as having performed enrichment.
