# System3 Project State

State updated: 2026-09-07. Documentation updated: 2026-09-08.

Shared entry points are [README.md](../README.md) and [AGENTS.md](../AGENTS.md) at the `05` root, alongside the systems. There is no separate system entry contract. The shared README links directly to specialist documents. Historical entry locations describe their original state. Integration facts belong to `../PROJECT_STATE.md`; the launcher is also at the `05` root.

## Current facts

- The user supplied a shared design discussion. Its meeting notes, user corrections and final direction have been read.
- The directory now has an explicit purpose: Requirement semantic enrichment and Site Model interface design. Keep the `system3` name; independent runtime deployment is undecided.
- Design evidence and candidate fields belong to `docs/design-basis.md`. There is documentation only, with no running code, automatic handoff or consumer-approved schema.
- Read-only inspection of System2 `domains/requirements/canonical.py` found applicability, conditions, modalities, exceptions and thresholds. Upstream output is not limited to raw text, but those fields do not by themselves establish consumer fit.

## Current checkpoint

Decision: `ADJUST`. Validate the consumer's semantic contract before deciding implementation ownership. Source records, System3 entry documentation and shared navigation are aligned. No code migration or external team contact was performed.

Next experiment: select 5 to 10 real requirements and compare System2 outputs with the candidate contract, identifying existing fields, enrichment gaps and unknowns.

- Hypothesis: these fields support Requirement-to-site mapping by the Site Model team.
- Evidence: real sources, field-level locations, upstream artifacts and consumer mapping feedback.
- Success: objects, conditions and actions can be mapped; gaps and ambiguity are traceable; consumers confirm usability.
- Failure response: adjust the contract to observed gaps before expanding an ontology or compliance engine.
- Automation implementation gate remains unmet: no real sample-mapping results or consumer acceptance are available.
