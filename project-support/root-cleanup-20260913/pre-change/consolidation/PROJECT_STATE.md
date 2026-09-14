# Requirement Workstream: current state

Updated: 2026-09-13. **ACTIVE: accurate, safe human review and local workbench delivery.** The user stopped further automatic extraction/recognition accuracy optimization; the [current goal](docs/design/human-led-workbench-goal.md#active-goal-extension-product-readiness-2026-09-12) supersedes the older quantitative targets. Historical quality FAIL/UNMEASURED results remain unchanged. Future training on human annotations and the final semantic schema are outside current implementation.

## Current delivery and loading

- The material workspace supports explicit extraction, manual correction, personal saving, guarded comparison/adoption, separate confirmation and offline exchange. Actual isolated browser evidence covers representative edits, conflict returns, empty/partial recovery and saved work after restart. Complete ten-scenario acceptance is still open: [coverage](project-support/product-readiness-20260912/workflow/ui-checks.md), [returned conflicts](project-support/product-readiness-20260912/workflow/return-conflict/RESULTS.md).
- The local PDF reader displays original-position text, continuous pages and search. Page/zoom/rotation survive refresh; source-load Retry has actual browser evidence. Reader checkpoint Workbench regression: **164 Python / 184 frontend PASS**. [Reader and recovery](project-support/product-readiness-20260912/ui/pdfjs-reader/recovery/RESULTS.md). PDF.js was actually loaded only in isolated 60905; 55542 and 58814 retain earlier parent versions. Normal 62742 was not restarted for these changes.
- Parser /7 was closed with **189 material-module tests PASS** and preserved original fragments/annotations. It is available to future source-loaded workers, but no normal business extraction was verified. [Final diagnostic checkpoint](project-support/product-readiness-20260912/quality/structure-diagnostic/source-line-fidelity/RESULTS.md). No further accuracy work is planned.
- Process and the third-pane semantic schema remain **Not connected**. Saved content, adopted master, human confirmation and future Requirement review remain separate states.

## Engineering management correction

[Root cleanup](project-support/root-cleanup-20260913/RESULTS.md) relocates 114 auxiliary files without discarding original bytes. Shared design context now lives in `project-support/design/`; capture/export evidence and the empty accidental root store are retained with a relocation map. Source, launchers, component stores and reference directories retain their ownership. The optional API no longer creates a cwd-relative database on import; 12 API checks and 13 recovery checks pass for this subsequent maintenance, separately from the reader regression. The unfinished confirmation-dialog change is parked with its test failure, and the prior verified UI source is restored.

## Remaining acceptance and next work

Finish actual-browser manual-review scope, confirmation, running-job reopen and missing-original/failure scenarios; complete keyboard/browser-zoom/preference checks; freeze the integrated candidate and run the predefined mixed-operation recovery workload. Previous `frozen-candidate-03` evidence predates current changes and is not current full acceptance. The unreadable legacy System2 `ui/review.html` remains a separately recorded [recovery gap](project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic/RESULTS.md).

Actual colleague usability and Windows round-trip acceptance remain pending. No business review, normal master switch, upload, external sending, repository push, new model, schedule or synchronization was performed. Continue from [execution and evidence](project-support/product-readiness-20260912/execution.md); component states own their detailed results. The preceding longer integration snapshot is preserved in [cleanup pre-change evidence](project-support/root-cleanup-20260913/pre-change/PROJECT_STATE.md).
