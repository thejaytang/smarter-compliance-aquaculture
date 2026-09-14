# PDF repair pilot: effective corrections and invalidation

Date: 2026-09-10. Decision: `CONTINUE` to source discovery and structural repair. The user confirmed the design in [the audit](21-pdf-repairability-audit.md). This checkpoint implements the first bounded stage; it does not complete the PDF repairability goal.

## Implemented and loaded

The normal workbench now provides guarded footnote/context/reference attachment and detachment, source-positioned missing-text insertion, shared table-cell text correction, and restoration before supported earlier repairs. Each operation changes the effective structured result, records actor/version/history and reopens affected checks. Repair drafts have durable claims and stale-draft comparison. Conflicting old whole-row text overrides cannot be dismissed as resolved; the reviewer must explicitly choose the corrected table values.

Original PDF and Canonical remain immutable. `review/effective.py` is the common resolver for browser detail, Requirement classification, Excel and delivery. Table owners store a cell correction once; row views derive from those cells. Related footnote text and evidence travel with the effective Requirement. Delivery identifies whole-table versus selected-cell scope. A repair is not content acceptance. Restoration makes a new revision and rejects conflicting later overlay changes.

The production service was restarted on port 62742 and its new repair module returned HTTP 200. Read-only database checks after restart found 38 source versions, 14,986 units, zero System2 human history records and zero deliveries. Isolated pilot decisions were not migrated. No API provider was enabled, no new full PDF parse was started and System3 semantic processing remains unconnected.

## Real-source bounded experiment

Source: `data/inputs/ASC-STD-010-ASC-Salmon-and-Cod-Standard-V1.5-Oct-2025-1.pdf`, SHA-256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. The experiment reused the existing Canonical window for PDF pages 18–21. Original pages 20–21 were inspected. Production originals and Canonical were preserved.

The disposable runtime is `../workbench/runtime/pdf-repair-pilot/`. Its manifest records two seeded challenges: a copied table criterion changed from ≥2 to ≥9, and footnote 7 removed from the review projection. These are controlled repair challenges, not measured automatic parser error rates. The source remains 134 pages; this four-page working window remains incomplete.

Browser actions under the isolated reviewer account:

1. Corrected the criterion for 2.1.3 to `≥ 2 highly abundant 7 taxa that are not pollution indicator species` through the table-cell editor.
2. Inserted the literal footnote 7 text at page 20, bounds `56.52,529.56,552.24,551.52`. It appeared in source order before footnote 8 with structured page/bounds evidence.
3. Attached footnote 7 to 2.1.3, restored the pre-attachment state, then attached it again. Restoration retained history and pending review.
4. Accepted the selected content and classified 2.1.3 through the browser. One add event contained the corrected criterion, literal footnote, and page 20 references. Excel values matched that delivery.
5. Reopened and corrected the linked footnote. The previously published Requirement received a suspend event; the current published count became zero and both affected checks remained pending.

Four prerequisite coverage/table/note decisions were prepared through the guarded HTTP interface with an explicit `ISOLATED FIXTURE GATE ONLY` note. They test gate mechanics and do not establish visually verified accuracy for the entire four-page window. The selected-row source comparison and the downstream contract experiment are separate evidence.

Local evidence under `tmp/pdf-repair-pilot/`: `accepted-output.json`, `accepted-output.xlsx`, `invalidated-output.json`, `invalidated-output.xlsx`, and `gate-fixture-receipts.json`. The accepted artifact predates additive table-scope metadata; its recorded source text and relation evidence remain valid. Pilot preparation scripts and the isolated runtime must not be rerun or copied into production as acceptance data.

Native Excel opened `accepted-output.xlsx`; the Source Index showed the incomplete source and one available Requirement, and the CS004 sheet rendered readable full-text rows. Exact criterion/footnote equality was checked programmatically against delivery, not by visually navigating to that exact row. No measured human workload or independent reviewer acceptance was obtained.

## Engineering checks

- Full System2 suite: 608 passed, 1 skipped, 1 warning in 13.13 seconds. The skipped test requires absent `_PS3_副本.pdf`; the warning is an existing Starlette deprecation.
- After the final conflict/history additions: 57 focused integration tests passed, including seven repair tests. They cover effective footnote invalidation, stale targets/cycles, shared table values/restore, supplementation and replay, conflicting restore, source ordering/history, and explicit resolution of old row overrides.
- Workbench Python: 21 passed. Frontend: 17 passed after the final UI edits; the new module also passed syntax checking.
- Evidence logs: `tmp/pdf-repair-regression-final.txt`, `tmp/pdf-repair-targeted-final.txt`, `tmp/pdf-repair-workbench-tests.txt`, `tmp/pdf-repair-frontend-final.txt`.

These checks establish bounded implementation behavior, not automatic extraction accuracy or whole-document acceptance.

## Next checkpoint and remaining limits

The next experiment must make problems discoverable independently of machine issue queues: page-region coverage, adjacent pages, source-backed outline/context, and explicit unmapped regions. Prioritize the PDF projection's overly broad coverage dependencies and missing hierarchy before expanding models. Existing production PDF dependencies can still reopen a wider range than semantically necessary; this pilot does not establish minimal invalidation for all production PDFs.

Then validate actual hierarchy/order edits, source-boundary split/merge, table row/column/span and cross-page repair, and ambiguous footnote ownership on a small real range. Current table repair changes cell text; it is not a table geometry editor. Footnote links target units, not character-level superscript anchors. The insertion locator validates page count and ordered finite coordinates but does not yet validate bounds against physical page size. Nested related-content resolution and source-first insertion need further work.

Safe local reparse with differences/conflicts and preservation of human patches remains unimplemented. The legacy standalone review writer must not be used to modify active immutable Canonical. Restoration currently covers supported repair overlays, not universal undo of all historical edits.

The following remain unverified: source-wide error discovery, important-error recall, independent reviewer repair time/click burden, document-disjoint complex PDF performance, scanned/mixed content, and real Norwegian PDF acceptance. Set workload limits from a measured human pilot rather than inventing a target after the fact. Advance only when known critical defects in the selected range are repaired or explicitly unresolved, output is source-correct, and no stale result stays available.
