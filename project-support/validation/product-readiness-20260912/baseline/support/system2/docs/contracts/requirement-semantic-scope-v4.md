# Requirement semantic scope v4 contract

## Purpose

This contract removes free-form annotator summaries from Gold v3 and Canonical Requirement `scope` / `applies_to`. Even plausible summaries cannot be mechanically checked against PDF evidence and can train the parser to imitate an annotator's wording instead of recovering source Requirements.

The v4 principle is:

> Semantic values may be normalised, but their targets must be established jointly by controlled identities and source-exact anchors.

Historical v2/v3 Gold remains for historical score reproduction only. Migration creates a new revision retaining predecessor path, SHA-256 and revision reason; never overwrite old annotations.

## ScopeRef

Every modality, negation, condition, exception, exemption, threshold and date must include `scope_ref`:

```json
{
  "kind": "source_span",
  "target": "indicator_text",
  "anchors": [
    {
      "source_segment_id": "p17-r5.1.6-indicator",
      "start_char": 0,
      "end_char": 34,
      "text": "Maximum unexplained mortality rate"
    }
  ]
}
```

Allowed `kind` values:

- `source_span`: exact character intervals in one or more source segments;
- `field`: the complete `indicator_text`, `requirement_value`, `applicability` or `normative_text` field;
- `clause`: a stable `clause_id` within the current Requirement;
- `requirement`: the current or explicitly referenced Requirement ID;
- `action`: `client:<marker>` or `auditor:<marker>`;
- `footnote`: an explicitly linked footnote marker.

`target` uses a controlled identity, never a natural-language summary:

```text
indicator_text
requirement_value
applicability
normative_text
clause:<clause_id>
requirement:<requirement_id>
client:<marker>
auditor:<marker>
footnote:<marker>
```

## SourceAnchor

Every anchor must satisfy:

1. `source_segment_id` exists in the current Gold/Canonical Requirement `source_segments`;
2. `0 <= start_char < end_char <= len(source_segment.source_text)`；
3. `source_segment.source_text[start_char:end_char] == text`；
4. Anchors are sorted by page, segment order and start_char;
5. Anchors within one `scope_ref` neither duplicate nor overlap;
6. The parser must not rewrite anchor text to match a target.

A `field` target normally anchors the whole field. `clause`, `requirement`, `action` and `footnote` targets still require at least one anchor proving that the identity comes from the current document rather than model inference.

## Semantic item contract

A v4 semantic item separates three kinds of information:

- Source value: the actual PDF token/phrase;
- Normalised value: for example `shall -> obligation`, `≤ -> lte`, `100% -> 100`;
- Scope relationship: controlled `scope_ref`.

Example:

```json
{
  "raw_text": "100%",
  "operator": "eq",
  "normalized_value": 100,
  "unit": "%",
  "basis": "explicit",
  "source_segment_ids": ["p17-r5.2.3-value"],
  "scope_ref": {
    "kind": "field",
    "target": "indicator_text",
    "anchors": [
      {
        "source_segment_id": "p17-r5.2.3-indicator",
        "start_char": 0,
        "end_char": 67,
        "text": "Percentage of medication events that are prescribed by a veterinarian"
      }
    ]
  }
}
```

`applies_to` / `scope` may remain derived display fields, but cannot independently enter v4 strict scoring. Generate them deterministically from `scope_ref`; do not fill them manually.

## Subjects and applicability

v4 replaces untraceable `normative_subjects` and `applicability` string arrays. Every item includes at least:

```json
{
  "text": "The farm",
  "source_segment_ids": ["p18-r5.2.10-indicator"],
  "anchors": [
    {
      "source_segment_id": "p18-r5.2.10-indicator",
      "start_char": 0,
      "end_char": 8,
      "text": "The farm"
    }
  ]
}
```

When explicit table-field relationships establish a subject or applicability, `basis` may be `inferred_from_source_structure`, but anchors must still point to the relevant field evidence.

## Strict evaluator

v4 strict scoring compares:

1. Source-exact/normalised semantic-value tuples;
2. `scope_ref.kind` and `scope_ref.target`;
3. Each anchor's segment identity, character interval and exact text;
4. Item order and logical structure;
5. Complete source provenance.

The following are no longer strict truth:

- An annotator's summarised `applies_to`;
- Equivalent paraphrases without source locations;
- Unanchored objects supplied from parser domain knowledge;
- Scope inferred only from Requirement IDs or proximity.

## v3 to v4 migration rules

1. Do not modify historical v2/v3 files;
2. New files use `gold_revision = predecessor.gold_revision + 1`;
3. `supersedes` and `supersedes_sha256` identify the direct predecessor;
4. Source, sample window, segments and excluded regions remain unchanged;
5. Change only semantic representation required by the v4 contract;
6. Manually verify source anchors for every former v3 `scope` / `applies_to`. If no unique location exists, record Gold ambiguity rather than guessing;
7. A v4 revision enters a new manifest only after second review;
8. Historical scores use old predictions and Gold. v4 scores require a new manifest and prediction fingerprint.

## Round 7 adjudication examples

- In `5.1.6`, `each of the previous two production cycles` applies to source span `Maximum unexplained mortality rate`;
- In `5.1.6`, `the most recent complete production cycle` applies to `All farms with > 6% total mortality` within the applicability field;
- In `5.2.3`, `100%` applies to the complete `indicator_text` field;
- In `5.2.7`, `per 2 years` applies to the clause containing the `25%` reduction;
- In `5.2.10`, `annually` applies to source span `monitor parasiticide residue levels`;
- In `5.2.11`, `before prescribing medication` applies to source span `certify that a pathogen or disease is present`.

Recompute character intervals from current frozen source segments and perform second review. Do not copy these examples directly into annotations.
