# Frozen native backend comparison: run 2

**Result: STOPPED_PARSER_INITIALIZATION_RESOURCE_ERROR. Comparative quality remains UNMEASURED.** The newly separated readiness phase completed for both Farm conditions. Docling then failed while constructing `DoclingPdfParser`, before loading the document and before producing any native/candidate output. The failure is `RuntimeError: no FontName found .../docling_parse/pdf_resources/fonts//standard/Helvetica.afm`. This was a concrete constructor/resource failure, not an import or parsing timeout.

| Condition | Readiness | Parsing | Process outcome |
| --- | ---: | ---: | --- |
| Farm PDFium | 0.309 s | 0.134 s | Completed, exit 0; 44 blocks; candidate partial |
| Farm Docling | 0.979 s | Failed during constructor | Exit 1 after 3.144 s total; no native/candidate output |
| Interpretation PDFium | Not started | Not started | Stopped after the new failure |
| Interpretation Docling | Not started | Not started | Stopped after the new failure |

Readiness includes adapter/source preparation and imports through the actual backend and layout dependency paths. No parser was instantiated before readiness. The 300-second readiness and 60-second post-readiness guards are operational process guards, not quality thresholds or a work-time target. Each worker was observed through its existing process handle, with no observation-timeout retry.

## Frozen scope and provenance

`freeze.json` and `docling_experiment.py` are byte-identical copies of run 1. Sources remain Farm pp 28–29 (zero-based 27,28) and Interpretation pp 19–21 (zero-based 18,19,20), with unchanged engineering annotations, critical-phrase definitions, marker relations and denominators. `resumption.json` records the new runner/configuration hash separately from the unchanged original freeze. The assessor only changes its output directory from run 1 to run 2; no matching rule changed.

The sole completed control has actual backend `pypdfium2`. Its 44 blocks equal the frozen run-1 control exactly, and all source-fragment payload/order/ref reconstruction invariants pass. The experimental source preserves the native Docling version/policy/provenance distinction, but it produced no Docling result to assess. No reserved document was used.

## Completed-control diagnostic only

The unchanged Farm control retains 18/25 complete page-bound engineering source segments, 6/6 single-block formal texts, 7/7 single-block clause texts, 9/9 labelled critical phrases, and 2/2 frozen marker relations. It has 34 text, 4 table, 6 image and 0 heading blocks. These overlapping active-DEV diagnostics do not measure an independent acceptance set or demonstrate a backend gain. Unrun or failed conditions are not counted as passing.

## Decision

Stop this comparison without further retry or environment repair. Import readiness is now separated successfully, but parser construction still has an unresolved resource-read/interpretation failure. The error moved from earlier Times/Arial resources to Helvetica in this observation; no resource content was read again, so this run cannot establish corruption, file-provider behavior or another OS cause. Import-only success does not guarantee successful parser initialization.

Do not change the production backend or claim structure/quality improvement. Original sources, annotations, product parser/native extractor, positioned configuration and dependency declarations remain unchanged. Run-1 timeout artifacts remain preserved.

Evidence: [final-status.json](final-status.json), [resumption.json](resumption.json), [Docling failure receipt](asc-farm-docling-receipt.json), [full constructor stack](asc-farm-docling-stderr.log), [control receipt](asc-farm-pdfium-receipt.json), [completed-control assessment](assessment.json), and [unchanged freeze](freeze.json).
