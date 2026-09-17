# Requirement Workstream stage v2: bounded execution plan

**Retained historical plan, 2026-09-11:** the [human-led material workbench goal](../design/human-led-workbench-goal.md) replaces v2 as the next product direction. Its [activation prompt](../design/human-led-workbench-goal-prompt.txt) is prepared for a separate user assignment. The ACTIVE label, clock, one-use permissions and checkpoints below describe the prior v2 execution and do not authorize a restart or constrain the new goal. Preserve recorded results and unresolved quality gates.

Status: **ACTIVE; explicitly started by the user on 2026-09-11.** The full v2 scope and proposed stage targets are adopted for this bounded diagnostic round; production release thresholds remain unchanged. Detailed targets and the acceptance matrix belong solely to the [English canonical v2 goal](../design/requirement-workstream-stage-goal-v2.md). Numerical values there are engineering proposals, not adopted production thresholds. This plan owns scheduling, checkpoint evidence and attempt tracking, not a second goal specification.

The [older PDF plan](../../system2/docs/plans/pdf-verification-reliability.md) remains PAUSED BY USER after checkpoint 46. This new plan neither resumes it nor resets its failed-attempt history. The completed earlier functional phase retains its historical scope.

## Active clock and state

The canonical [execution state](../reports/stage-v2-20260911/execution-state.json) records the clock, latest objective hash, current checkpoint and one-use reset authorization. Start: **2026-09-11 00:26:35 Europe/Oslo** (2026-09-10 22:26:35 UTC); eight-hour hard deadline: **08:26:35 Europe/Oslo**. Stop normal optimization at 05:26:35 local and reserve the final three hours for freeze, retest, reporting and the presentation. The subsequent reset-authorization addition does not restart the clock. A session continuation restores this state.

An explicit user instruction to start this full v2 adopts its proposed numerical stage targets; record that instruction and do not ask for approval of each number. Stage-target adoption is distinct from production-release policy authorization. In-scope reversible implementation and diagnostic experiments proceed on explicit start; changing production thresholds, enabling a provider/schedule, exposing confidential materials or other protected actions needs its existing authorization. A required decision pending at a checkpoint does not stop unrelated measurements or preparation.

## Initial 8-hour rolling horizon

| Checkpoint / elapsed budget | Hypothesis and concrete work | Evidence and success | Failure response / next decision |
| --- | --- | --- | --- |
| CP0, 00:00–00:30, 30 min | Existing code/evidence can support a focused release audit. Read states/contracts, inventory actual daily routes and loaded versions; reuse migration/recovery. Freeze 8 PDF pages, HTML/XLSX controls and B windows from originals before errors; set manifest and quality proposals. Outline 24 Canva pages as local text only. | Current read-only inventory, preservation scope, feature wiring matrix, frozen page/unit IDs and exposure, target/clock/attempt history. No parsing of an entire large PDF. | Missing runtime route: specify exact gap and protected load/restart need. Missing material: preserve shortfall, choose allowed existing development scope without pretending scan/held-out coverage. CONTINUE useful baseline; do not wait for all business reviews. |
| CP1, 00:30–02:00, 90 min | Source-first comparison reveals the dominant extraction/classification/detector errors. Survey all selected original regions; freeze diagnostic references and ambiguity; measure natural Q2–Q7 and initial Q8/Q9 on unchanged outputs; inspect all sampled unalarmed/auto-released items; separate seeded controls. | First real numeric baseline by 02:00, complete available denominators, per-case source evidence, reference qualification, initial human task mapping and 1–2 ranked root causes. Inadequate labels remain scoped UNMEASURED, never invented. | Reference effort too large: preserve the full selected scope and report completed subset/shortfalls; do not relabel it a complete baseline. Use smaller discriminating controls to diagnose. Baseline failure selects repair, not wholesale parser replacement. |
| CP2, 02:00–03:30, 90 min | At most 1–2 measured root causes can materially improve function/quality/effort. Rank silent critical errors/main-flow defects first. Reproduce minimal cases, count historical attempts, change the smallest owning module, repeat matched baseline/control cases and affected tests. | Exact before/after errors, impacts, regression/control results, retained source/history. Continue only when the diagnosis or measurable result improves. | Three consecutive ineffective attempts: STOP that route. Preserve known-good version/manual path; record failed Q gate. Integrity/false-completion/main-flow failure must be fixed or block freeze acceptance. Do not spend the reporting reserve on a fourth blind retry. |
| CP3, 03:30–05:00, 90 min | The candidate's main paths work through the real shared UI and persist correctly. Complete/reuse version-valid H scenarios, isolated review/repair/B recheck, offline and failures, weekly mechanisms, save/restart/Excel cycles. Audit source/handoff fields and collect bounded timing/burden observations. | H1–H5 scenario table, browser/DB/history/output evidence, runtime feature matrix, source preservation, raw timing and task-dedup ledger. Demonstration script and presentation content evidence ready. | Prioritize a simple repair for hard blockers within this slot. Defer numerical optimization with truthful FAIL/UNMEASURED. Protected load requires the exact preparation/authorization, not an invented loaded claim. At 05:00 stop normal optimization. |
| CP4, 05:00–06:00, 60 min | The frozen candidate and all reported numbers match. Freeze code/config/sample/reference hashes, repeat changed metrics and control checks, verify report calculations/links and no source/history drift. Produce quality/robustness report and machine-readable data; finalize demonstration/recovery instructions. | Candidate manifest, baseline/candidate/corrected comparison, complete H/Q/D statuses, all failed/unknown gates explicit and owner/next action. Safe candidate selection or explicit NO-GO. | A late critical change requires affected remeasurement; preserve prior report as historical. If impossible in remaining budget, freeze the prior safe candidate or report unresolved blocker. Do not pair old numbers with new code. |
| CP5, 06:00–08:00, 120 min | The technical explanation can be complete, editable and visually clear in one Canva design. Use the applicable skill and authorized non-confidential materials; create pages from frozen evidence, inspect every rendered page, correct overlaps/arrows/text, verify edits and link. Reserve the last 30 min inside this slot for final page review, outcome and handoff. | One multi-page Canva link; topic-to-page/evidence index; every-page visual checklist; demonstrated element editability; final report/version aligned; stop/resume state saved. | Tool/access or visual failure: preserve local content and exact unresolved D gate, do not invent a Canva deliverable or switch formats silently. No deadline extension, external transmission beyond authorization, or goal PASS from packaging alone. STOP at deadline. |

Total: **0.5 + 1.5 + 1.5 + 1.5 + 1 + 2 = 8 hours**. The final 3 hours are reserved for freeze/retest/report/presentation/handoff. A 6-hour window uses CP0 0.5h, CP1 1.25h, CP2 0.75h, CP3 1.5h, then 2h for CP4/5 combined. Choose that shorter plan only if baseline/reference reuse and presentation tool availability make it credible; reduce optimization, not confirmed core functionality or evidence/visual review. An unavailable input or tool consumes budget and remains an explicit failed/unmeasured gate, not a reason to silently run overtime.

## Initial technical presentation page allocation

This is a **PROPOSED 24-page outline**, adjustable for readability while retaining every required content group. Only one editable multi-page Canva design is the presentation master. No external design is created during this document revision.

| Pages | Content and purpose |
| --- | --- |
| 1–2 | Delivery question, declared scope, frozen version and honest outcome; confirmed three-layer overview: upper cross-system unified human review, middle System1 -> A -> B with System3 boundary, lower cross-system optional API/multi-agent enhancement. Label review/decision and API request/suggestion returns, disabled/unverified paths and current offline core. |
| 3–5 | System1 internal pipeline, source/selection/version/failure branches, source decisions/history/database and source Excel/handoff example. |
| 6–9 | A format routing; PDF native/scanned/mixed paths and exact active parser/OCR/table configuration; whole-source content/table/footnote/cross-page representation; original-side verification and unverified scope. |
| 10–12 | B checked-A/context input and positive/negative/advisory decisions; provisional parent/subitem identity/counting; confidence/acceptance and all exception paths. |
| 13–15 | Unified workbench tasks/reasons/evidence and side-by-side review; actual supplement/table/manual flow; drafts, history, retry and targeted downstream recheck. |
| 16–18 | Environment/module ownership; originals/Canonical/overlays/databases/versioned receipts/recovery; actual Excel fields and source/A/B handoff example with coherent background sync. |
| 19–21 | Runtime feature matrix; frozen natural quality and separate seeded challenges; automatic release versus parsing, silent-error checks, burden/performance and missing independent qualification. |
| 22–24 | Weekly monitoring/offline/provider-failure boundaries; runnable demonstration and operator handoff; failures, limits, evidence-backed next priorities and final outcome. |

Use multiple focused diagrams rather than one page containing every detail. Keep arrows small and proportionate, relationships correct and text readable. The overview's human and API layers must each span all systems; later pages explain per-stage program calls, evidence inputs/returns and verified versus proposed enhancement. The page checklist records: page ID, rendered version, overlap/clipping/readability, connector endpoints/direction/crossings, arrow proportions, alignment/spacing/style, actual text/diagram editability, three-layer/flow/status semantics where applicable, issue, repair, recheck and final status. Inspect all final pages; after edits recheck affected pages. Do not count successful generation/import as a visual check.

## Evidence and attempt record templates

Create evidence only on implementation start, under the existing report/run ownership structure. Use one new stage-v2 report directory for the manifest, machine-readable measurements, feature/scenario/visual checklists and handoff index; component experiments retain their owning paths and are linked, not duplicated as new authorities. Preserve historical evidence and frozen versions.

Each metric record includes metric ID, target revision/adoption, version/hash, sample IDs, natural/seeded/synthetic, raw/corrected, reference qualification, numerator/denominator/unit, uncertainty, measured value, proposed target, result and evidence. Independent metrics stay absent/unmeasured without actual qualification. Report raw observations, not only summary percentages.

| Cause ID and historical evidence | Attempt / hypothesis / minimal discriminator | Frozen before/after and unchanged controls | Result and decision | Consecutive ineffective count / new evidence needed |
| --- | --- | --- | --- | --- |
| Inherited checkpoint 47 | Method-change stale-report gap fixed; visible last-decision row height fixed before v2 baseline | 816 System2 tests passed before layout edit; 10 targeted workbook checks passed after it | Retain as pre-stage functional evidence; source quality not inferred | Historical PDF attempts are not reset to zero |

An ineffective attempt neither reduces the target error on matched cases nor produces useful evidence changing the diagnosis. A negative discriminating experiment may be useful evidence; record why, without gaming the counter. Three ineffective attempts stop that cause. A different-looking edit to the same failed hypothesis does not reset it. Manual alternatives preserve function only; the applicable quality/automation gate remains failed until measured improvement.

At each checkpoint save elapsed/remaining time, evidence paths, measured result, active blockers, next discriminating experiment and CONTINUE/ADJUST/BACKTRACK/PIVOT/STOP. At deadline, report the four separate outcome layers defined by the canonical goal. If any required gate is not passed, retain `goal incomplete` even when a restricted candidate/report/Canva presentation is delivered. End the implementation window; wait for explicit instructions for another one.

## Historical checkpoint 8 record

[Checkpoint 8](../reports/stage-v2-20260911/checkpoint-8.md) freezes candidate 04 after correcting two actual B applicability misses and its visible evidence display. B recall is 41/41; decisiveness remains 51/60 and safe automation stays zero. The prior [CP7](../reports/stage-v2-20260911/checkpoint-7.md) inference routes remain stopped. Next verify current handoff/runtime evidence and complete pending protected/UI steps when input arrives. The original clock and failed-attempt history remain in force.

## Checkpoint 9, persisted-score binding

[CP9](../reports/stage-v2-20260911/checkpoint-9.md) fixes an isolated old-score/new-method release counterexample. Candidate 05 preserves raw scores and human history while deriving unknown confidence for stale bindings. Durable reopened-store machine/human paths and 880 System2 tests pass. Quality counts are unchanged. CONTINUE handoff consistency and only a new bounded error hypothesis; the stopped raster/cross-page routes, pending approvals and original deadline remain unchanged.

## Checkpoint 10, native character spacing

[CP10](../reports/stage-v2-20260911/checkpoint-10.md) retains a new, discriminated font-run spacing repair. Parser 04 changes only seven faulty cell texts; current 123/125 cell-text target passes while strict coverage, relations, natural detection and automation still fail. Candidate 06 has 889 passing tests plus one existing skip, unchanged originals/reference and a coherent actual workbench/Excel fixture. Six Canva draft pages are visually checked and awaiting the latest save input. CONTINUE handoff consistency and pending steps; original clock, reporting reserve and stopped-path history remain unchanged.

## Historical checkpoint 11, frozen context proposals

[CP11](../reports/stage-v2-20260911/checkpoint-11.md) freezes candidate 07: classifier 5 improves complete-original decisiveness to 53/60 with positives unchanged. Actual runtime keeps damaged A bibliography uncertain; 907 System2 checks pass with one skip. CONTINUE version/report consistency and pending approved UI actions. No additional broad optimization is planned; retain the original stop at 03:26:35 UTC and the three-hour reporting reserve.

## Historical checkpoint 12, final candidate review

[CP12](../reports/stage-v2-20260911/checkpoint-12.md) freezes candidate 08 after a misleading follow-up description was corrected in the actual UI. All unit/history/guard data remain identical and the full 907-pass suite is retained. No further normal optimization is planned. Continue final evidence consistency and pending input-dependent normal startup, Office inspection and Canva save under the original clock.

## Historical checkpoint 13, current-version final retest

[CP13](../reports/stage-v2-20260911/checkpoint-13.md) verifies candidate 08 on a fresh full-workload copy with 20/20 reads, ten saves, three export/recovery cycles and complete source/history preservation. It also restores the expired six-page Canva draft and corrects the remaining old page-9 count. No product code changed. The final-three-hour reserve is active. Continue delivery consistency and input-dependent steps; preserve quality FAIL and source/normal boundaries.

## Current checkpoint 14, completion audit

[CP14](../reports/stage-v2-20260911/checkpoint-14.md) checks all twelve objective sections, sixteen scenarios, 38 metric rows and five named artifacts. It corrects a stale cell-text failure statement and confirms the actual remaining gates without adding future/optional prerequisites. Product source remains candidate 08. Final reserve and pending input-dependent actions remain unchanged.
