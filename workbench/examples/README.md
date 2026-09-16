# Current Workbench example: ADF-10

The requesting user supplied a Norwegian HTML excerpt and matching Markdown, with an English requirement decomposition (`ADF-10`). `example.html` and `example.md` retain the supplied source words and chapter links; only the presentation headings and HTML code fence are removed. `example.json` is the supplied JSON unchanged. `example-workbench.json` records the normalization and fourth-pane check design.

Open **Material review → example (PE001)** on the authoring installation. It is pinned first for the requesting reviewer. The former demonstration remains available as an older source/material version.

## Four entries

- **R1:** the shared operational-journal obligation. Its Subrequirement links require all three entries R2, R3 and R4.
- **R2:** incoming/outgoing animals and products, including both origin and destination. The location group retains `[2,2]`.
- **R3:** mortality per production unit, qualified by relevance to the production method.
- **R4:** results of completed health inspections. The five listed information categories retain `[5,5]`.

Each child entry includes the original lead-in plus its own bullet through multi-block source references. This makes inherited scope and modality explicit without introducing new source words. Group counts apply to listed required categories; they do not cap records or forbid additional journal information.

## Fourth pane

Scope, Conditions and Demands retain source wording. Their editable Logic fields explain object identification, applicability and evidence checks in English. The applicability expression is `NOT (covered_by_chapter_4 OR covered_by_chapter_5 OR covered_by_chapter_6)`, presented as a proposed logical interpretation, not an executable Site Model query. The linked chapters are not included here, and the excerpt gives no fixed update interval. Those gaps remain explicit. R1 composes its child checks with AND; missing evidence never becomes a passing result.

Saved content is not reviewed or adopted legal evidence. No live model, Site Model query or compliance verdict was used. These portable files alone do not install database records elsewhere. [Local installation and verification](../../project-support/workbench-example-adf10-20260916/RESULTS.md).
