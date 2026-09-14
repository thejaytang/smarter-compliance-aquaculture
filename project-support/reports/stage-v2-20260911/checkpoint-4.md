# Stage v2 checkpoint 4: candidate freeze and bounded cross-page discriminator

2026-09-11. Decision: **CONTINUE protected-load and presentation handoff when authorized; ADJUST cross-page inference before production integration.** The original eight-hour clock remains active. Overall goal incomplete.

## Frozen candidate

The [candidate manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v1/manifest.json) binds `requirement-stage-v2-candidate-01`: 371 program, test and dependency files, a source archive, local configuration hashes, frozen references and exact measured output hashes. Archive SHA-256: `ea6b3cfa90066eaae7fee212aeb0c942cf3f14158a5e0fd067c31a26f9b73de9`. All 91 baseline sample files match their frozen hashes. Business originals, references and normal decisions were not changed.

The [handoff](handoff.md), [functional matrix](functional-matrix.md) and [quantitative report](quantitative-report.md) distinguish current code, isolated evidence, historical normal observations, failed quality gates and independent evidence gaps. The normal-entry scenario remains FAIL; the other fifteen retain scoped PASS evidence. A link audit resolved all 124 local links in the root README and stage reports.

A dedicated isolated candidate launcher preserves previous initial-summary evidence and writes a fresh session receipt on actual restart. Its existing-service path was executed and correctly reused the live full-load fixture. It has not restarted the normal service.

## Editable presentation

One native [25-page Canva design](https://www.canva.com/d/Y9RKJmiWmqUG-o8) contains 480 editable text elements. All saved version-1 page renders were inspected individually. Actual geometry and flow checks found imported dashed-stem loss on page 2; the corrected draft uses supported ordinary arrows and dotted stems. Pages 3 and 9 have corrected flow connections. All three corrected pages were rechecked, including footers; no outstanding visual issue was observed in those drafts.

The [page review](canva-visual-review.md) records native render limitations and exact evidence paths. Final saving remains pending the explicit approval required by the Canva commit tool. The saved version-1 architecture defect is not reported as fixed until that commit succeeds.

## Next useful experiment: source-side cross-page geometry

Hypothesis: independently acquired original painted table boundaries can locate cross-page relation questions without relying on extracted nodes.

The [bounded discriminator](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/crosspage-discriminator-v1/result.json) read only the same eight selected original pages. Pypdf painted rectangles plus retained original Poppler observations locate all **4/4** frozen continuation edges, with no extra edge among the selected adjacent pages. This is a geometry candidate result, not production verifier recall.

A separate synthetic information-content counterexample used two adjacent, separately captioned tables with the same column geometry. The geometry-only rule incorrectly proposed continuation. This demonstrates that column alignment alone cannot decide semantic continuity. There is no representative natural negative same-grid boundary in the eight-page cohort.

Decision: retain the source-region candidates for the next implementation, but do not promote the geometry rule or alter the frozen quality metrics. Add original caption/header scope and real negative boundary examples before a version-bound document-window comparison. Native rectangles also leave scanned, rotated, borderless and arbitrary-path tables unverified.

The first probe attempted an unavailable `fitz` module, then used the existing project `pypdf` dependency without installation. This environment adjustment did not change the diagnostic or reference population. No new production verifier method, source link or acceptance state was created.

## Remaining gates and smallest required inputs

- Protected normal start/load approval, already requested, enables actual current-parent entry verification. Prepared backups and operation steps are in [runtime-load-review.md](runtime-load-review.md).
- Mac unlock enables native Excel final visual checks.
- Explicit approval of the shown Canva pages permits saving the existing correction transaction.
- Source quality, natural verifier quality, automatic release, independent label ownership, real scan/mixed material, peer final subdivision policy and actual reviewer time remain failed or unmeasured as recorded in the quantitative report. A manual demonstration or source-geometry prototype does not satisfy those gates.

No reset was consumed; the latest usage check showed 38% of the weekly Codex window used. Existing external-provider, scheduling and confidentiality boundaries remain unchanged.

