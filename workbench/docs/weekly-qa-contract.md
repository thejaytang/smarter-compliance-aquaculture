# Weekly QA integration contract

The workbench service owns due-time orchestration and display. Each system owns its eligible population, versioned sample, task decisions and audit record. Do not use a Codex automation, workstation username or personal reminder as the scheduler.

- Period: Monday date in Europe/Oslo, one durable batch per system and ISO week. A stopped service catches up the current week only. Retry after locks release; never run retrieval, extraction or machine review as part of sampling.
- Target: 5 distinct eligible items per system. Exclude unresolved items. Use the entire eligible population when fewer than 5 exist; record requested, eligible and sampled counts, including zero. Previous unresolved batches remain visible.
- System1 sampling unit: governed source record and registered original. System2 proposed unit: a parsed atomic item with page/bbox and source text. System3 proposed unit: an enrichment judgment with upstream provenance. The latter two adapters are not implemented; their teams must confirm eligibility and application contracts before connection.
- Batch evidence: system ID, Monday date, stable batch ID, sample item IDs, version/fingerprint, requested/actual population counts. Decisions need named actor, timestamp, CORRECT/INCORRECT, and error notes; an error opens a correction task without rewriting the original QA verdict.
- Accuracy: correct / actual sampled, only after all sampled items have a final named applied verdict. Pending, missing and unconnected weeks are null, not zero. Keep the sample denominator visible; do not present sample accuracy as whole-library accuracy.
- Chart: current week plus previous four weeks. Missing values break the line. Equal series overlap without artificial offsets; table and legend distinguish each system.

Current System1 persistence: `RANDOM_QA_CHECK` rows plus `RANDOM_QA_BATCH_SUMMARY` in the governed workbook, keyed by `batch_week`. Monthly historical rows remain unchanged and do not masquerade as weekly batches. The bridge exposes `random_qa`, guarded by existing process/workbook locks. The workbench worker invokes it when idle and retries at most once per minute. `qa.py` projects audit evidence; `qa-chart.js` renders it. System2/3 currently return Not connected.
