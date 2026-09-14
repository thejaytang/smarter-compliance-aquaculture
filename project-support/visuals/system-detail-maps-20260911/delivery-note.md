# Detailed system report | 2026-09-11

The user requested three additional canvases that explain the internal workflows of System1, System2A and System2B. During authoring, the user explicitly emphasized original-structure scanning/reconstruction and cross-page content assembly. The user then preferred the HTML presentation over Canva and redirected publication to Sites.

## Artifacts and scope

- `system1.html`: 38 process/branch nodes and 63 connections.
- `system2a.html`: 46 process/branch nodes and 74 connections.
- `system2b.html`: 46 process/branch nodes and 77 connections.
- Each detailed canvas has four named module frames, a shared human review/return loop and four distinctive gold double-frame evaluation containers.
- The complete architecture remains in `../requirement-workstream-map-20260911/` and is retained as the report overview.
- `build_details.py` owns these authored detail diagrams. `*-layout.json` includes the matching workflow and evaluation content for the Sites read view.

System2A now explicitly depicts original-structure scanning; hierarchy and reading-order reconstruction; cross-page paragraph/list continuation; physical-table reconstruction; cross-page table assembly; context/footnote/caption binding; original-side checking; versioned human repair and revalidation. Source correspondence was checked against the paragraph/table assemblers, current two-stage review and source-intake contracts, and stage-v2 diagnostic evidence.

Exact cross-page join precision and recall require independently labelled fragment pairs. Their results remain **UNMEASURED**. The displayed 98% precision/recall criterion is proposed, not a changed production setting. Existing text, grid, relationship and complete-table diagnostic populations remain separate.

## Verification

Browser layout checks on the local HTML detail canvases found no text overflow after the last content/layout correction. Focused views of source retrieval, content reconstruction and B proposal classification were inspected. Geometry checks found no connector crossing a process/branch node interior in all three detail diagrams. This validates the authored explanation only; it is not system quality acceptance.

Sites additionally checks static entrypoints, references, JavaScript syntax, content counts and exact release packaging. Sites browser testing was not requested and is not claimed.

## Destination change

System1 was imported before the user redirected publication: Canva design `DAHU38wC-gY`, title `System1 | Source Governance - Internal Workflow`, edit URL https://www.canva.com/d/4HwcpIOceJ2ufYu. Import success was reported by Canva; its native layout was not inspected before the pivot. System2A and System2B were not imported. The original Canva deck and architecture whiteboard were not modified.

The canonical report destination is the private Sites project `appgprj_6aa3b5418c2881919812b96064615173`. Its standalone checkout is `/Users/tang/.codex/visualizations/2026/09/11/01a08f51-7160-78f3-8dba-96e14beec338/requirement-report-site`. Deployment status and exact published identifiers are recorded in its `PROJECT_STATE.md` and summarized in the workstream root state after deployment success.

Future report refreshes use the same Site ID and URL. Synchronization is an explicit source-to-report release, not automatic ingestion of live databases or an enabled recurring job.
