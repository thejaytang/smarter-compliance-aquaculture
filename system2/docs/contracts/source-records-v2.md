# Source-Content and Clause Consumption Projection v2

`source-records/2` extends the read-only [v1](source-records-v1.md) projection, retaining upstream hashes,
text references, confidence/review policy and the source-verification gate. Canonical remains the sole structured fact source.
New batches default to v2. The v1 model, schema, mapper and explicit CLI remain; historical artifacts are not migrated.

## Records and structure

- GLOBALG.A.P. `standard_principle` and Lovdata `source_clause` retain their IDs,
  original fields, missing values and issues. Excel source formulas are not executed; audit answers are not standard requirements.
- ASC `standard_indicator` recovers number, body and applicability from actual `indicator-id`, `indicator-content` and
  `indicator-applicability` columns. Annex `table-row.indicator-row` structures use
  the source `table-cell.indicator` number column and other text columns. Paragraphs explicitly labelled `Indicator applicability:`
  are mapped separately. Applicability without a separate declaration stays missing; filter labels cannot supply it.
- `indicator-row--not-in-use` creates a `source_marked_not_in_use` issue while preserving the record and original CSS state.
  Machines must not delete the record or infer legal effect from that state.
- Other content in the five supported HTML template families creates source-structured heading, paragraph, table-cell,
  list-item, note, caption, definition or direct-text records. These are source-content units, not automatically
  extracted normative requirements. Unknown templates remain unsupported.
- Images retain separate `source_image` records and untranscribed issues; textless links retain `source_link`.
  Do not execute page scripts, load remote targets or invent text from images.

Every HTML record's `structure` consists of Canonical pointers with locators:

| Reference | Purpose |
| --- | --- |
| `/nodes/{i}` | Original DOM nodes/ancestors, section/annex paths, attributes, display conditions and Canonical heading context |
| `/tables/{i}`, `/tables/{i}/cells/{j}` | Original rows/columns, spans, empty cells and table issues |
| `/lists/{i}` | List type, item ownership and source labels |
| `/links/{i}` | Internal footnotes, external links, missing/ambiguous targets and access status |

Do not duplicate geometry or join different cells into sentences without column boundaries. Referenced Canonical tables
fully represent empty cells. Nested-table text belongs to its own cells; footnote text stays in
notes or separate note records and must not silently enter table values. Unmapped incidental text remains `source_text`.

New content anchors append `:content`, `:image` or `:link:{i}` to source node IDs. Order records by anchor
DOM order. Text fragments preserve exact atom pointers and original sequence. Nonadjacent residual text
remains separate fragments, without invented joining spaces. Record order is not a flattened reading order for all tables/nesting.

## Coverage and review

Every nonempty Canonical text belongs to a field or residual; metadata, controls and navigation remain explicit.
Complete coverage means no text disappeared at this layer, not human acceptance of field semantics. Image, unresolved
interactive-footnote and display-variant issues remain. `requirement_status=not_extracted` is unchanged.

The independent verifier reconstructs field ownership, source order, nontext records and structure references from Canonical
without calling the mapper. Missing cells/images/footnotes, incorrect geometry references, mixed fragments, altered applicability or
removed inactive markers fail. This is not another independent original-source channel; original evidence remains bound by source verification.

## Entry points and scope

`source-records-result.json` adds `source_records_schema_version`. Consumers must check the version
and every bound hash. Generate the legacy version explicitly:

```sh
PYTHONPATH=src .venv/bin/python -m pdf_extraction.orchestration.source_records \
  --canonical outputs/runs/EXAMPLE/canonical.json \
  --verification outputs/runs/EXAMPLE/verification.json \
  --output outputs/runs/EXAMPLE-v1 --schema-version source-records/1
```

Production scope includes only current System1 `INCLUDE` sources with valid snapshots. Other source gates protect
intake and do not generate parsing, replacement or repeat-review tasks. Excel files not INCLUDE do not block current production
completion. Local reference-XLSX diagnostics cannot establish production intake.

See the [completion report](../reports/14-nonpdf-content-completion.md) for validation and remaining source issues.
