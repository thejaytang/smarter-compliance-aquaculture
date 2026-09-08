# Phase Two Implementation Objective

Implement all requirements in [phase two](../architecture/02-capabilities-and-accuracy.md), preserving backward compatibility with phase one and existing Canonical JSON.

## Execution constraints

1. The phase-two design is the sole requirements source. Audit existing implementation, then implement, test and repair until every completion criterion passes.
2. TODOs, empty implementations, placeholder adapters, entirely mocked tests or weaker acceptance criteria do not count as completion.
3. When an external model/component is unavailable on the platform, provide a real runnable alternative and record backend, version, provenance, trigger and degradation reason.
4. Preserve phase-one data, IDs, coordinates, evidence and output conventions. Schema extensions remain backward compatible.
5. Use the project `.venv`; do not install dependencies into Conda base.
6. Use root `_PS3_副本.pdf` and necessary synthetic boundary PDFs for real end-to-end, schema, regression, repeated-run structural-equivalence and visible-content acceptance.
7. Every critical conflict must be resolved automatically, confirmed by a human or block document acceptance. Never accept silently.
8. Do not execute `git commit` or `git push`.

## Implementation method

Follow phase-two module boundaries, using automated tests and real outputs as evidence. First complete evidence/completeness/review flow, then cross-page assembly, fallbacks and links, then Gold, stratified evaluation and regression gates. Run relevant tests after each module. Finally run the full suite and the same real PDF twice, comparing structural fingerprints and quality reports.
