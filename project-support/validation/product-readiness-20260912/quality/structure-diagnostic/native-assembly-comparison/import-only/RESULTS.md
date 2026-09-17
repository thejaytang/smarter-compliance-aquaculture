# One import-only observation

**Result: IMPORT_COMPLETED_NO_PARSING.** The existing System2 environment imported the actual `DoclingPdfParser` symbol in **42.710 seconds**; the complete worker process exited 0 after **42.856 seconds**. The 300-second operational guard was not reached. No parser was instantiated and no PDF was opened. Product/source/config fingerprints captured in `freeze.json` remained unchanged.

The top-level `import docling_parse` completed in 0.0064 seconds and only initializes locale/logging. To exercise the dependency chain that previously stalled, the same worker then executed `from docling_parse.pdf_parser import DoclingPdfParser`, exactly the symbol imported by the existing adapter. This remained an import-only test with no `NativeExtractor.extract`, application creation, model initialization or external processing. An audit hook rejected socket connection/address-resolution and subprocess requests; none caused a failure. Temporary caches and working directory were isolated, bytecode writes disabled, and offline flags set.

## Distinguishing evidence

- The previously observed `_philox` import now took **2.717 ms**; `_sfc64` took **3.378 ms**.
- Successive import-log observations advanced through separate pandas modules. `pandas.io.common` alone consumed about 5.898 seconds of self import time.
- The single 30-second faulthandler snapshot showed `importlib.get_data → get_code` in the pandas dependency chain, rather than the prior `_philox` extension creation frame. Import subsequently completed.
- Actual loaded paths for Docling, pandas, NumPy, `_philox`, `_sfc64` and `cv2` all resolved inside the existing System2 `.venv`. No copied package tree was used.

This distinguishes **eventual slow import with progress** from a persistent block at the same extension for this observation. It supports separating dependency readiness from parsing in the next experiment: a single end-to-end 60-second timeout can conflate expensive imports with parser work. It does not prove that the previous failed attempt would have completed, that every subsequent import is fast, or that cloud/file-provider materialization caused the delay. `-X importtime` adds instrumentation, and the environment had already been exercised by prior attempts; this is not an independent cold-start benchmark.

## Next decision

The existing frozen Farm/Interpretation DEV comparison can now reasonably resume in a **new preserved run** with explicit import-ready observation and correct actual-backend provenance. Keep the same sources/windows/engineering annotations and denominators. Do not overwrite the original 60-second failure or change the production backend based on this import observation. This subtask does not execute that comparison.

Quality remains **UNMEASURED** for the incomplete Docling-versus-PDFium comparison. Installed native `docling-parse` is not the complete learned Docling pipeline; font evidence or hidden text still cannot establish a correct visible heading.

Evidence: [freeze.json](freeze.json), [receipt.json](receipt.json), [summary.json](summary.json), [stdout.log](stdout.log), [importtime-and-stacks.log](importtime-and-stacks.log), [runner](run.py) and [import-only worker](observe_import.py). The runner refuses to overwrite its observation outputs.
