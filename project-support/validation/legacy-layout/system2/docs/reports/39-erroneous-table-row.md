# Manual repair of an erroneous extracted table row

Date: 2026-09-10. Decision: **CONTINUE**. This closes a missing manual operation identified by the functional-stage audit; it does not resume automatic table-quality tuning.

## Behavior

The existing table-row editor now offers **Remove an extracted row absent from the original**. A named reviewer must explicitly confirm absence and supply original evidence. The operation preserves immutable Canonical and original unit fields, retains the excluded effective cells and their source positions with the decision, retires affected row items, shifts subsequent row positions and reopens affected A/B checks. Excluded rows remain visible in a retained-history panel. The existing guarded restore action reverses the overlay while keeping both decisions.

The operation refuses an entire one-row table, cells shared with another row, changed row versions, unfinished row drafts and incoming dependencies on a retired row. These require explicit source-boundary or relationship repair first. This is not an automatic deletion rule or a way to bypass unresolved content. Cross-page assemblies use the corrected fragment geometry; their header identities are preserved, and dependent later-row judgments reopen.

## Real-source browser evidence

CS004 original page 19 contains one INDICATOR / REQUIREMENT header and two numbered rows, 2.1.1 and 2.1.2. The extraction contained an additional leading row of `|` glyphs. The retained original image was inspected again. No new PDF parsing or source retrieval was performed.

In the isolated weekly pilot, table `pdf:ad9760e45858a11b2514f47e` was corrected from four rows/eight cells to three rows/six cells at revision 46. Its erroneous row item was retired; the header and numbered row identities remained. The first submission was rejected after a draft save added the newer confidence-gate version to old row records. Its note was retained, no repair was applied, and refreshing/recomparing allowed a guarded submission. This observed failure is retained in the evidence.

The reviewer then restored the prior overlay at revision 48: four rows/eight cells and the old row identity returned. The same source-backed removal was reapplied at revision 50. All 91 original unit records and all Canonical hashes remain unchanged. This pilot retains its earlier source-intake compatibility configuration; normal System1 authority remains its separately verified governance database.

The actual browser operation repaired one fragment. Cross-page recomputation, retained header identities and suspension of a later published B judgment are additionally covered by the focused integration experiment. Earlier real fragment-combination evidence remains in report 31 and is not repeated here.

## Output and engineering checks

The generated Excel reached event 63. The complete-table cell at `CS004!B42` begins with the real header and contains exactly its two body rows; the former glyph-only line is absent. Status remains Pending / Not delivered, preserving other unresolved issues. Original text such as the known `Benthic Qua lity` spacing defect was not silently changed by this row operation. Workbook SHA256: `8a5ad0786ed0e9ca06a893e6fc0799b4690e452904e9a2c136a9bcec928af3dd`. OfficeCLI validation passed; native visual acceptance of this copy is unperformed.

Seven new integration checks cover exact source preservation, current row reassignment, duplicate request replay, output invalidation, restoration, missing confirmation/stale targets, unfinished/cited rows, shared cells and cross-page behavior. The 22 focused row/assembly checks passed. Full System2 regression: 738 passed, one existing missing-fixture skip and one existing dependency warning. Workbench: 28 Python checks passed; frontend: 17 checks passed.

Local evidence: `workbench/runtime/table-artifact-row-20260910/`, with idle-pilot database backups, rejected first readback, undo/reapplication readbacks, effective table details, complete history, Excel snapshot/readback and OfficeCLI result. This code is served by the shared local interface and fresh System2 bridge processes. No normal business decision, source file, provider or schedule activation changed.

## Next functional boundary

Ordinary text, scanned-body transcription, table cells, grids, merged cells, notes, row identities and whole-table cross-page correspondence now have exercised manual routes. Audit the remaining case of a single numbered row continuing across pages: preserve both physical grids and provide a complete linked parent without double counting. Existing automation does not implement cross-page row reconstruction. If the current context route is insufficient, implement a minimal explicit continuation operation; do not disguise a missing manual route as an accuracy limitation. Complete the remaining B correction/advisory checks and consolidated functional acceptance matrix after that boundary is resolved.
