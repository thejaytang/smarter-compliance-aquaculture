# HTML Parser Implementation and Verification Objective

Status: complete. The user explicitly established this objective on 2026-09-07.

## Boundaries and completion gates

Read only currently selected, eligible local System1 HTML. Cover known Lovdata, Fiskeridirektoratet, Miljødirektoratet, Mattilsynet and ASC families. Reject empty bodies, unknown templates and invalid hashes/selections explicitly; correct negative-control rejection does not block implementation acceptance. Do not invent source text, download, call external models, run PDF parsing, implement Requirement semantics or build Workbench.

Completion requires all of:

1. Versioned HTML Canonical preserving source atoms/DOM paths for selected body regions, traceable structures, cells, lists, internal links/footnotes and filter/display attributes; no script or external-link execution.
2. At least one real sample per known template, with source-checked body boundaries/exclusions. Exclusions need reasons/locations; unsupported content is not noise.
3. Independent lxml source checks compare text/order, tables/cells and locations, detecting omission, duplication, rewriting, invalid exclusions and boundary errors. Include mutated-artifact failure tests.
4. Separate development samples from unseen-file retests, freeze source hashes and never alter samples to pass. Classify every eligible registered HTML in the final local registry retest; full content fidelity requires evidence.
5. Targeted tests and human structural inspection of real samples pass. Low confidence, source ambiguity and incomplete structure remain reviewable; do not lower thresholds.
6. Retain compatible entries; update state, reproducible commands and file-level merge manifests. Results at this checkpoint existed only in the worktree.

## Rolling horizon

A. Freeze sources/manual windows and define v2/template boundaries.
B. Implement template recognition, DOM/text atoms and table/list/link recovery, retaining explicit v1 configuration.
C. Run independent checks and fault injection; inspect real windows.
D. Retest non-development sources, respond to observed failures without hiding content, and produce the completion-gate report.

Choose CONTINUE/ADJUST from evidence at each stage. Nonempty or schema-valid artifacts alone cannot finish the objective.

## Completion checkpoint

`STOP`: implementation and frozen-static-corpus checks complete. Thirty positive sources passed, seven empty bodies were correctly rejected, ten source windows passed and 75 tests passed. Later upstream cache changes were recorded separately and must not be bypassed for new intake. See the [completion report](../reports/09-html-parser-completion.md).
