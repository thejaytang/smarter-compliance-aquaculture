# Generated source Excel and source-version status checkpoint

Date: 2026-09-10. Decision: **CONTINUE** for the bounded output and synchronization checks. Overall source-fidelity and Requirement acceptance remain incomplete.

## Source Excel repair

The three confirmed causes were invalid zero-DPI print settings, duplicated freeze-pane selections accumulated by repeated confidence-sheet rebuilds, and font-property ordering rejected by OfficeCLI's Open XML validator. The generated view now removes invalid print defaults, retains one selection per pane, rebuilds confidence selections idempotently and writes the supported font-property order. Unknown font elements stop publication. Font values, cell values, formulas and all other package parts survive the ordering transform.

The first row-height estimate still clipped PA012 in native Excel because Excel breaks at the source-ID hyphen. That failed observation changed the estimate to reserve an extra wrapped line. The final native check showed all 135 characters of PA012, the current longest managed filename, including its final `.html`, and also showed PA004's wrapped filename. The protected copy opened without a repair prompt and was closed without saving. This is desktop evidence for the current generated source register, not a guarantee for arbitrary future files or every possible printer.

Normal source output uses renderer 5, database revision 1, SHA-256 `847305b51a2a1b1bf92a4c8e6a3e440675fd4961a01e853cd84d5aeb88ab3749`. OfficeCLI reports zero schema errors, down from the 22 retained baseline errors. Full business readback, all 73 original-file identities and database/history preservation passed. The immutable import workbook remains untouched. The generated output is still a one-way view; no Excel readback was added.

System1 passed 108 checks; the final extra-line adjustment also passed its focused preservation test. The test verifies cells/formulas, font properties, idempotent row sizing and unchanged non-style package parts. The earlier failed StyleProxy comparison was corrected to compare actual font values rather than wrapper identity. The final normal artifact separately passed OfficeCLI and native inspection.

## Source-version synchronization

System2 now publishes a replaceable checked-source marker during controlled reconciliation. Excel metadata includes both the registry digest and its kind; the Read Me sheet distinguishes `sqlite_snapshot` from a workbook-file identity. The workbench compares source, review-event and policy versions. A source-only change makes output pending even when A/B review events do not change. Missing, failed or older-than-30-second source checks show unknown. The 30-second value is an operational freshness default, not a source-accuracy score or a user acceptance threshold.

The existing background coalescing, bounded maximum wait and retry mechanism is reused. No new scheduler was enabled. Page reads use the small saved marker rather than waiting for a full handoff or workbook reconstruction. Last successful output remains downloadable with its version/hash while a newer snapshot is pending or failed.

The complete isolated workbench changed only CS001 issuer metadata, injected an Excel lock, observed pending/failure, removed the lock, observed automatic convergence, then restored the original issuer through another versioned save. The old Excel bytes survived the lock. Failure appeared after 4.312 seconds, convergence after unlock took 17.019 seconds, and the restoration synchronized in 19.746 seconds. Source revision advanced 10 to 12, retaining both engineering events. Every source value was restored; all operation rows and all System2 workflow tables remained unchanged. This is one injected-error observation, not p95 or a natural-error accuracy measure.

System2 passed a fresh 693-case suite with one skip (692 passed); Workbench passed 26 checks. Tests cover source-only changes without review events, digest kind/readback, failed/missing/stale checks, cached prior output, failed-check recovery and preserved review state. The failed initial export assertions targeted the wrong guide/header cells; the final assertions inspect the actual Read Me fields and source-title banner.

## Normal integration and remaining scope

The verified normal service was drained, backed up and reloaded on port 62742, process 52480, instance `S0gomkjPAzYpcg_5klPQIfunPBnpdYPg`. All related database table contents were preserved except ordinary new Workbench sessions. Normal source counts remain 87 total, 30 pending, 96 historical operations, 38 included and 24 excluded. No normal source decision was submitted. The actual System2 browser view showed saved event 71 and synchronized Excel event 71; the API also confirmed matching source digests and `sqlite_snapshot`. Source Excel and System2 output remained separate owned snapshots.

The B provisional parent/subitem policy, independent real-scan/cross-page references, calibrated held-out A/B evaluation, human effort, new weekly 5/20/5 sampling and broader performance remain unfinished. Source discovery, external models, retrieval, publication and scheduler authorization boundaries are unchanged.

## Evidence

The local evidence and stopped-write recovery package are in [`runtime/output-fidelity-20260910`](../runtime/output-fidelity-20260910): `office-final.json`, `normal-live.json`, `source-sync-proof/`, and `reload-backup/manifest.json`. The prior `normal-output.json` records renderer 4 and its failed PA012 height observation; renderer 5 above is the accepted bounded layout. System2 logs are [`source-version-final-regression.txt`](../../../system2/runtime/source-version-final-regression.txt). Workbench evidence is [`source-version-workbench-final.txt`](../../../workbench/runtime/governance-db-pilot/source-version-workbench-final.txt). Native observations are recorded above; generated structure or regression results alone were not treated as visual or source-fidelity proof.
