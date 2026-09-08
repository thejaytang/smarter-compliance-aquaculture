# System1 Local Snapshot Intake and Format Contract v1

Status: 2026-09-07, governed multi-format intake in the saved project. System1 owns selection and snapshots. This interface does not download, discover sources, scan history or modify workbooks. It is not the shared workbench or a complete human-review service.

## Inputs and eligibility

Normal intake uses `--system1`, calling the read-only `read` operation of `system1.workbench_bridge` through System1's environment and consuming `effective_selection`. Source review and selection scoring belong to System1; System2 does not repeat them. Resolve workbook/Data paths from System1 configuration and verify configuration/workbook versions before and after the call to prevent mixing save states.

`system1-handoff.json` records effective selections, source revisions, bridge revision, configuration hash and registry hash for explicitly requested source IDs. The manifest binds its hash. Do not import task/history copies or call apply, random_qa, downloads or Routine Cycle. Recheck input versions at batch completion; changes cause failure while generated evidence for the previous version is retained.

The compatible `--registry --source-root` offline entry uses `read_registry` to read one immutable workbook-byte snapshot. It requires cached `selection_status` values and rejects missing caches. System1 refreshes formula/chart caches in every atomic save; its state owns the current evidence. Intake does not replace that responsibility. Revalidate source versions before admission to a future persistent queue; old manifests cannot be replayed indefinitely.

Calls must specify source IDs explicitly. Process only unique registered records satisfying `operator_selection_decision=INCLUDE`, `selection_status=INCLUDE`, `snapshot_status=STORED`, `source_status=CURRENT` and `download_status=SUCCESS`. In normal intake, `selection_status` is the compatibility name for System1 `effective_selection`. These gates verify agreement between upstream eligibility and the actual snapshot.

The production scope includes System1 INCLUDE sources only. Gates for other sources protect intake; they do not create parsing or replacement tasks. An Excel file not included by System1 does not block production completion.

Resolve `folder_code/stored_filename` relative to System1 Data at invocation. Reject absolute paths, parent traversal, injected separators, escaping symlinks and snapshot/source-ID mismatches. Compare registered `content_hash` after reading and revalidate before execution. Preserve source/snapshot IDs, relative path, original hash, human/effective selections, source/snapshot/download states and registry hash. Conflicting or missing registry records are separately `rejected`; do not fill gaps by scanning other files.

## Formats and Canonical

Extensions route HTML/PDF/Excel, checked against registered format and obvious signatures. XLSX also requires internal workbook/content-types ZIP parts. XLS receives an OLE-signature check only and explicitly remains unimplemented. See the [Excel contract](excel-document-v1.md) for XLSX parsing and independent verification; formulas and macros are not executed.

`source-parse-result/1` is the shared index contract for source, status, reason and the relative reference/hash of the sole Canonical artifact. It is not another fact store. HTML defaults to `html-document/2` (see [v2](html-document-v2.md)); the explicit legacy template retains `html-structure/1`. PDF retains schema 1.5. Source/artifact indexing is shared; a fine-grained cross-format schema is not complete. Do not fabricate PDF page/bbox geometry for HTML.

HTML v2/XLSX passing source verification also generates the [v2 source-content projection](source-records-v2.md), covering Lovdata clauses, ASC Indicators, five HTML source-content families and GLOBALG.A.P. IFA v6 Smart/AQ. The explicit v1 entry remains. Projections have independent consistency verification and bound hashes; they cannot overwrite Canonical.

Default v2 supports Lovdata, ASC and three government page families, with independent source verification in each batch. See [HTML v2](html-document-v2.md) for fields, boundaries, failures and compatibility. Legacy `lovdata-document-v1` clause rules remain an explicit compatibility entry; revision notes below are historical evidence.

## Human conversion of other formats

User confirmation on 2026-09-08: automatic parsing targets HTML, XLSX and PDF only. Other formats enter a dedicated human-conversion
channel in the existing workbench. Convert according to content, verify completeness and register original/copy lineage before
re-entry. Preserve the original; the conversion is a parsing copy, not the official published format. Conversion eligibility does not replace
the existing INCLUDE decision, and conversion completion is not parsing acceptance. See the [format pipelines](../architecture/06-format-pipelines-and-human-conversion.md).

This is an approved design awaiting implementation. The Snapshot contract still admits only its existing governed snapshots. Unknown formats
and legacy XLS retain unsupported/not-implemented results. Human conversion tasks and automatic converted-file registration are not implemented.

## PDF adapter

`formats/pdf.py` lazily calls existing `extract_pdf` without changing its public entry or Canonical contents. Freeze hash-verified bytes into the new run's `source.pdf` before parsing to prevent source changes on reread; originals remain read-only. `native/canonical.json`, native provenance, confidence, review policy, pages, review and derived artifacts remain the PDF fact source.

This entry requires one to four explicit zero-based page indices and local backends. Automatic model downloads and external models are prohibited. Explicit pypdf, pdfium and docling-parse are supported; the recommended configuration is `config/pdf-intake-positioned.yaml` with the locked docling extra. `config/pdf-intake-local.yaml` retains the low-cost pypdf route. The full-PDF CLI is unchanged. A page window does not establish whole-document completion; the low-cost route has lost structure on real samples.

The index retains PDF Canonical schema and verification report/hash. Native failure, Canonical validation failure or missing verification reports return failed, not a generic review_required wrapper.

Output directories must be new and outside the source root. Never overwrite existing results. Each item reports `review_required/blocked/failed/not_implemented`. `review_required` means reviewable machine artifacts exist, not human confirmation or parsing-accuracy acceptance.

## Excel and future workbench interfaces

The existing local workbench is the normal human-review entry. System2 produces review items/evidence, applies versioned decisions and supplies audit receipts; Workbench owns UI and server-bound operators. See the [integration plan](../plans/03-system2-completion.md). Reading existing artifacts does not establish production integration.

Ordinary XLSX supports `excel-document/1` and independent verification; legacy XLS remains `not_implemented`. See the [Excel contract](excel-document-v1.md). Excel export is downstream work, not a new operating interface.

The current PDF review service targets block/span/cell only. Requirement/field targets, omitted-content insertion, split/merge, field versions and complete decision contracts remain unimplemented. This index is not a complete workbench review-write interface. Read-only consumers follow result → Canonical → locator; future human decisions require separate contracts binding source and result versions.


## Historical non-PDF regression revisions | 2026-09-07

`lovdata-html/0.1.1` constrains actual ownership of headings, nested clauses and lists, and applies metadata configuration. Unrepresented section text produces specific `unrepresented_body_text` DOM issues; an issue does not establish structural recovery.

XLS/XLSX must match the registered format individually. Fully serialise JSON before exclusive publication; failure must not leave partial final results. Default CLI HTML configuration is independent of the working directory. Input/configuration errors create failed-batch receipts when a valid new output directory is writable. If storage cannot be created or written, persistence cannot be guaranteed; callers must also inspect the exit code. Excel content parsing was unimplemented at this historical checkpoint; current XLSX capability is defined above.

See the [targeted regression report](../reports/07-nonpdf-module-regression.md).


Performance revision `lovdata-html/0.1.2` caches completeness-scan heading recognition once per section, without changing Canonical fields or review issues. Four real files were identical except parser_version; see `../reports/08-html-template-matrix.md`. This revision did not expand template support.
