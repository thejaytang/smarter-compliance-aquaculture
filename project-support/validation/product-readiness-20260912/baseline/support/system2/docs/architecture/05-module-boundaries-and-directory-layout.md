# Module Boundaries and Engineering Structure

## 1. Architecture decision

Use a modular monolith: one repository, one project environment and one Canonical
artifact contract, with independent modules composing the complete workflow. Do not split into microservices at this stage.

Modules are defined by decision ownership rather than directory names. Each owns one primary class of decisions,
collaborating through versioned input/output contracts without depending on other modules' internal temporary state.

## 2. Stable processing chain

```text
PDF
 -> preflight
 -> evidence acquisition
 -> extraction
 -> canonical validation
 -> fidelity verification
 -> domain interpretation
 -> delivery
```

`orchestration` owns call order, run state, caching and failure propagation only. It owns no parsing,
verification or domain-decision rules.

## 3. Module responsibilities and contracts

| Module | Primary question | Input | Output |
|---|---|---|---|
| `contracts` | What do modules exchange? | No runtime input | Stable versioned models |
| `preflight` | What kind of PDF is this, and which route applies? | PDF | `DocumentProfile` |
| `evidence` | What is actually observed in the source? | PDF, page/region selection | `SourceEvidenceBundle` |
| `extraction` | How should the most likely correct structure be reconstructed? | Profile, source evidence | `CanonicalDocument` |
| `canonical` | Is the Canonical artifact internally valid? | `CanonicalDocument` | Invariant/schema errors |
| `verification` | Is Canonical faithful to source evidence? | PDF, Canonical, policy | `VerificationReport` |
| `domains` | What does Canonical mean in the target domain? | Accepted/reviewable Canonical | Requirement/Regulatory IR |
| `delivery` | How are consumer artifacts generated? | Canonical, domain artifacts | Markdown/HTML/XML/RAG/RDF |
| `evaluation` | How does the system perform on fixed evidence? | Predictions, Gold/manifest | Metrics/regression report |
| `orchestration` | How are these modules combined? | Run request, configuration | Run state, artifact references |

## 4. Dependency direction

```text
contracts
  ^
  +-- preflight
  +-- evidence
  +-- extraction
  +-- canonical
  +-- verification
  +-- domains
  +-- delivery

orchestration --> coordinates all modules
```

Stable rules:

1. `contracts` imports no business implementation.
2. `verification` may read PDFs, evidence contracts and Canonical artifacts, but must not call
   the extractor's final decision functions as proof of extraction correctness.
3. `domains` reads Canonical contracts, not temporary layout/OCR objects.
4. `delivery` must not modify Canonical or domain artifacts.
5. `evaluation` does not participate in production inference or inject Gold annotations into extraction.
6. Do not add layout, OCR, Requirement or verification rules to `orchestration`.

## 5. Verification depth and human review

Machine verification depth and human-review routing are orthogonal dimensions:

```text
machine depth: internal -> source -> independent -> strong
human routing: every atomic assessment -> confidence/policy -> accept or review
```

Every machine-generated or machine-judged atom carries confidence, provenance and an evidence
path. Below-threshold or missing confidence, incomplete provenance or evidence
disagreement requires human review. Human review is not restricted to the highest
verification depth.

Reduce human workload by improving recognition quality, evidence coverage and confidence calibration,
never by lowering thresholds or hiding review items.

## 6. Current source structure

```text
src/pdf_extraction/
├── contracts/       # Public cross-module contracts
├── preflight/       # Public preflight/profiling entry
├── evidence/        # Public source-evidence entry
├── extraction/      # Public extraction boundary and migrated region helpers
├── routing/         # Text-channel routing implementation
├── layout/          # Layout, reading order and marginal-content implementation
├── parsers/         # Block-type-specific parsers
├── assemble/        # Paragraph/table/document assembly
├── reconcile/       # Conflict, span and abstention implementation
├── canonical/       # Canonical schema and invariant validation
├── verification/    # Fidelity verification and per-item human routing
├── domains/
│   ├── requirements/ # Requirement canonical implementation
│   └── regulatory/   # Regulatory IR canonical implementation
├── delivery/
│   ├── exporters/    # Markdown/HTML/XML/RAG/overlay implementation
│   ├── ontology/     # RDF/SHACL implementation
│   └── writer.py     # derived artifact writer
├── requirements/    # deprecated compatibility facade only
├── regulatory_ir/   # deprecated compatibility facade only
├── export/          # deprecated compatibility facade only
├── ontology/        # deprecated compatibility facade only
├── evaluation/      # Gold and regression evaluation
├── orchestration/   # Pipeline orchestration
│   ├── context.py   # Run paths, fingerprints, resume and state contracts
│   ├── finalization.py # Canonical validation and delivery-stage runner
│   └── pipeline.py  # Compatible main entry and stage composition
├── api/             # REST/worker adapter
└── review/          # human-review adapter
```

Compatibility namespaces remain temporarily to protect Gold regression, CLI, API and historical scripts. They may only
forward to canonical implementations and must not regain business logic. Enforcement belongs to
`tests/contracts/test_namespace_layout.py`. New code uses the public `domains` and `delivery`
entry points.

Test structure:

```text
tests/
├── contracts/              # Module boundaries, schemas and compatibility
├── unit/                   # Focused capability tests
├── integration/            # Cross-module, API and pipeline integration
├── domains/requirements/   # Requirement semantic/Gold regression
└── support/                # Shared test paths and infrastructure
```

## 7. Fact ownership

| Fact type | Canonical source |
|---|---|
| Stable operating rules | System2 section of [AGENTS.md](../../../AGENTS.md) at the `05` root |
| Shared human entry | [README.md](../../../README.md) at the `05` root |
| System2 installation and operations | `system2/USER_GUIDE.md` |
| Current engineering state and next checkpoint | `PROJECT_STATE.md` |
| Stable architecture and module boundaries | `docs/architecture/` |
| Current complex-refactoring plans | `docs/plans/` |
| Domain contracts | `docs/contracts/` |
| Historical experiments and decisions | `docs/reports/` |
| Executable policy | `config/`, schemas and tests |

Conversation history is not the source of truth for project state.

## 8. Current stage contracts

`RunContext` and `RunPaths` are explicit shared orchestration contracts, owning output directories, configuration
hashes, source fingerprints, resume decisions, timing and state callbacks. Stages must not independently recompute or
maintain parallel run state.

`FinalizationInput` is the explicit finalisation input contract. `FinalizationStage` only composes existing
Canonical validation, verification reports and the delivery writer. It contains no layout, OCR,
Requirement or field-decision rules.

Per-atom verification is implemented in `verification/evidence_routing.py`. Existing native/OCR EvidenceSpan
paths satisfy `source` depth. Without additional paths declared
`independent_from_generation`, `independent` and `strong` fail closed into human review. High
confidence cannot bypass evidence-depth requirements.
