# Human-led workbench: second improvement round

Activated by the user on 2026-09-11 following the approved conversational plan. This is a single-user local workbench with multiple tabs. Preserve the [material-centered goal](../design/human-led-workbench-goal.md), original files, manual work and history. The third-pane schema and semantic processor remain unavailable.

## Outcome and implementation sequence

1. Capture preservation/performance baselines and isolated fixtures.
2. Add durable, sanitized worker status and infrastructure backoff; keep `/health` compatible and expose `/api/runtime-status`.
3. Load material summaries (50/page), history summaries (20/page) and candidate/conflict details on demand. Stream original files without full Base64 transport; bind reader caches to source hash, reader version and range. Window large editable tables without losing edits.
4. Default to readable content with block editing, continuous-edit mode, whole-content search, chapter navigation, evidence-bound two-way locations and PDF rectangle selection with numerical/keyboard alternatives.
5. Compute review impact on the server. Preserve only provably unaffected checks and their provenance. PDF page / Excel sheet / whole HTML remain the review scopes. Unknown association/dependency impact and source changes invalidate full review. Every content change invalidates final confirmation; no automatic acceptance.
6. Provide configuration-derived stopped-service consistent backup and isolated restore tools. Include owning stores and required originals/Canonical/material resources. Verify hashes and references. Never overwrite a normal store or erase history automatically.
7. Exercise failure/recovery, run a 60-minute isolated mixed-operation test, verify actual browser behavior, then safely load and check the normal local instance.

## Acceptance contract

- Runtime status reports source, material extraction, storage and workbook synchronization, with last successful checks, active work, duration and safe errors; failures survive restart. Explicit parser failures require explicit retry.
- At least 30 repeated measurements on this machine: material/history summary p95 <=1s; repeated original range <=1s; first large original <=5s; 10,000-block save p95 <=5s. First versus repeated reads are separate. Parser throughput is measured separately.
- Synthetic scale: 100 materials with 20 historical versions each, a 300-page PDF, 10,000 content blocks, and a 20,000-row/30-column Excel with hidden/empty scopes. Retain public and mixed/scan controls.
- Actual browser: reading/editing, full-content search, chapter navigation, two-way evidence locations, crop, table-window edits, unsaved drafts, multiple tabs, stale candidates, source replacement, history and restart.
- Review-impact tests cover ordinary edits, cross-page tables, hierarchy/reordering, split/merge, shared dependencies, unknown links and historical compatibility. No old human confirmation is fabricated or overwritten.
- Backup restoration into a new isolated root preserves body, human decisions, history, candidate and conflict data plus evidence references; corrupted backups are rejected.
- Continuous 60-minute real-time mixed operations (at least one operation group per minute), with concurrency, worker interruption and service restart; no integrity failure or unexplained resource growth. Record actual duration, not simulated time. Do not claim multi-day stability.
- Original/Canonical and existing business preservation checks pass. Root/component states and guides describe actual delivered evidence and limitations.

## Current checkpoint

**COMPLETE for this round's approved scope, 2026-09-11.** The [acceptance report](../reports/human-led-round2-20260911/acceptance.md) records actual browser, scale, fault/recovery, phased 60-minute operation, complete backup and normal-load evidence. Final service: http://127.0.0.1:62742/ with matching parent code and six successful runtime components. The isolated engineering service has been stopped; its data and evidence remain retained.

Preservation comparison: all five original owning-store table sets and all 73 originals/75 Canonical artifacts are unchanged, except additional maintenance sessions. Rebuildable indexes are additive. The full final recovery package also includes the optional sixth Jobs store. No normal material workspace or business confirmation was created. Baseline source tree had existing untracked content and an existing deleted `Book1.xlsx`; those are not this round's changes.

Actual validation found and corrected additional issues with large browser drafts, duplicated-tab ownership, reader switching, restored-source confirmation, source-export retry backoff, Leader-store backup coverage and WAL-mode package validation. The final recovery fix has an explicit live-WAL/repeated-verification regression and a passing 55-test Workbench rerun. These adjustments retain the approved scope and protected boundaries.

No external publication/transmission, commit/push, model activation, new schedule, credit reset or important-history deletion is authorized by this plan.
