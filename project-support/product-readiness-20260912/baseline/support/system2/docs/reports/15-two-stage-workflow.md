# Two-stage workflow implementation evidence

Date: 2026-09-09. Scope: local code and isolated validation; no repository publication, provider enablement or production human acceptance.

## Implemented

- Shared browser jobs backed by System2 SQLite; explicit start, bounded single-worker PDF processing, pause/resume/retry/reprocess, versioned evidence and recoverable request receipts.
- Content/structure acceptance before dependent Requirement classification, complete residual coverage, original-boundary corrections, immutable human overlays, source/policy invalidation and incremental System3 events.
- One editable workbench threshold policy with owner mirrors. Tests exercise 95% → 98% for 96% machine results, lower-threshold restoration, human precedence, drafts/reports and task deduplication.
- System1 source-version-bound five-dimension evidence assessment, exact snapshot traceability proof, optional proposals and machine admission constrained by existing source checks. Named human decisions and draft/report holds remain protected.
- HTML and XLSX reuse their Canonical and source-records formats. PDF numbered table rows now reference Canonical cells directly; legacy domain proposals remain diagnostic. Unsupported-format conversion preserves original/copy lineage.
- Disabled-by-default JSON suggestion adapters with evidence allowlists and limits; independently scoped calibration-artifact support; service-owned weekly QA and inactive System3 consumer state.

## Regression and bounded original checks

The initial complete regression after integration passed System2 555 tests with one skip, System1 82 tests and Workbench 19 tests. Additional fixes and targeted checks are recorded in the final regression receipt below. The System2 warning is the existing Starlette/httpx deprecation; optional backend absence remains a skip, not accepted capability.

The registered PA001 Norwegian HTML was started in an isolated browser workbench, producing 150 reviewable units. No unit auto-passed uncalibrated scores. Original text, empty-field and residual issues remained visible. Browser decisions use an explicitly isolated test operator/session and are not production source approvals.

A bounded real English CS004 source check used printed pages 20–21 (zero-based 19–20), SHA-256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. The native result stayed `review_required` with `document_window_only`. The new projection exposes 38 units including numbered rows 2.1.3 and 2.1.4. For 2.1.3, `≥ 2` remains in the requirement-value column and is absent from the indicator body. This catches the observed older domain candidate's column contamination; it does not claim all rows, footnotes or a full PDF are correct.

The GLOBALG.A.P. reference XLSX is tested only in isolated storage/registry. It is not a current production INCLUDE task. Structural parser tests retain unknown cells, merged/hidden regions and formula/cache evidence rather than treating unsupported layouts as completed Requirements.

Local diagnostic evidence: `system2/tmp/implementation-20260909/`, including `pdf-pages-20-21/workflow-check.json`, `html/` and the isolated `browser/` workspace. These local runtime artifacts are excluded from Git and are not substitutes for a shared release receipt.

## Open acceptance gates

- Independently labeled, representative calibration and held-out accuracy/recall/field/relation acceptance per format and language remain absent. No synthetic score fixture is activated in production.
- Real Norwegian PDF acceptance is missing. The English two-page check is insufficient for that claim or for complete cross-page robustness.
- Complete current INCLUDE processing is not claimed. Missing originals and incomplete source content stay explicit blockers; only user-started jobs run.
- No external API is configured or tested live; gateway failure tests prove fallback only.
- System3 has an input/state contract and readable feed; no semantic worker, Site Model consumer acceptance or acknowledgment is claimed.

Checkpoint: CONTINUE for offline engineering use and bounded human review; ADJUST before expanding automated acceptance. Keep the data/provider/consumer gates separate from regression success.

## Final regression and activation receipt

Final local regression: System2 **562 passed, 1 skipped**, System1 **83 passed**, Workbench **19 passed**, frontend state suites **14 passed**. Script syntax and all relative links in 16 changed entry/state/contract documents passed. No new dependencies or shared environments were installed.

Rendered browser checks covered real HTML start and safe original view, named content/classification decisions, one incremental Requirement while the source remained partial, a subsequent correction suspending that item, saved drafts/history, policy revision 2 (98% content) to revision 3 (95%), PDF 2.1.3 opening page 20 with separate columns, and the reference XLSX's original sheets/cells. The XLSX produced 2596 pending units. Desktop inspection at 1280 px found no horizontal overflow. These are isolated workflow tests, not human regulatory approvals or mobile acceptance.

The normal local workbench was reloaded after verifying no queued/running/waiting System1 submissions. Its port and existing history were preserved. Readback confirmed **87 sources**, **96 historical records**, unchanged applied request identities, **zero newly started production parsing jobs**, and all four initial policy values at 95%. The production registry SHA-256 remained `7beb2c9d63afcf693f41b3440b3ed3bb3cb7dd350b149480957d4f2901b8d041`. Exact local receipts are `system2/tmp/implementation-20260909/production-reload.json` and `browser-checks.json`. No original, Gold or old parser output was overwritten.
