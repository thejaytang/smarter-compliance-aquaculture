# Weekly original and classification sampling

Status: engineering implementation integrated; normal A/B activation is disabled. This monitoring contract does not establish independent acceptance quality.

## Scope and activation

Monday targets are System1 5 governed records, System2 A 20 original inspection units and System2 B 5 completed classification judgments. System3 is off. The existing System1 schedule and history are preserved. A/B use `config/weekly-sampling.json`; a runtime-local `weekly-sampling.json` can override it for an authorized isolated experiment. Targets and schema are validated. Normal activation requires explicit authorization after verification; loading the interface does not activate it.

The running service checks the current business week in Europe/Oslo. It catches up only the current week after downtime. It does not create a new external scheduler or backfill imaginary inspections. A batch pair is persisted atomically, is unique by week and stage, and retains its seed, population, selected identities, source versions and frozen results. Reads and previews do not create batches. Earlier machine-only System2 batches remain available as legacy history.

## Original inspection units and B strata

The original catalog never reads extraction units. PDF pages are enumerated from the retained original file, including pages with zero extracted items and pages not yet processed. The proposed engineering inspection unit is one full PDF page, 20 nonblank original HTML text positions, or 40 nonempty XLSX cells. HTML images and empty/visual worksheets have separate scopes. These unit sizes are implementation choices awaiting representative human-effort validation, not accuracy thresholds.

HTML positions retain DOM paths and text/tail distinction. XLSX positions retain the original worksheet-part/cell addresses. Script-generated/external HTML and spreadsheet drawing layouts carry explicit limitations. The catalog is neither an independent verifier nor a reference-label dataset. A finding on an unprocessed page is unfinished coverage, not a measured natural parser failure.

B samples completed A/B judgments with source context, including positive `requirement` and negative `context`/`non_requirement` decisions. It selects three positives and two negatives where available, then fills remaining places from the remaining pool. A missing class or a short sample remains explicit; pending machine guesses are not used to fill the target. Complete-table containers, evidence-only and superseded records are excluded where they would duplicate review items.

## Decisions, findings and repair

The workbench shows the original on the left and the frozen result on the right. For finding follow-up it displays the current result, including B subdivisions and counting policy. A named reviewer, original-evidence note and confirmation of the reviewed range are required. The server checks item/result guards, source currency, request identity and original-file hash. Failed requests retain browser drafts. Replays reuse the receipt without another decision.

`CORRECT` completes an inspection. `UNVERIFIED` remains pending. `INCORRECT` opens a finding and preserves its original verdict after repair. A creates or reuses an original-position coverage item, even when no extraction exists; associated A/B results are invalidated. Missing content is entered through the normal source-position-bound supplement operation. B adds a classification blocker without revoking A acceptance. The reviewer explicitly resolves that finding while recording the corrected B decision.

A saved repair does not close the monitoring finding. A separate follow-up checks the current repair and accepted content before closure. B also requires an accepted current judgment. Open blockers, drafts and changed/ineligible sources prevent closure. Source changes with no current comparable original remain unverified and require source follow-up; no automatic retirement is performed.

Completed items enter the weekly Review history filter. Remaining samples and findings stay in Pending. Batches remain incomplete when below target, missing a class, affected by catalog failure, or carrying unfinished items. The overview reports observed agreement only for complete batches. It never substitutes monitoring agreement for precision, recall, calibration or held-out acceptance. System1 follow-up findings likewise prevent its batch from appearing complete.

## Persistence and output

System2 owns normalized `sampling_batches` and `sampling_items` tables, request receipts and events in its workflow database. Original files and original Canonical units are unchanged. Earlier QA tables are retained. The normal disabled path creates neither new tables nor batches.

The existing background Excel worker exports a `Weekly checks` sheet from the same read transaction as the source-result snapshot. It includes batch targets/shortfalls, frozen scope/results, initial verdict, status, current reviewer and full inspection history. Long values continue across rows. Excel remains one-way output; browser decisions do not wait for its rewrite. Renderer 16 accounts for the new sheet and long evidence-note row heights.

See [checkpoint 35](../reports/35-weekly-original-sampling.md) for observed failures, evidence and unfinished acceptance.
