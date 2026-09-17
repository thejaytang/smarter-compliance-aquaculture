# 1. Resumed DEV native/assembly comparison

**STOPPED: dependency-import timeout. Quality comparison remains UNMEASURED.** Small-file preparation reads completed normally (four files in 0.0013 seconds), so one bounded comparison was started. No product source, backend configuration, original or Gold annotation changed.

## 1.1 Frozen experiment and provenance

The same existing development sources were selected: Farm pp.28–29 (zero-based 27,28), Interpretation pp.19–21 (18,19,20). `run-1/freeze.json` captures original/annotation hashes, existing segment/formal/clause denominators, labelled critical phrases, the eight-positive/one-negative marker subset, production code/config/lock hashes and backend versions before parsing. These are exposed engineering development references, not independent or business Gold. No reserved window was used.

`compare.py` runs each condition in a fresh process with a 60-second operational guard and 25-second stack snapshot. PDFium uses the original `/4` module. The Docling condition uses only an isolated source copy, `run-1/docling_experiment.py`, changing its adapter version, native backend policy and the hard-coded PDFium warning. Candidate/config/native provenance therefore cannot falsely report PDFium if Docling executes. Original package paths are used; no copied dependency, installation, external call, model or full-document extraction is introduced.

## 1.2 Actual outcome

| Condition | Outcome |
| --- | --- |
| Farm / PDFium | Completed in 40.80s, 44 blocks; actual native backend `pypdfium2`; blocks exactly equal frozen `/4` output |
| Farm / Docling | 60-second process guard triggered during dependency import; no native output or candidate |
| Interpretation / PDFium | Not started after stop condition |
| Interpretation / Docling | Not started after stop condition |

The PDFium stack at 25 seconds was in the `cv2` native extension import. The Docling stack was in `numpy.random` native extension import through `pandas → docling_core → docling_parse`. This is concrete import-delay evidence, not a new FontName failure or evidence about parsing/structure accuracy. The exact OS cause remains unknown. No retry, resource repair or environment change was performed.

The completed control preserves all input group members and ordering exactly, including original text and source references. Its existing development diagnostics are: 18/25 complete page-bound annotated segments; 6/6 formal texts and 7/7 clause bodies in single editable groups; 9/9 labelled critical substrings; 2/2 Farm marker relations. These overlap and must not be pooled or presented as the absent Docling comparison. Its four tables and zero actual heading blocks remain unchanged. Font metadata or previous profiler confidence0.99 on occluded Criterion text is not a heading PASS.

## 1.3 Decision and continuation

Do not promote or adapt the product backend based on this incomplete comparison. The prior resource A/B/A experiment establishes richer native evidence availability in one successful warm run, not stable startup or measured paragraph/structure improvement. `docling-parse` remains a native-cell extractor, not the full learned Docling layout pipeline.

Evidence: [freeze](run-1/freeze.json), [final status](run-1/final-status.json), [control assessment](run-1/assessment.json), [Docling timeout and stack](run-1/asc-farm-docling-receipt.json), [PDFium receipt](run-1/asc-farm-pdfium-receipt.json), [runner](compare.py), [read-only evaluator](assess.py). Source/config/annotation preservation is verified in final status. The runner refuses to overwrite `run-1`; any later resumption must use a new evidence run while retaining this freeze, stopped partial directory and all receipts. It must not treat the earlier NOT_RUN record or this import failure as measured source-quality results.
