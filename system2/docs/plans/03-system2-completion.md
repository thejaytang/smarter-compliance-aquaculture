# System2 Completion Priorities and Execution Plan

Updated: 2026-09-08. User-approved order: complete Excel/HTML parsing, integrate System2 with the existing local workbench, then jointly improve PDF accuracy. Current facts belong only to `PROJECT_STATE.md`; preserve prior tests and repair evidence.

## Priorities and completion gates

| Order | Scope | Completion gate |
| --- | --- | --- |
| P0 | Excel/HTML parsing and independent source verification | Traceable text, structure, formulas/caches, hidden content and locations; negative controls detect omission, rewriting and wrong associations; field-level acceptance on real target samples |
| P1 | System2 integration with the existing workbench | Review queues, versioned evidence, decisions and receipts; named decisions, versions, replay, locks, backups and recovery pass; Workbench consumes and jointly validates state readback |
| P2, pending | PDF text and Requirement semantic accuracy | Resume jointly when requested; preserve unresolved Round 8 issues and historical evidence; no new accuracy experiments |
| P3 | Module consolidation, performance and release evidence | Depends on contracts and real acceptance above; passing tests alone do not establish release completion |

## Near-term work

1. Five HTML content mappings and original-field acceptance for the GLOBALG.A.P. reference XLSX are complete. Stable contract: [v2](../contracts/source-records-v2.md). Maintain actual figures/evidence only in System2 state and the [report](../reports/14-nonpdf-content-completion.md).
2. Production scope is System1 INCLUDE only. Consume effective selections/versions without repeating scoring. EXCLUDE/PENDING rejections are intake protection, not parsing failures or new tasks. Non-included Excel does not block completion.
3. Seven INCLUDE Lovdata sources are directory snapshots with empty bodies and full-text links. System1 should acquire complete snapshots while retaining identity, versions and history before reparsing. The diagnostic round located/preserved evidence only, without upstream changes or downloads.
4. Supported static HTML remains uncalibrated and review_required. Preserve boundaries for untranscribed images, interactive footnotes and legacy XLS. Complete text coverage does not establish semantic acceptance.
5. Next complete review items, evidence, versioned decision application and receipts for the existing workbench. Reuse its normal human interface; PDF accuracy remains pending.

6. Use three independent format pipelines: HTML, XLSX and PDF. Design human-conversion tasks for other formats in the existing workbench. Validate original/copy lineage, completeness confirmation and re-entry contracts before implementing tasks/receipts. Preserve originals without repeating eligibility review. See the [format flow](../architecture/06-format-pipelines-and-human-conversion.md).

## P1 system-side deliverables

- Review queue: stable task/item IDs, source/result versions, format, issue class, status and supported actions.
- Evidence reads: Canonical/report references and hashes; original-format PDF page/bbox, HTML DOM and Excel sheet/cell locators, without fabricated common coordinates.
- Decisions: accept server-bound operator, request ID, target, versions and explicit action; System2 validates and updates its own result.
- Receipts/readback: distinguish applied, rejected, stale, waiting and failed; return new version, remaining issues and traceable history. Submitted is not applied.
- Ownership: Workbench owns UI, sessions and interaction; System2 owns parsing facts and review processing. Reuse contracts, declare each supported operation and reject unimplemented operations. Production closure requires joint integration validation.

## Boundaries

Keep originals, Gold, historical outputs and System1 business state read-only. Process only currently eligible sources. No downloads, external transmission or Full Source Check; no PDF accuracy experiments, large PDFs or costly model jobs. Record CONTINUE / ADJUST / BACKTRACK / PIVOT / STOP at key checkpoints.
