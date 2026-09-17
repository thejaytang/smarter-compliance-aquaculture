# Workbench continuity and handoff

## Outcome
Complete the previously identified gaps without performing Site Model checks or real AI calls.

1. Versioned logical Requirement delivery in the existing full snapshot: splitting, historical revisions, interpretation fields, candidates, references, review attribution and mappings. Validate before preview; retain conflicts and immutable history.
2. Explicit field states: specified, not explicitly stated, unresolved. Absence is documented with a reason; it never means an unconditional predicate.
3. Durable reviewer-isolated drafts, recovery list and navigation without mandatory formal save. Formal save and review remain explicit.
4. Empty-by-default configurable Site Model catalog: labels, types and allowed operators; validate mappings against a pinned catalog revision.
5. Source change impact list from frozen passage/citation versions to affected fields and rules, with conservative handling of legacy records.
6. Semantic regression cases for source wording, absence, exceptions, quantities, time and references.

## Checks and delivery
Use isolated fixtures, backend and browser regression, Windows CI, consistent pre-activation backups, then update the existing GitHub PR. No secrets, runtime databases or source originals are published. Native checks that cannot run remain explicitly unverified.
