# Phase Three Implementation Objective

Implement all requirements in [phase three](../architecture/03-complete-product-implementation.md), yielding a deployable, reviewable, traceable, reproducible and ontology-ready product.

## Execution constraints

1. The phase-three design is this phase's sole requirements source. Phase one, phase two and existing Canonical JSON remain mandatory compatibility baselines.
2. Audit implementation gaps, then implement, test and repair until all completion/release gates pass. Do not claim completion by narrowing scope, lowering thresholds or rewriting requirements.
3. TODOs, empty implementations, fixed-example endpoints, display-only UI, entirely mocked tests, fabricated model results or manually edited exports cannot replace real functionality.
4. Canonical JSON remains the sole structured fact source. Human decisions, Regulatory IR, RDF, RAG chunks, HTML, XML, JSONL and other derivatives must use formal Canonical interfaces, without independent competing fact stores.
5. Every accepted critical fact traces to source PDF page, bbox, block, segment and evidence. Model-generated content belongs only in `derived` or review and cannot overwrite native evidence.
6. Human review supports block/span/cell acceptance, editing, rejection and `unreadable`, with append-only immutable audit events. Rerun validation and derivation after changes.
7. CLI, Python API, REST API and background worker share one pipeline/state model, with real job persistence, retained failure artifacts, recovery and retries.
8. Enforce preflight, resource limits, sensitive-log controls, temporary-file governance and local/hosted routing at runtime. PDF text is untrusted data and cannot change instructions or execution policy. Hosted OCR/VLM is disabled by default.
9. Use the project `.venv`, not Conda base. Constrain new dependency versions and verify compatibility.
10. Validate with root `_PS3_副本.pdf`, existing target-domain Gold, real regulatory/standard production PDFs and necessary synthetic worst cases. Cover schema compatibility, fixed-PDF integration, repeatability, recovery, API/UI review, Regulatory IR, SHACL, security, performance and memory.
11. Critical conflicts, unprovenanced critical facts, SHACL violations and unreliable structures must be resolved, human-confirmed or block acceptance; never pass silently.
12. Do not commit/push or upload test documents/parsed content to external services without explicit authorisation.

## Implementation method

Turn phase three's ten completion criteria into executable acceptance gates. Build a gap matrix and freeze phase-one/two regression baselines. Then complete block parsers/page labels, unified derivatives, Regulatory IR and deterministic RDF/SHACL, source-grounded review UI, shared service interfaces/persistent worker, recoverable/observable runs, security/data governance, performance baselines and automatic release gates.

For each vertical capability, validate the complete flow from real PDF evidence through Canonical and human review to derivatives, then run relevant regression immediately. Finally run all unit, schema, integration, target-domain Gold, real-document, worst-case, performance, memory, API, UI, Regulatory IR and SHACL checks. Run the real root PDF twice and compare structural fingerprints. Completion requires reproducible evidence for all ten criteria without unacceptable regression.
