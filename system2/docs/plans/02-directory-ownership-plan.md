# Directory Responsibility Consolidation Plan

Status: `CONTINUE`; this round's scope is complete.

## Objective

Reduce confusion from public modules alongside historical implementation directories under `src/pdf_extraction/`, while
preserving CLI, API, worker and Python-import compatibility.

## Target structure for this round

```text
src/pdf_extraction/
├── contracts/
├── preflight/
├── evidence/
├── extraction/
├── canonical/
├── verification/
├── domains/
│   ├── requirements/       # Canonical Requirement implementation
│   └── regulatory/         # Canonical Regulatory IR implementation
├── delivery/
│   ├── exporters/          # Markdown/HTML/XML/RAG/overlay
│   └── ontology/           # RDF/SHACL
├── evaluation/
├── orchestration/
├── api/
└── review/
```

During migration, `requirements/`, `regulatory_ir/`, `export/` and `ontology/` are deprecated
compatibility facades only, without business implementations or a second source of truth.

Organise tests by responsibility:

```text
tests/
├── contracts/
├── unit/
├── integration/
└── domains/
    └── requirements/
```

## Constraints

- Do not modify, move or delete `data/inputs/`, Gold annotations/manifests, historical baselines or
  run artifacts。
- Do not change external `pdf_extraction.pipeline`, CLI, API or worker entries.
- Each old namespace forwards to one canonical implementation; do not duplicate business code.
- Do not migrate layout, parsing, assembly or reconciliation in this round. Their deep state-sharing with page extraction
  requires a separate migration after real-PDF artifact comparisons are established.

## Validation gates

1. Old/new import paths identify the same objects.
2. Module-boundary tests pass.
3. Targeted Requirement, Regulatory IR and delivery tests pass.
4. Full `pytest` has no new failures.
5. Inputs, Gold and historical baselines are unchanged.

## Implementation results

- Canonical Requirement and Regulatory IR implementations moved into `domains/`.
- Exporters, ontology and the derived-artifact writer moved into `delivery/`.
- The four old implementation directories retain only `__init__.py` compatibility facades.
- Tests are grouped under `contracts/`, `unit/`, `integration/` and `domains/requirements/`;
  `tests/support/paths.py` resolves the shared project root.
- `tests/contracts/test_namespace_layout.py` prevents parallel business implementations from returning to compatibility directories
  and prevents internal code from depending on old facades again.
