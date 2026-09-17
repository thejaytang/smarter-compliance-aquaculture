# Requirement Workstream architecture and evaluation map

Created 2026-09-11 at the user's request, replacing a slide-by-slide explanation with one spatial map. This is an explanatory design, not a change to the program or its acceptance state.

The delivered [Canva whiteboard](https://www.canva.com/d/2ve42QSUmzruj5C) is `DAHU36wMHvs`, titled **Requirement Workstream | Complete Architecture & Evaluation Map**. The existing design `DAHU2Fbzuew` was inspected without edits. The intermediate fixed-page import `DAHU36pIAf0` was converted to this separate whiteboard because Canva clamped the imported page dimensions. The whiteboard is the delivered design; the intermediate import is not the presentation entry point.

## Reading and presentation

Start in the central workflow: System1 source governance, System2A reconstruction and original-side checking, then System2B Requirement identification. Follow the issue/decision arrows through the shared human workbench. Preservation, one-way Excel, release gates, weekly QA, optional assistance and future System3 are shown alongside that flow.

Zoom into the ten numbered peripheral frames. Each links to its corresponding part and contains its purpose/process, boundary and a distinctive double-framed, notched gold evaluation container. The evaluation containers state scope, observed values, stage criteria, status, measurement method and interpretation. The main map omits implementation-level code, schemas, databases and dependency details.

| Frame | Explanation | Quantitative evidence |
| --- | --- | --- |
| 01 | Source governance and traceability | Q01; 73 preserved originals; seven explicit source follow-ups |
| 02 | Format routing, content, order and coverage | Q02–Q06, Q09, Q11, Q36 |
| 03 | Whole tables, cells and relationships | Q07, Q08, Q10, Q12 |
| 04 | Original-side verifier | Q19–Q23, with natural and injected populations kept separate |
| 05 | Requirement classification | Q13–Q16, with the separate negative supplement identified |
| 06 | Parent/child subdivision | Q17, Q18 and context invalidation |
| 07 | Confidence, release and future interface | Q24–Q26, Q35 |
| 08 | Durable decisions and one-way Excel | Q32–Q34 current candidate-08 supplement; Q38 |
| 09 | Human review, workload and response time | Q27–Q31 current candidate-08 supplement; functional checkpoint 15 |
| 10 | Weekly QA and optional assistance | Q37; design sample counts and inactive boundaries |

## Evidence ownership

- [Current quantitative report](../../reports/stage-v2-20260911/quantitative-report.md) and [metric definitions](../../reports/stage-v2-20260911/metrics.json) own Q01–Q38. Q05 is labelled REPORT in the visualization because it has no adopted numeric cutoff; this does not silently reinterpret it as an accuracy gate.
- [Current candidate-08 performance supplement](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/performance-current08/metrics.json) supplies Q29–Q34 instead of the earlier frozen timings.
- [Normal-load checkpoint 15](../../reports/stage-v2-20260911/checkpoint-15.md) supersedes the old presentation's unavailable-normal-entry statement. Functional evidence is 16/16 scoped PASS; source-quality and automatic-release failures remain unchanged.
- [Aligned target](../../design/requirement-workstream-target.md) and [decision boundaries](../../design/decision-boundaries.md) ground responsibilities and provisional/future scope. Component state files remain authoritative for implementation status.

The eight PDF pages are exposed, Agent-checked development references. Independent held-out accuracy, real scan/mixed/photo quality, actual reviewer effort and API benefit remain unmeasured. Native Excel inspection remains deferred by user instruction. This design uses no confidential customer material.

## Artifacts and verification

- [Canva delivery receipt](canva-delivery.json) records the final design and conversion.
- [Static design source](architecture-map.html) contains the single 7600 × 5600 authored layout.
- [Zoomable local review](review.html) provides Full map, Core workflow and ten detail buttons.
- [Authoring helper](build_map.py) regenerates those two artifacts; it uses the existing System2 environment without dependency changes.
- [Quality record](quality-check.json), [Canva text readback](canva-text-readback.json) and [layout record](layout.json) retain scoped verification.

All 422 text elements survived the whiteboard conversion with identical content and dimensions and one uniform coordinate translation. All 38 metric IDs are represented. The central workflow and all ten detail frames were inspected in the local browser; no text overflow remains. The actual Canva whiteboard image shows the entire composition, frames and connectors. Its returned render is 600 pixels wide, so this does not establish native-resolution visual acceptance or native Canva object grouping. The normal browser was signed out of Canva; no login or account change was performed. Read-only Canva transactions were cancelled after checks; the imported/converted design is saved.
