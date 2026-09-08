# Source-Clause Consumption Projection v1

This document retains the v1 contract. See [v2](source-records-v2.md) for the current default and expanded HTML content. Generate v1 explicitly; historical artifacts are not migrated.

`source-records/1` is a read-only Canonical projection for downstream review and System3 consumption.
Canonical JSON remains the sole structured fact source. Map only fields explicit in source structure;
do not infer legal effect, applicability, responsible actors, conditions or final compliance decisions. Existing
`requirement_status=not_extracted` is unchanged by projection generation.

## Inputs, versions and artifacts

Inputs are `html-document/2` or `excel-document/1`, with a `status=passed` source-verification report
binding both source and Canonical-file hashes. Missing, stale or mismatched reports reject projection.

Successful batch items generate three companion files:

- `source-records.json`: original field text, locations, residual inventory and issues.
- `source-records-verification.json`: completeness and consistency checks from Canonical to fields.
- `source-records-result.json`: hash index for both companions, upstream Canonical and source-verification report.

`source-parse-result/1` remains compatible. Consumers read `result.json`, verify Canonical and
source-verification references, then read the companion index and compare all hashes. Missing companions in old results
mean projection was not run, not zero clauses. Projecting historical Canonical does not reconfirm current source selection;
production-queue entry requires current System1 source versions.

## Fields and locations

Each record has `id`, `kind`, `source_anchor`, original-format `locator`, `fields` and `issues`.
A field may comprise ordered source fragments, each with `text`, `present/empty/missing` status and
`references`. `references.pointer` identifies the exact Canonical text scalar; `locator`
preserves DOM or sheet/cell coordinates. Concatenated references must exactly equal the fragment, without added spaces or changed punctuation.

`source_anchor` identifies source structure and need not point to a JSON container. Excel anchors retain
actual row numbers; text references point to scalars in the cells array. Record IDs must be used with source and
Canonical versions. Machine fields retain `confidence=null` and `review_required`.
Parsing review here does not invalidate completed System1 source reviews.

## Explicitly supported source templates

**GLOBALG.A.P. IFA v6 Smart / AQ**: after uniquely matching the actual nine-column header, create Principle-row
records, allowing shifted header rows and columns. Map Standard, Version, Product Category, Principle,
Section, Description, Criteria, NIG and Level. Audit answers, Justification and Site information are
not standard requirements. Formula fields without literal source text retain missing issues; caches are not standard text.
Preserve and flag duplicate IDs and missing body/criteria/level values rather than deleting records.

**Lovdata clauses**: map number, title, body, footnotes and ancestor headings separately. Keep nested clauses separate;
body follows source-atom order, footnotes are not duplicated in body, and sharing/navigation controls remain residual.
Canonical retains table/list geometry, markers and links; do not flatten these into inferred business fields.
Preserve clauses lacking numbers or body, including `(Opphevet)`-only headings, without inventing content or legal effect.

Other HTML/Excel templates return `not_supported` projections while retaining usable Canonical.
Every nonempty text reference must appear in mapped fields or `residual`. Residual includes unmapped sections/annexes,
source controls, audit data and nonliteral formulas. Complete inventory does not establish domain interpretation.

## Verification boundaries and failure propagation

An independent projection verifier reconstructs clause ownership, field order, source references and residual content from Canonical
without calling the mapper. Deleted clauses, swapped fields, changed text/locations, missing footnotes, reordering, residual omissions or stale hashes
fail verification. This checks projection consistency, not another independent original-source evidence channel. Upstream HTML/XLSX
source-verification reports remain bound. Projection-verification failure fails the batch item while preserving Canonical and
verification evidence.

See the [clause and handoff report](../reports/13-nonpdf-source-records.md) for acceptance evidence.
