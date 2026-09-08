# System2 Canva Flowchart Delivery

Date: 2026-09-08.

## Current revised artifact

- Canva design: `DAHUmF-8SUQ`, four fixed 1920 × 1440 pages.
- Title: `System2 处理流程 · 清晰分图版`.
- [Open the revised design](https://www.canva.com/design/DAHUmF-8SUQ/edit).
- [Local four-page HTML](../../outputs/diagrams/system2-flow-v2/system2-flow-v2.html).
- Import job: `4321d880-7ecc-49ad-b16d-5f90698b6f7a`, returned `success` with four pages.

The user rejected the original whiteboard because its text and connectors were cluttered. A deterministic grid replaced that layout with one overview and three PDF detail pages. Main branches have separate lanes; cross-page references replace long cross-diagram connectors. Optional engine paths and pending workbench/conversion integration remain labelled. Unresolved PDF evidence retains its status in Canonical rather than bypassing the result pipeline.

Verification: inspected all four local renders, then all four pages in the authenticated Canva full-screen view. Canva rich-text readback retained the labels, and the editor reported `All changes saved`. The local artifact has 61 nodes and 68 orthogonal connector paths; geometric checks found zero paths crossing unrelated nodes, and browser DOM checks found zero node text overflows. Text imports as Canva text; connector lines import as positioned graphics, not automatically rerouting Canva connectors. User acceptance of this revised layout is still open.

## Superseded first artifact

- Canva design: `DAHUmEoM0Q4`, one editable whiteboard.
- Title: `System2 全流程与 PDF 精细处理管道`.
- [Open the saved design](https://www.canva.com/design/DAHUmEoM0Q4/edit).
- Module detail and implementation references: [format-pipeline architecture](../architecture/06-format-pipelines-and-human-conversion.md).

The diagram separates HTML, XLSX and PDF processing and retains the proposed human-conversion channel. PDF expands into page evidence routing, layout/content regions, fine-grained table processing, cross-page assembly and conflict/source checks. Optional paths and the restricted local 1–4-page intake are labelled; PDF accuracy remains pending. Common result/review nodes sit outside the PDF frame.

## Recovery and verification evidence

The connector's initial generation job `774aa2ed-3b38-4290-8cb6-d62331495024` returned `in_progress` without candidate IDs or a finished-design URL. The user confirmed no candidate card appeared. A subsequent account search found only the older unrelated presentation. That job was not used as completion evidence.

The authenticated Canva web editor created the whiteboard above. `get-design` confirmed its identity and `get-design-content` returned the actual Chinese labels for native/scanned/mixed page routing, region OCR, table cells, cross-page decisions, Canonical/source checks and pending human integration.

An AI follow-up edit requested a premium feature and did not apply the requested changes. A connector inspection transaction reported the whiteboard page as `is_editable=false`; it was cancelled without applying changes. The saved design remained intact. Ordinary browser editing then added inter-stage connectors and resized the PDF/verification background frames to separate common outputs. Temporary mis-clicks were undone. No upgrade or purchase was made.

The first canvas was inspected in fit view and at 47–50% zoom, and the editor reported saved changes. Those checks did not establish acceptable visual quality: the user subsequently rejected the layout. The original design is retained as history and is superseded by the four-page revision above.

No parsing job, source download, original-file conversion, workbook update, Gold change, baseline migration, publication or Git commit was performed.
