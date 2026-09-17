# Background export performance and recovery

Date: 2026-09-10. Decision: **CONTINUE** with the next independent migration experiment. This resolves the observed export bottleneck in a bounded workload. It does not complete the original multi-format checkpoint, source-quality acceptance or the overall goal. [Checkpoint 32](32-original-page-verifier.md) retains the previous failed 100-second recovery observation.

## Workload and diagnosis

The preserved original-verifier pilot contains all 38 documents and 15,131 units, including its earlier isolated repairs. The frozen input is event 144, policy 1. Device: Mac16,12, Apple M4, 16 GiB RAM; component-owned Python environments; no external model API. These are previously exposed development sources, not held-out reference material.

Profiling identified repeated per-cell Font/Alignment construction and style registration as the dominant export cost. About 582,867 `_cell` calls consumed 55.5 seconds under profiling. The running worker also waited a fixed minute between attempts and serialized System1 confidence export before System2 export. No audit rows, unresolved items, original text or confidence gates were removed to improve time.

The exporter now uses an equivalent reusable `RegisterBody` style and avoids redundant effective-content resolution. Render version 12 forces regeneration. The worker observes durable event/policy versions every second, coalesces a burst for 2 seconds with a maximum initial wait of 5 seconds, and retries failures after 5/10/20/30 seconds. A separate existing-service thread handles System1 confidence export. A periodic 60-second integrity/upstream check remains. These are local worker timings, not activation of a new weekly schedule.

Excel lock checks occur before expensive hydration and again before replacement. A lock or write failure preserves the previous workbook and marker; the database remains authoritative. A write during generation stays pending for the following snapshot. Downloads still verify the advertised immutable snapshot hash.

## Measurements

| Measurement | Before | After | Interpretation |
| --- | --- | --- | --- |
| Complete profiled export | 70.367 s | 20.278 s | Same complete frozen workload, both with profiler overhead |
| Profiled workbook construction | 62.308 s | 11.385 s | Largest measured improvement |
| Unprofiled read/build/save phases | Not measured | 2.597 / 3.564 / 2.480 s | 8.642 s combined; separate from HTTP and coalescing time |
| Actual draft HTTP acknowledgment | Not measured | 1.030 s normally; 1.064 s with export locked | Two isolated draft saves, not human review-time measurement or p95 |
| Background convergence after ordinary save | Not measured | 12.732 s | Observed pending, refreshing, then matching event 145 |
| Lock failure visible after saved event | Previous failure retained in checkpoint 32 | 3.043 s | Database event 146 retained while Excel remained at 145 |
| Selected-unit read while export failed | Not measured | 0.322 s | Saved draft and pending content remained readable |
| Automatic convergence after lock removal | Previously exceeded 100-second observation window | 14.163 s | No synchronous refresh was needed to reach event 146 |

The running pilot was reloaded before this experiment. Requests used the normal guarded loopback HTTP endpoints with server-bound reviewer identity; each draft explicitly says it is a Codex isolated engineering timing test and not source acceptance. Failure was a clearly labelled artificial `~$` lock, removed in `finally`. The state sequence was saved/pending → refreshing → failed → refreshing → current. The browser displayed `Decisions saved · Excel synchronized · saved event 146 · Excel event 146`; source coverage remained incomplete and accepted Requirements remained zero.

The target document's proposed 2-second acknowledgment and 60-second ordinary convergence budgets are met by these individual observations. They are not demonstrated p95 service guarantees or user-approved release thresholds. Actual human effort and broader representative-load performance remain unmeasured. The earlier original-page check's 8.11-second complete request is a different operation and was not remeasured here.

## Output and engineering checks

- Before/after sheet names and dimensions match. All 387,157 populated cells were compared: zero content differences and zero differences in checked font/fill/alignment/number-format/protection/border-style properties. The 41 permitted changes are generated timestamps and snapshot fingerprint metadata. This is structured parity, not a new native visual acceptance.
- The automatically recovered event-146 workbook has SHA256 `7cef39c373599df4edecb488bba5f9dff9f166b8087e32a6d0895d8dc0d71eca`. OfficeCLI reads the complete repaired footnote at `CS004!B618`, including `both`, with Aptos 11, top alignment and wrapping. Open XML validation reports no errors.
- Native Excel reinspection of the optimized snapshot is outstanding: CUA reported that the Mac was locked and automatic unlock failed. The user was asked to unlock it. Checkpoint 32's native inspection belongs to the earlier workbook and is not relabelled as acceptance of this artifact.
- System2 full regression: **689 passed, one pre-existing missing-fixture skip**; the existing Starlette warning remains. A new fault test opens Excel during generation, verifies unchanged prior bytes/marker and temporary-file cleanup, then verifies recovery to the newer saved event. Workbench Python: **24 passed**, including burst coalescing, continuous-edit maximum wait, changed-during-export handling and failure backoff. No frontend code changed in this checkpoint.

The normal service was then backed up and reloaded on retained port 62742. Every table digest in both System2 and Workbench databases matched before/after. The source registry and all 73 files under System1 Data matched byte-for-byte. Normal state remains 38 documents, 15,120 units, 71 events, zero System2 human-review rows and zero deliveries; the normal Excel marker matches event 71. No source discovery, repeated source review, new parsing batch, external provider, weekly scheduler or external deployment was initiated.

## Evidence and restoration

Local evidence is retained under `system2/tmp/workstream-performance/`: frozen SQLite input, `before.xlsx`, `after.xlsx`, `export-before.json`, `export-after-profiled.json`, both profiler outputs, `export-after.json`, `export-parity.json`, `background-sync.json` and `background-sync-snapshot.xlsx`. The timing script's final download originally used the regular workbook route only after current state had already been observed; it did not cause either measured recovery. Its reusable version now uses the cached download route.

Pilot pre-reload databases are in `workbench/runtime/original-verifier-pilot/workbench/runtime/checkpoint-before-export-reload/`. Normal backups, exact table/file hashes and reload verification are in `workbench/runtime/export-performance-release-backup/`. Restoration requires a stopped-write checkpoint and preservation of any later human changes; no original file needs restoration.

## Next experiment

Follow [the active plan](../../../docs/plans/requirement-workstream-implementation.md). Independent real scan/structure/B labels are still unavailable. While that input is pending, migrate a complete isolated System1 copy and prove all source rows, operation history, selection/pending states and original/version links survive round trip. Keep normal System1 authority unchanged until its database transaction, adapter, one-way Excel export and recovery checks pass. Provisional B splitting, calibrated independent acceptance, weekly A/B sampling and human effort remain open.
