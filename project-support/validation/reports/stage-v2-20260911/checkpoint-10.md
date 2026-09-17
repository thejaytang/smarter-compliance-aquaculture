# Checkpoint 10: native font-boundary spacing and actual delivery views

Decision: **CONTINUE with the bounded repair retained; overall goal incomplete.** Candidate 06 improves seven measured table cells without changing the original reference or a previously correct region. This is exposed development diagnosis, not independent acceptance.

## Discriminating evidence and intervention

The remaining cell errors had distinct causes. On physical page 19, native word fragments `Qua` and `lity` touch on the same baseline at a font-run boundary. Page 128 parentheses show the same condition. Original rasters confirm the continuous words and punctuation. Conversely, `Require` and `ment` on page 117 are on different lines and cannot be joined by the same rule.

The [coordinate probe](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-spacing-discriminator-v1/result.json) retained all touching pairs on all eight pages. `native-character-spacing/1` subsequently requires a font change, matching baseline, touching bounds within 0.12 points and exact agreement with the native character sequence. Encoded whitespace, missing characters, conflicting characters, OCR, a line change or a larger gap prevents joining. The tolerance is an engineering rule verified in this diagnostic, not an accuracy estimate.

This modifies only the derived native analysis words and records the contributing original word IDs. Immutable native words/characters and source files remain unchanged. It uses no dictionary substitution, cross-line guessing, external model or production-threshold change.

## Same-source results

The new eight-page run uses the same source hash, page indices and configuration hash `7ae4b65ec163d9d650d9115912bbd2a38d9df559b0a2542379a3e576fb38359d` as parser rerun 03. Only seven of 275 delivered region texts change, all from incorrect to correct; the other 268 texts are identical. [Exact changes](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-spacing-discriminator-v1/region-changes.json).

| Measurement | Parser 03 | Parser 04 |
| --- | --- | --- |
| Character edits / reference characters | 31/12,860 | 17/12,860, CER 0.1322% |
| Word edits / reference words | 44/2,011 | 18/2,011, WER 0.8951% |
| Exact body-cell text | 116/125 | 123/125, 98.4%, stage target PASS |
| Body-cell position / critical expressions / order pairs | 125/125; 211/211; 20/20 | Unchanged |
| Strict complete regions | 58/275 | 64/275, 23.27%, FAIL |
| Explicit selected relationships / complete logical tables | 0/12; 0/3 | Unchanged, FAIL |
| Natural errors detected | 9/36 | 8/29, FAIL |
| Critical errors detected | 7/11 | 7/11, FAIL |
| Actionable findings correct | 9/34 | 8/33, FAIL |

The [current adjudication](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/diagnostics/candidate-spacing-method6/aggregate.json) retains 25 false/generic prompts, 40 unverified scope entries and all four critical cross-page misses. The smaller error denominator reflects seven actual repairs, not removed examples. Verifier recall remains inadequate. The remaining two cell errors concern cross-line `Requirement` and the retained reference's `non- salmonid` spacing; no reference normalization was used to erase them.

The old metrics are retained in [prior parser-03 metrics](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-spacing-discriminator-v1/prior-metrics-rerun03.json). All 38 metric rows remain present: 21 PASS, 11 FAIL, six UNMEASURED. These counts do not replace the applicability distinctions in the stage report. B classifier-4 evidence, paired challenges, manual fixtures and full-load performance retain their earlier explicit scopes. Safe A/B/end-to-end automatic release remains zero.

## Actual workbench, persistence and Excel

A separate owning workflow admits the actual new Canonical with all 109 units and the eight-page scope. The [runtime evidence](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-spacing-runtime-v1/result.json) binds the exact Canonical, physical page 19 and row 2.1.2. The actual shared UI shows the left original and right table; horizontal navigation reveals `Benthic Quality Index`. Confidence is unknown, three A prerequisites remain, B is blocked and no decision/draft was submitted.

The generated [Excel snapshot](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-spacing-runtime-v1/native-spacing.xlsx) agrees at saved/exported event 1, contains the corrected criteria and says Not delivered. SHA-256 `70c1dc05a5b0c4933e00605acb3243bec065e7c8b0312d4cdfb8f51a0a2276ba`. OpenXML readback is distinct from the still-unmeasured native Office visual check. A temporary stale-source-check indication recovered without restart.

The initial fixture selector encountered the same phrase on two physical pages and was narrowed to page 19. An initial assertion incorrectly looked in the `body` field; the real interface correctly puts the numerical criteria in `criteria`. Neither observation required a product change or business decision.

## Candidate, checks and preservation

Candidate `requirement-stage-v2-candidate-06`: 384 program/test/declaration files, archive SHA-256 `4513b2b17c0988b7cf93c219179ca568834fb4240f364d9ac5ba37188a07d01e`. The [manifest](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v6/manifest.json) binds code, configurations, references and outputs. All 91 frozen sample files and prior candidate archives remain unchanged; [recovery verification](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/candidate-freeze-v6/recovery-verification.json) verifies restored/current hashes without restoring any business database.

System2: **889 passed, one existing fixture skip**, 18.169 seconds. [JUnit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/full-system2-native-spacing.xml). Nine added checks cover exact character evidence, punctuation chains, original preservation and abstention controls. Frontend 25 and workbench Python 30 previous checks retain unchanged-code applicability. The [normal preservation audit](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/integrity-native-spacing-v1/normal-preservation.json) again matches all five business stores, managed originals and Gold; only browser-session rows differ.

## Presentation and remaining work

Canva remains the same 25-page native editable design. Pages 20 and 21 now show parser-04 and classifier-4 figures; the new PASS cell color was corrected and both whole pages were visually rechecked. A separate version label distinguishes retained earlier speaker-note evidence. Together with the four earlier checked draft pages, six pages await the latest explicit save approval. The [current receipt](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/presentation/canva-spacing-final-receipt.json) records the same transaction and replay dependencies. No saved completion is claimed.

Normal startup and native Office visual inspection retain their pending input boundaries. No protected start, model activation, scheduler activation, business acceptance, source expansion, reset or Git operation occurred. The original clock remains active. Next finish handoff/version consistency and the already prepared approval-dependent steps; use the remaining optimization window only for a genuinely different bounded failure hypothesis. The stopped raster and column/caption-only routes remain stopped.
