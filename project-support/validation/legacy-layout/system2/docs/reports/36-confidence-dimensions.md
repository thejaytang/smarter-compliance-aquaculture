# Required confidence dimensions and isolated artifact ownership

Date: 2026-09-10. Decision: **CONTINUE** for the bounded engineering changes; independent quality and whole-workstream acceptance remain incomplete.

## Verified behavior

A requires separate text, original coverage, structure/relationships and reading-order scores. B requires classification, original association and parent/subitem correctness. A missing, repeated or unknown dimension prevents automatic acceptance. The lowest supported dimension controls the stage; uncalibrated, invalid, missing-evidence or conflicting scores do not produce an overall confidence percentage. A human decision remains separate and cannot bypass an unresolved explicit blocker.

The workbench now displays all seven dimensions, their missing or supported state, the recorded method/calibration and original evidence. Actual normal HTML and isolated PDF review pages were inspected through the browser. Missing dimensions remain visible after human confirmation; no score was rewritten to 100%. No threshold or provider was changed.

The gate is versioned as `required-confidence-dimensions/1`. Source reconciliation rechecks cached machine acceptances from older gate versions, records an update event and suspends unsupported deliveries. It does not initiate a blanket review of already pending items or named-human decisions. Engineering tests exercise an old cached machine result, unchanged originals/history and idempotent repeat reconciliation.

## Failure found during actual browser checking

The weekly pilot displayed zero available Requirements despite its completed B counting follow-up. Its stored Canonical bytes still matched SHA256 `7ad6a77bb4ab77dc0ac5051730f936d3cfa406f46e163acfea52b2a8769b3cd3`, but the copied database referenced the earlier PDF pilot's directory. A symlink did not satisfy the existing owning-root guard. The `canonical_artifact_changed` hold was therefore correct. This was an isolation-fixture ownership error, not an observed natural extraction error; checkpoint 35's review/history observations did not establish delivery availability.

After the verified pilot service drained, its two databases and workbook were backed up. Identical Canonical bytes were copied into its own artifact directory, its local references were rebound, and only the established path-ownership hold was resolved. An explicit development-maintenance event records the before/after paths. All 91 original unit facts and all prior review history were retained; the earlier Canonical remained byte-identical. The original symlink is retained as recovery evidence.

The pilot then displayed one available complete parent, with its two exact fragments, footnote 7 and provisional parent-counting policy. A's page-9 finding remains open. B's initial `INCORRECT` verdict and completed follow-up remain historical records. Automatic Excel synchronization converged to event 57; browser, database and exported criterion 2.1.3 agreed. This restores the bounded delivery check without accepting the full source or independently validating the B split.

A first restart used an incorrect component path ending in `system1/Code/Code`; the output worker reported failure. That isolated service was drained and restarted with the correct System1 root. It recovered automatically. The normal service was not restarted or redirected.

## Evidence and preservation

Local evidence is under [the checkpoint directory](../../../workbench/runtime/confidence-dimensions-20260910/): `pilot-ownership-repair.json`, `pilot-recovery/`, `dimension-readback.json`, `normal-preservation.json`, `excel-snapshot.json`, `office-validation.txt` and `evidence-readiness.json`. The repair helper is deliberately one-time and must not be rerun in place. Restoring its pre-repair backup would restore the known blocked fixture, not a valid production state.

Normal port 62742 retains 38 documents, 15,120 pending content units, event 71 and zero published Requirements. All five owning database table snapshots and all 73 managed originals matched the stopped-write checkpoint-35 baseline. No normal review, source inclusion, original or source history was changed. Three normal weekly-read observations after the gate upgrade were 0.4023, 0.3595 and 0.3144 seconds; these are bounded local observations, not a performance percentile or representative workload acceptance. The current bridge loads the gate changes from its owning System2 environment; the shared interface was reloaded and observed normally.

The frozen output `/private/tmp/Requirement-Confidence-Checkpoint.xlsx`, SHA256 `9af00b182f676ada0f1817a3c97776dd956a38d11ed4ed62d75f5e1d0bc067b0`, passed OfficeCLI schema validation and data readback. Criterion 2.1.3 is available with one counted parent; weekly A remains `finding_open` and B `complete`, both retaining `INCORRECT`. **Native Excel visual acceptance of the latest long-note layout remains pending because the Mac is locked.** This supersedes neither the earlier observed native copy nor its recorded limitations.

Validation logs: `system2/runtime/confidence-dimensions-final-regression.txt`, `system2/runtime/confidence-gate-upgrade-targeted.txt`, and `workbench/runtime/confidence-dimensions-{frontend,workbench}.txt`. The final System2 regression passed 726 tests, with one skip and one dependency warning, in 25.96 seconds. Workbench passed 28 Python tests and 17 frontend tests. Nine changed documentation files contained 225 valid local links. These are engineering controls, not independent real-source accuracy labels.

## Independent evaluation readiness

Only the historical sample registry metadata was read for this audit. Its 13 samples comprise seven `active_diagnostic` and six `active_regression` records; none is untouched held-out material. A filename containing “holdout” does not reverse development exposure. No Gold annotation, manifest, baseline or reference answer was changed. Registry SHA256: `4f66a2322146f95dae6ace03cd75fb42b26441f02e449aae1bde2deede57b987`.

No production `scoring-rules.local.json` is present. The existing calibration helper still relies on caller-supplied independent-label provenance; checking its digest and dimensions alone does not establish the reference owner's independence, held-out performance or applicable accuracy. Production calibration qualification and independent reference collection remain unfinished. The new gate must not be reported as empirical calibration acceptance or an improvement in automatic processing share.

The currently enrolled PDF source is CS004, 134 pages. A read-only bitmap inventory found raster objects on its cover only; that cover was visually checked and contains designed title/photographic material. This did not identify a representative real scanned-body sample. No new source was discovered, retrieved or admitted, and no complete PDF extraction was started for this inventory.

## Next bounded work

Keep the independent reference owner, fresh calibration/held-out material and real scanned-body input explicit. Continue source-fidelity and recovery work that does not depend on those answers. The next useful engineering experiment is a source-version-bound original reference/inspection workflow with measured reviewer effort; separate its development examples from later independent acceptance. Complete native Excel inspection when the Mac is unlocked. Peer B granularity/counting and user-selected release thresholds retain their existing boundaries.
