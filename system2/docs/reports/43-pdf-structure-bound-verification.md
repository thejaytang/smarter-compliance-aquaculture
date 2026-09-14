# Checkpoint 43: structure-bound PDF verification

Decision: **CONTINUE**. The input-version blind spot is fixed and bounded structural contradictions are inspectable. Independent source-quality acceptance remains open.

## Observed failure and experiment

On the already exposed CS004 development page 19, reversing the extracted table's row numbers changed neither text nor source boxes. The previous verification input had the same SHA256 before and after the mutation. Column reversal had the same failure. A saved original-page check could therefore survive a structure-only change. This was an output-copy experiment; the governed original and normal database were never edited.

The frozen [48-unit development window](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/development-document-window.json) contains existing page-19/20 units and dependencies. It is development material, not calibration or held-out material. CS004 source SHA256 remains `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. The [initial blind-input evidence](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/baseline-blind-structure.json) and preserved input/comparator code precede the fix.

## Implementation and limits

Method `original-page-comparison/4` receives text records plus `pdf-output-structure/1` packets. The packets preserve row/column indices and spans, headers, row-to-cell ownership, hierarchy and order, typed related content and its target positions/structure, and logical table fragments. Other-page cell content participates in the assembly fingerprint. Review-only version increments are excluded; unchanged acceptance does not stale a check. A field literally named `version` in source content remains preserved.

Structure-only packets never count as text coverage or spend another copy of a cell's words. Linked note wording is checked at its own original position; its identity and inherited association remain bound to the owning item. A row-specific link is retained even though physical table text is emitted once by its owner. Unknown structure schemas produce explicit unverified scope.

The verifier now detects out-of-grid cells, overlapping logical slots, and row/column order contradicting claimed PDF positions. The positional rule assumes top-to-bottom rows and left-to-right columns, uses orthogonal overlap and separated extents, and does not call overlapping/ambiguous boxes a proven reversal. Touching adjacent cell edges are handled. Same-kind conflicts for one table/axis are grouped into one issue with all conflicting pairs and source regions.

These checks establish **output self-consistency**, not independently recognized original table structure. Findings retain `output_structure_and_claimed_positions` as their evidence origin and null confidence. Original snippets support inspection; they do not certify the grid or its boxes. A logical table with reversed physical fragments produces a conflict. Even correctly ordered fragments keep `output_cross_page_relation_unverified`; order alone does not establish a table continuation. Typed links keep localized `output_relation_source_unverified`, including the target on another page. Marker meaning, note scope, merged-cell correctness, hierarchy and full reading order still require source evidence and independent labels.

Changing structure, note target/meaning, or another assembly page now stales the affected saved check through the existing guarded transaction. This retains earlier evidence/history and reopens downstream content acceptance. A recheck reports the new conflict; it does not carry forward acceptance. The shared component displays compared row/column/span claims and supports source highlights/content entry. An unlocated structural issue stays readable and can open its owner; no nonexistent location button is shown.

## Evidence

| Check | Observed result | Interpretation |
| --- | --- | --- |
| Unmodified real page 19 | 8 candidate findings, 5 unverified items before and after | No new candidate burden in this development control; candidates have no independent true/false labels |
| Seeded row reversal | Old input unchanged, no specific detection; new input changes and adds one grouped conflict | Bounded structural failure detected |
| Seeded column reversal | Old input unchanged, no specific detection; new input changes and adds one grouped conflict | Bounded structural failure detected |
| Prior checkpoint-41 challenges | All 8 seeded differences retained; both clean controls without findings | Regression challenge evidence only |
| Prior checkpoint-42 challenges | Occurrence deficit retained; two clean occurrence controls remain clear; column-ownership ambiguity remains localized unverified scope | Previous behavior retained |
| Isolated workflow | A geometry repair stales an actual saved machine report; recheck sees the conflict; original and old evidence bytes/history retained | Transaction protection, not an actual independent-human acceptance |
| Typed links and assemblies | Same-wording target replacement, target edit/role change, row-specific note and other-page assembly edit change the input; review-only versions do not | Relevant change detection |
| System2 regression | 769 passed, 1 existing skip, 1 existing Starlette warning | Engineering compatibility |
| Workbench frontend | 20 passed | Component rendering/action protection |
| Browser component | Row/column controls displayed; source highlights, expanded structure and mapped-content action observed; main highlight has 8 recorded rectangles; no browser warnings/errors | Read-only diagnostic fixture, not a normal service decision or source-grid acceptance |
| Preservation | All 18 tables across the 2 normal stores, 73 managed files and 51 Gold files match checkpoint 41 | Normal source facts, business state and retained Gold unchanged |

The first targeted iteration excluded touching cell edges from reversal detection; the rule was corrected. Two synthetic fixture issues were also corrected: a missing initial review version and a request helper's fixed source hash. The versioned mutation test now uses the actual fixture PDF hash. The earlier failed targeted log is retained; the final full suite passes. This is one productive implementation round for this defect, not three unsuccessful repeats.

The [diagnostic runner](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/run-diagnostics.py), [geometry evaluation](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/geometry-evaluation.json), [prior challenge replay](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/prior-challenges-replay.json), [browser evidence](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/browser-component-evidence.json) and [preservation check](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/preservation.json) define the reproducible scope. Use System2's environment with `PYTHONPATH=src`; no API or business workflow is opened by the diagnostic runner. [The manifest](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/artifact-manifest.json) binds final code copies and experiment artifacts. The temporary loopback browser fixture was stopped after inspection.

## Cost and outstanding acceptance

Twenty repetitions of in-memory window projection plus comparison took a median 0.00892 seconds before and 0.01138 seconds after, maximum 0.00928/0.01194 seconds. This includes only the 48-unit development window and cached 57 original lines. It excludes original acquisition/OCR, normal full-document hydration, persistence, Excel and human work. The [environment record](../../outputs/runs/pdf-verifier-reliability-20260910/cp43/environment.json) identifies CPython 3.12.12 on macOS 26.6.2 arm64; device model/CPU count/memory were unavailable to this sandbox. These timings are diagnostic observations, not an accepted performance budget or workload estimate. No real human operation time was measured.

Next prepare a source-first, typed independent-reference protocol and its shared-workbench path, including unrepresented original regions, note markers/targets and cross-page relation questions. Preserve development exposure and keep human confirmation distinct from Agent-authored drafts. The reference owner, qualifying real scan, source-family-separated calibration/held-out material and user release thresholds remain unresolved. Current normal PDF table/relationship accuracy and verifier precision/recall remain unknown. Do not count structural consistency, newly saved links or these passing tests as independent correctness evidence.
