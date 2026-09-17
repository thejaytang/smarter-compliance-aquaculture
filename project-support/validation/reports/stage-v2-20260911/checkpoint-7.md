# Stage v2 checkpoint 7: stop unsupported relation and raster inference

2026-09-11. Decision: **STOP column/caption-only relationship inference and the current raster line-removal route; CONTINUE candidate evidence and handoff checks.** The overall goal remains incomplete. Candidate 03 and all published quality measurements are unchanged.

## Cross-page context discriminator

The original geometry probe locates four known continuation candidates, but column alignment is not proof of table continuity. The [context experiment](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/crosspage-discriminator-v2/result.json) adds source caption/scope anchors and five separate feature controls. Two controls have identical observed features and opposite semantic relationships. All four natural candidates remain ambiguous; zero new confirmed relationships are credited.

Original CS004 physical pages 21 and 121 were acquired and visually inspected as supplementary development context. Page 21 continues rationale without a body table; page 121 starts Appendix VII without a body table. They establish ending boundaries, not natural same-grid negative examples. Their [exposure manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/crosspage-discriminator-v2/supplementary-manifest.json) keeps them separate from the frozen eight-page quality cohort and twelve seeded challenges. No reference answer or denominator changed.

## Raster discriminator and failed route

The independent original observer currently emits 15 generic ink regions over the eight pages. These are already adjudicated as false prompts in the natural diagnostic. Three isolated prototypes copied the observer without editing production code:

| Prototype | Hypothesis | Observed candidate regions | Decision |
| --- | --- | --- | --- |
| [v1](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/raster-rule-discriminator-v1/result.json) | Remove long horizontal/vertical ink after observer word masks | 13 versus 15; page 128 fragments from 2 to 11 | ADJUST: colored fills are mistaken for text ink. |
| [v2](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/raster-rule-discriminator-v2/result.json) | Local contrast distinguishes fill from white/black text; odd line kernels remove anchor artifact | 98 versus 15 | FAIL: much more fragmented noise. |
| [v3](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/raster-rule-discriminator-v3/result.json) | Detect intact lines before recognized-word masks can interrupt them | 97 versus 15; page 128 still 21 | STOP: interruption is not the dominant cause; no production integration. |

These are region counts, not a newly adjudicated error-recall or precision result. Structural ink remains recorded in each prototype, but that does not prove the removed pixels contain no text. Separate controls retain `not` and the phrase `- 0.01 mg`; flat fill produces no text region and white-on-dark text is retained. They do not establish isolated minus-sign detection, representative scan performance or held-out accuracy. The v1 Unicode-minus OpenCV control was unsuitable for a minus-sign claim; v2/v3 use visible ASCII text. These controls never enter the frozen twelve-error denominator. Page 128 and the corrected phrase control were visually inspected.

Three bounded probes have now exhausted this line-removal/contrast route for the present round. Do not make a fourth threshold/kernel adjustment without materially new evidence. A future attempt needs an original-side component model that can distinguish text, line junctions and artwork while preserving unrecognized glyphs, with dedicated critical-symbol controls. Merely relabeling raster warnings does not reduce reviewer work or prove extraction correctness.

## Retained evidence and limits

[Integrity readback](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/checkpoint-7-integrity.json) verifies all 378 current candidate source hashes, candidate 03 archive hash and all 91 baseline hashes unchanged. No production edit, normal decision, model call, schedule activation or protected service operation occurred. Regression evidence remains the version-valid CP6 result, 848 System2 checks and 25 frontend checks; no repeat suite is needed for diagnostic-only scripts.

Natural detection remains **9/36**, critical detection **7/11**, useful-finding precision **9/34**, and A/B/end-to-end safe automatic passes remain zero. These failures continue to prevent overall acceptance. See the [stage applicability note](stage-applicability.md) for the distinction between required stage results and future/optional qualification; independent labels and live APIs are not substituted for the actual failed engineering targets.

The next checkpoint verifies report-to-version consistency, demo instructions and retained functional evidence. Protected normal startup, native Office inspection and Canva draft commit await the existing user requests; no approval is inferred from time elapsed. The original eight-hour clock is unchanged.
