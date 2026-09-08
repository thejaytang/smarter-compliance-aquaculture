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

## Current boundaries

- Actual site modelling, sensor/log collection and final compliance decisions are outside this scope.
- Low historical deviation counts cannot exclude legal obligations; they may inform human-enrichment priorities only.
- Sheet separation is a collaboration view. Requirement identity and the field model remain unified.
- Requirement-to-Evidence relationships may be many-to-many; their mapping contract needs joint validation.
- System2 already produces some semantic/domain fields. This design does not move or delete existing code.

## Usage and next step

Read [current state](PROJECT_STATE.md) and the [design basis](docs/design-basis.md). Select 5 to 10 source-backed requirements, populate candidate fields and ask Site Model consumers whether they support mapping. There is currently no launch command or separate environment.

Agent entry: [AGENTS.md](../AGENTS.md). Shared boundaries: [system overview](../README.md).
