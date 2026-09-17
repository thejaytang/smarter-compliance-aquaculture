# Modular Migration Plan

## Objective

Migrate the large pipeline into a modular monolith composed through stable contracts,
without changing input PDFs, Gold annotations, historical baselines or external interfaces.

## Working assumptions at plan creation

- One project environment and process are sufficient for current scale; microservices are unnecessary.
- Existing parsing capability and Gold regression protect migration rather than justify rewriting.
- The directory had no `.git` metadata at plan creation, so migration required small compatible steps retaining runnable entries.

## Checkpoint 1: Public boundaries

Status: `CONTINUE`.

Completed:

- Created public `contracts`, `preflight`, `evidence`, `extraction`, `canonical`,
  `verification`, `domains`, `delivery` and `orchestration` boundaries.
- Moved the actual `ExtractionPipeline` to `orchestration`, retaining a facade at the old path.
- Established per-atom confidence/review contracts; human review is orthogonal to verification
  depth.

Success gate: old/new entries import and targeted regression passes.

## Checkpoint 2: Split the orchestrator

Status: `CONTINUE`; this round's target scope is complete.

Gradually extract implementations from `orchestration/pipeline.py` into stage runners:

1. workspace/runtime preparation；
2. preflight and evidence acquisition；
3. page extraction；
4. document assembly；
5. reconciliation；
6. canonical finalization；
7. delivery。

Every stage uses explicit context/result dataclasses instead of implicit global state. Failures include stage,
input-artifact hash and recoverability information.

Success gate: no unexplained behavior/artifact-hash changes on fixed small samples; the pipeline file retains
composition logic only.

This round completed explicit workspace/runtime preparation and Canonical finalisation
runners and added verification routing as an independent production stage. A fixed one-page sample
passed, producing `canonical.json`, `verification-report.json` and all derivatives. The legacy
`ExtractionPipeline` import remains valid.

Page parsing still resides in `orchestration/pipeline.py` because backend lifecycle,
page cache and block assembly share substantial state. After establishing fixed real-PDF hash comparisons,
migrate it incrementally into page-extraction, assembly and reconciliation runners. This belongs to
the next planning window and does not roll back stable public boundaries.

## Checkpoint 3: Fidelity verification

Status: `ADJUST`. Atomic production-review routing is complete; independent verification remains future work.

Build an independent `VerificationPipeline`:

- Accept Original PDF, CanonicalDocument and VerificationPolicy;
- Record confidence, threshold, provenance, evidence paths and review
  disposition；
- Support `internal`, `source`, `independent` and `strong` machine evidence depths;
- Apply human-review routing at every depth.

Success gate: low/missing confidence, evidence disagreement and missing provenance
reliably trigger review; Gold validates confidence calibration.

Production EvidenceSpan now records confidence, threshold, path IDs, reason codes and
`requires_human_review`, and produces `VerificationReport`. Minimum evidence-path requirements for machine depth are
enforced. Independent `VerificationPipeline` and Gold confidence calibration remain unimplemented;
this is not complete fidelity-verification product acceptance.

## Checkpoint 4: Implementation namespace migration

Only after checkpoint 2/3 regression stabilises should `requirements`, `regulatory_ir`,
`export` and related implementations move into new boundaries. Migrate one capability package at a time, retaining deprecated
facades until all internal callers switch.

## Stop conditions

Choose `BACKTRACK` or `STOP` if:

- Canonical hashes drift without explanation;
- Migration changes Gold source segments, annotations or manifests;
- Review-item counts fall while accepted-result precision also falls;
- A new boundary duplicates models into a second source of truth.
