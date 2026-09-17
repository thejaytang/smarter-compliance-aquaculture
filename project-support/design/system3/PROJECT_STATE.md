# System3 current state

2026-09-16: Manual interpretation and check-design support is implemented inside the existing Workbench, under [the four-pane contract](../workbench/docs/requirement-interpretation.md). System3 remains the semantic/Site Model design owner, without a standalone service or executed compliance engine. Six editable interpretation fields feed a deterministic readable chain; AI suggestions are optional and share global Settings. [Workbench verification](../project-support/four-pane-20260916/RESULTS.md) owns implementation evidence. Earlier third-pane deferrals below retain their historical scope.

2026-09-16 optimization: optional typed AND/OR rule mappings now retain field-level provenance in Workbench and project the documented QueryBuilder shape. Site Model field definitions, joins, event context and evidence evaluation remain downstream responsibilities; no filter is executed. [Data and interface contract](../workbench/docs/requirement-interpretation.md).

## Earlier checkpoints
Updated: 2026-09-13. The user clarified one passage may yield multiple Requirements with a `verb`, an `object` (action target, explicitly confirmed), and multiple conditions. The direction and inspected existing models are recorded in [DESIGN.md](DESIGN.md#user-clarification-passage-to-requirement-decomposition). This narrows the design gap but does not provide a frozen semantic schema, connected processor, measured decomposition quality or consumer acceptance. The subsequent recursive parent/child count-range and ontology question is recorded as a discussion proposal in the same design file: typed groups, atomic statements, scoped conditions and distinct recurrence/deadline concepts. Next: validate these distinctions on source-backed examples before freezing a schema.

Updated: 2026-09-11. **Reserved third pane and dormant extension contract implemented; semantic processor not connected.** The shared workspace visibly separates content-review completion from Requirement structuring. Process is disabled with a reason; direct processing requests return unavailable without changing content.

The generic `material-processor/1` boundary records source/material/request identity, confirmed input revision, scope/dependency closure, input hash, future candidate payload/evidence/errors and separate human adoption. Output bindings, distinct empty/partial/failed/unavailable states and preserved unknown payloads are tested. No nested domain fields, final forms, semantic algorithm or System3 runtime environment were invented.

The exact nested structure and processor await the user's specification. This explicit deferral does not block the bounded human workbench delivery and does not represent complete structured Requirement processing. See [contract](../system2/docs/contracts/human-material-workbench.md), [acceptance report](../project-support/reports/human-led-workbench-20260911/acceptance.md) and [integration state](../PROJECT_STATE.md). Site-instance grounding and final compliance decisions remain outside scope.

## Historical interfaces and design evidence

## Input interface | 2026-09-09

System2 now provides `system3-input/1` through the shared workbench, including ordered delivery/suspension/withdrawal events, source versions, evidence and incomplete scopes. Settings can store the future System3 threshold. The interface reports `consumer_connected: false`; no semantic processing or consumer acknowledgment has run.

The input contract is [two-stage review and delivery](../system2/docs/contracts/two-stage-review.md). Existing semantic design and Site Model mapping work remain separate. The next acceptance gate is consumer review of a small set of actually accepted Requirements and invalidation events. Older current-facts statements about absent automatic handoff refer to the prior design checkpoint; semantic runtime and consumer acceptance are still absent.

## Retained earlier checkpoints


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
