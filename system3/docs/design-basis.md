# System3 Design Basis and Candidate Interface

Source: [Aquaculture compliance project discussion](https://chatgpt.com/share/6a9e6781-31d4-83eb-a0e1-942c7c79608a)

Recorded/read: 2026-09-07. Source ID: `6a9e6781-31d4-83eb-a0e1-942c7c79608a`. This user-selected design discussion is not a legal source, formal meeting record or signed interface contract. This document is an attributed reading summary, not a complete conversation archive. Images, original AquaInsight data and classification tables mentioned in the discussion were not obtained in that round.

## Discussion development and adopted principles

1. The user emphasised Source Management before Extraction.
2. The supplied meeting notes covered applicability objects and timing, required actions, the Requirement acquisition process and its evolution, sheet-based views, information/evidence needed to apply or check requirements, and shared evidence across requirements.
3. Earlier assistant suggestions named an independent System3 semantic service and even discussed System4. Later corrections superseded those suggestions; they are not final architecture decisions.
4. The user clarified that the requesting collaborators were the Site Model team. The discussion converged on defining structured Requirement outputs they can consume, then validating a small sample. The user agreed to that direction.
5. Retain the user-requested `system3` directory for enrichment and interface design. Its existence does not establish the need for a separate service; deployment remains to be validated.

## Mapping feedback to work

| Feedback | Current interpretation | Boundary to confirm |
| --- | --- | --- |
| What it applies to | Object types and responsible roles | Site Model owns actual entity IDs and grounding |
| When it applies | Conditions, triggering events and temporal relationships | Site models/assessment determine whether actual events occurred |
| What must be done | Actions, modality and prohibitions | Inference must not rewrite source obligations |
| Acquisition process and evolution | Cross-system workflow and historical basis | Do not force process history into Requirement fields |
| Separate sheets | Classification views and human collaboration | Taxonomy and sheet dimensions remain to be agreed |
| Information needed for application/checking | Candidate `information_needed_to_check` interface | Requirement, Site Model and Evidence teams must agree ownership |
| Evidence shared by several requirements | Support many-to-many relationships | Sharing evidence does not automatically satisfy every requirement |

## Minimal candidate contract

Stable Requirement identity, original text and source locations form the foundation. Add or map classification, applies_to (actor/object type), when_it_applies (condition/trigger/temporal constraint) and required_action. Information needed to check is an optional discussion field.

These are semantic groups, not final JSON keys. Real examples may justify frequency, threshold, exception or location-scope fields. Distinguish source silence, extraction gaps, semantic uncertainty and incomplete human review; do not collapse missing values into unconditional applicability.

System2 already has related semantic outputs; see [Canonical Requirement construction](../../system2/src/pdf_extraction/domains/requirements/canonical.py). Map existing fields to consumer needs and identify gaps before maintaining another equivalent interpretation.

## Background for human priorities

The shared discussion relayed colleagues' plans to prioritise work using historical AquaInsight deviations/incidents and extended classification. This is a report from the conversation, not a database verification. Whether incidents link to regulations, sections/paragraphs or atomic requirements remains unknown; do not assume Requirement-level frequency exists.

This lead can help choose 5 to 10 useful interface examples. Do not invent counts or rankings when original data is unavailable. Deviation frequency is neither a complete risk measure nor a basis for excluding other obligations.

## Proposed acceptance method

For real examples, show source text/evidence, upstream fields, enriched fields and Site Model consumer needs. Record field evidence and open questions. Freeze a minimal contract only after consumers confirm that objects, roles, conditions and actions can be mapped. That validation is not yet available.
