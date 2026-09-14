# Cross-page table repair checkpoint

Date: 2026-09-10. Implementation paused after this checkpoint at the user's request, pending a progress discussion. This is a bounded table-correspondence implementation, not complete PDF repairability acceptance.

## Source-backed experiment

CS004, ASC Salmon and Cod Standard v1.5, original PDF SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`: visual comparison of pages 19 and 20 established one continuing Criterion 2.1 table. Page 19 supplies the INDICATOR and REQUIREMENT headers and items 2.1.1–2.1.2; page 20 supplies 2.1.3–2.1.4. No new model or parser dependency was introduced.

The isolated browser applied the correspondence at revision 109, undid it at 110, and recreated it at 112. Readback after undo confirmed that both original projections and earlier page-20 cell/row corrections remained. The active assembly is `table-assembly:3c83e7fad548bbedaa0f97e7`. The source fragments remain `pdf:d9f2d131d10121178a814f90` and `pdf:f15bf96c905af0f7a15d41e2`; their row identities were not replaced.

A real source typo in extraction, `Benthic Qua lity Index`, was corrected to the printed `Benthic Quality Index` at revision 114 through the original cell editor. Every other character was preserved. The effective assembled body, fragment, row output and derived Excel contain the corrected wording. Original Canonical/table fields remain unchanged. Final isolated event cursor is 137; no Requirement was accepted or delivered, and the source remains incomplete.

## Effective behavior and safeguards

`table_assembly` creates a versioned context view over ordered physical fragments. It retains all cells, source fragment IDs, source cell IDs, page coordinates and original row positions, while projecting combined row offsets. Selected header cell identities provide source-backed column labels to later rows and delivery metadata. Matching column counts and nonoverlapping page order are required. The current operation assumes matching column order; column remapping, joining a single row across pages and repeated-header suppression are not implemented in this checkpoint.

The assembly depends on its physical fragments; row items depend on their original table and the assembly. Fragment owners do not depend on the assembly, avoiding a dependency cycle. Local notes continue to belong to the original fragment and its rows. Joining tables does not broaden their note scope. Fragment repairs reopen affected acceptance and suspend eligible prior deliveries in the same workflow transaction. The assembly itself cannot be delivered as a new Requirement. Later row creation retains the assembly gate and remains reversible.

Restore preserves originals and creates history. It refuses to overwrite later conflicting cell or relationship changes. Missing fragments, changed columns and invalidated header bindings remain blocked; generic issue resolution cannot bypass these failures. Reopened human concerns have an explicit resolution path. Duplicate request IDs return the same receipt; stale fragment versions and other reviewers' drafts reject the combination.

Browser verification caught an omitted request field in the workbench allowlist; the first submission failed without applying a decision. The field was added, the service restarted, and the same retained request succeeded. Browser verification also showed that a one-region preview covered only page 19. The combined view now loads separate bound previews for both fragments, each with an enlargement control, plus complete-file and individual-fragment entries. A screenshot and DOM readback verified both pages and the corrected combined text.

## Checks and retained artifacts

- System2 final regression: 681 passed, one missing-fixture skip and one existing dependency warning.
- Workbench: 21 checks passed. Frontend: 17 checks passed; edited JavaScript syntax checked.
- Eight assembly integration checks cover source provenance, same cell IDs across fragments, retained row identity, delivery metadata and invalidation, note scope, replay, restoration/conflicts, stale/draft rejection, header drift, later row creation and reopening.
- Excel data readback and OfficeCLI verified the combined body at `CS004!B611`, including the correction. Native Excel visual acceptance remains outstanding; no spreadsheet-layout acceptance is claimed.

Local-only evidence is retained under `system2/tmp/pdf-cross-page-pilot/`: original page renders, `before-assembly.sqlite`, `before-fragments.json`, `effective-cross-page.json`, `repair-history.json`, `verification.json`, `officecli-cell.json` and `cross-page-repair.xlsx`. The workbook SHA256 is `dc465bf4b5bfe9717e41a792eca017e493b9e067627d0a3d4a19c76835deccc9`. The snapshot is a test artifact, not the formal source's accepted output.

The normal workbench at port 62742 was backed up and restarted with the new interface. Production still has 15,120 units, 31 waiting sources, seven failed sources, zero System2 review decisions and zero deliveries. Isolated pilot decisions were not migrated to production.

## Unresolved findings and stopping point

The original page-19 table has three physical rows including its header; the current extraction has an extra first row containing `|` glyphs. The combined view therefore retains six rows, not the five correct original rows. The defect was not silently discarded, and the table remains pending. Removal/classification of spurious source cells, repeated-header handling, actual cross-page row reconstruction and ambiguous fragment correspondence still need work.

Safe local reparse with conflict-preserving application remains unimplemented. Norwegian, scanned/mixed and wider complex-PDF acceptance, measured human review effort, native Excel visual acceptance and System3 consumer acceptance remain open. Existing tests and bounded examples do not establish source-wide text/structure accuracy. Further implementation is paused until the user and agent align on progress and the next scope.
