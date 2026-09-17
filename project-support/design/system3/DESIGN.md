# System3 | Requirement Semantic Enrichment and Site Model Interface Design

System3 defines structured Requirement outputs that the Site Model team can consume: **what they apply to, when they apply and what must be done**. The `system3` directory is currently a design and interface-validation workspace, with no running implementation. Later interface experiments will determine whether independent deployment is needed.

## Responsibilities and logical architecture

```text
System1 governed sources -> System2 faithful extraction and source evidence
                                      |
                                      v
                      System3 structured output and semantic enrichment
                                      |
                                      v
                         Requirement <-> Site Model interface
                                      ^
                                      |
                       Site Model entities, events and states

Evidence and compliance assessment: collaboration interfaces outside current implementation scope
```

System3 expresses responsible actors, constrained object types, actions, conditions and temporal relationships at the Requirement semantic level. The Site Model team maps these concepts to actual site entities, roles, events and states. Describing a trigger does not establish that it occurred at a site.

## Candidate inputs and outputs

Inputs include System2 requirements, source context, stable identifiers, evidence locations, verification status and explicitly identified human classifications or additions. Reuse existing System2 fields before identifying gaps; avoid independently reinterpreting the same data.

| Output | Purpose |
| --- | --- |
| `requirement_id`, original text, `source/provenance` | Stable references traceable to sources and versions |
| `classification` | A taxonomy agreed with the collaborating team |
| `applies_to` | Responsible roles and object types, without binding actual site instances |
| `when_it_applies` | Conditions, triggering events and temporal constraints |
| `required_action` | Required or prohibited actions, preserving modality and negation |
| `information_needed_to_check` | Optional discussion field; confirm ownership with Site Model/Evidence collaborators |

This is a candidate semantic contract, not a frozen API/schema. Label missing values, ambiguity, inference and human decisions explicitly. Store source text and evidence locations separately from enrichment. See the [design basis](docs/design-basis.md) for sources and open questions.

## User clarification: passage-to-Requirement decomposition

On 2026-09-13 the user clarified that one passage may contain several Requirements, each with a `verb`, an `object` (the target of the action), and potentially several `condition` entries. The user explicitly resolved the earlier word `objection` to `object`, not `objective`. Nested dictionaries and lists describe storage, not the business meaning or extraction acceptance criteria. This direction does not itself connect the third-pane processor or freeze a replacement schema.

The candidate review model must keep each derived Requirement linked to its exact source passage and confirmed source-content revision. An unconditional Requirement may have no conditions; do not invent one to fill a field. Condition membership and scope must remain inspectable, including conditions shared by several Requirements and conditions applying only to one action. AND/OR relationships, modality, negation and exceptions must not be silently flattened or inferred when the source is ambiguous. Reviewers need passage comparison and editable Requirement fields rather than raw nested JSON.

Current-code inspection found reusable `Requirement.conditions` lists, `RequirementScopedText.scope_ref`, source-exact anchors and clause `joins_next` in System2's `models/requirement.py`. The separate `domains/regulatory` projection has a singular `condition` field and a simple verb/remainder split; it is insufficient evidence of the requested multi-Requirement, multi-condition decomposition. Reuse and assess the richer model before introducing parallel fields. Original-document hierarchy, Requirement identification, and internal semantic decomposition require separate acceptance evidence.

Field mapping after the user's explicit `object` confirmation:

| Business concept | Existing representation | Adaptation / acceptance gap |
| --- | --- | --- |
| One source passage to several Requirements | Separate `Requirement.requirement_id` values and reusable `source_segments` / exact character anchors | Preserve shared passage identity and confirmed content revision; measure missed, duplicated and incorrectly split Requirements against the complete source passage |
| `verb` | `client_actions` / `auditor_actions` preserve action text; the regulatory projection has an action extraction path | The richer action model has no explicit verb/object pair. Action text alone is not a verified decomposition |
| `object` | Regulatory projection has `object`; the richer model has normative subjects and applicability | A subject is the responsible actor, not the action target. Do not repurpose `normative_subjects` or take all text after a verb as a reliable object |
| Zero to several conditions | `conditions: list[RequirementScopedText]` with optional `scope_ref` and exact anchors | Verify each condition's membership and affected Requirement/action; preserve shared conditions, alternatives and unresolved scope. Clause `joins_next` is not by itself a complete condition-logic model |
| Prohibition, obligation, exceptions and time limits | Existing modalities, negations, exceptions, exemptions and dates | Preserve these alongside the verb/object view; do not turn a prohibition into a positive action or drop a qualifier during splitting |

This is a source-code mapping and candidate review design, not a schema migration. An illustrative review case is “If an abnormal discharge occurs, the operator must stop the discharge and notify the authority within 24 hours”: two candidate Requirements share the event condition; the time limit belongs to notification; the operator is the actor; discharge and authority are action targets. This invented example is not business Gold and contributes no quality score. A future source-backed evaluation must test the split, fields, qualifier scope and evidence together before accepting the semantic adapter.

## Discussion proposal: recursive groups and ontology preparation

On 2026-09-13 the user proposed recursive parent/child Requirement groups with a range specifying how many child Requirements must be fulfilled, and asked how multiple verbs, conditions and recurring periods should be decomposed. This is an active design discussion, not an approved replacement schema or permission to connect semantic processing.

Recommended separation: source-document hierarchy; a Requirement expression containing atomic normative statements or recursive logical groups; and later site-specific evidence/assessment instances. Group membership is not `subClassOf`. A group should explicitly express ALL, ANY, a bounded count, or a sequence; count constraints apply to distinct immediate children in a named scope/period, not all descendant leaves. A minimum count alone does not imply an upper prohibition. Selection counts, satisfied-child counts, action occurrence counts and quantified objects are different quantities. Unknown/inapplicable children require an explicit evaluation policy; no evidence is not automatically failure.

An atomic statement preserves actor, original modality/negation, an action with paired verb/object and role-qualified participants (for example recipient), or a required state/property constraint. Applicability, trigger, prerequisite, exception, threshold/value/unit and temporal constraints retain distinct roles and exact source spans. Shared and action-specific qualifiers bind by explicit references. Multiple verbs are split only where duties can be independently satisfied or violated; preserve joint/sequence semantics and ambiguous scope instead of pairing every verb with every object. Conditions use nested AND/OR/NOT expressions, not an implicitly conjunctive flat list. Recurrence, per-period count, deadline, duration and retention are separate temporal concepts. “Every year” leaves calendar/rolling period, anchor and due date unresolved unless the source specifies them.

For eventual ontology mapping, give each source span, rule, group, action, participant, condition and temporal expression a stable identity and typed relationships; nested JSON can remain an interchange/view representation. Preserve a reusable rule separately from later site/period-specific assessment evidence. OWL describes concepts and relations under an open-world assumption, not completeness validation or automatic compliance. SHACL validates recorded graph constraints; fulfilling child rules needs separately defined evaluation semantics. ODRL logical constraints offer useful AND/OR/XONE/sequence reference patterns but are not selected here as the complete aquaculture ontology. References: [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/), [SHACL](https://www.w3.org/TR/shacl/), [ODRL model](https://www.w3.org/TR/odrl-model/).

Next design validation: use source-backed examples covering joint verbs, alternative and nested groups, threshold states, shared exceptions, annual recurrence and deadlines. A reviewer must be able to reconstruct the original logic and identify unresolved scope before any formal schema migration. Third-pane processing, Site Model integration and final compliance assessment remain disconnected.

## Current boundaries

- Actual site modelling, sensor/log collection and final compliance decisions are outside this scope.
- Low historical deviation counts cannot exclude legal obligations; they may inform human-enrichment priorities only.
- Sheet separation is a collaboration view. Requirement identity and the field model remain unified.
- Requirement-to-Evidence relationships may be many-to-many; their mapping contract needs joint validation.
- System2 already produces some semantic/domain fields. This design does not move or delete existing code.

## Usage and next step

Read [current state](PROJECT_STATE.md) and the [design basis](docs/design-basis.md). Select 5 to 10 source-backed requirements, populate candidate fields and ask Site Model consumers whether they support mapping. There is currently no launch command or separate environment.

Agent entry: [AGENTS.md](../AGENTS.md). Shared boundaries: [system overview](../README.md).
