# Provisional B requirement subdivision

Status: **PROVISIONAL**. The [aligned target](../../../docs/design/requirement-workstream-target.md) and [decision register](../../../docs/design/decision-boundaries.md) retain authority over collaborator-dependent granularity, delivery and counting. This mechanism is independent of A structural split/merge and introduces no System3 ontology fields.

## Decision and evidence

The normal workbench submits `subdivide_requirement` through its existing guarded decision endpoint. A content and dependency gates must pass; unresolved relationship issues, non-current sources, evidence-only units and superseded units cannot bypass those gates. Tables with existing original row items are shared context and cannot be subdivided into another counted copy of those rows.

The operation keeps the complete effective A item, original facts, source version, original number, locations, related content and footnotes. Each B subitem binds an exact nonempty Unicode-code-point interval `[start, end)` in one accepted field. The submitted quotation must equal that interval. Intervals in the same field may not overlap. Binding means an exact accepted-text span and the parent's source region; it does not assert a new independently measured PDF box for each subitem.

Generated labels such as `Subitem 1` are separate from original numbering. A reviewer may supply an original subitem number only when it is the complete prefix of the selected original quotation; its text interval is retained. Otherwise original subitem numbering stays empty and the original parent number remains linked. Original numbering outside this supported prefix form remains in the complete parent context and requires a future evidence-bound numbering extension, not an invented identifier.

All unassigned text from the supported text/context fields is shown. If non-whitespace text remains, submission requires an explanation of why it contains no additional requirement, plus complete-parent review and an evidence note. The software cannot establish the semantic correctness of that explanation. Independent B precision/recall and subdivision evaluation are still required.

## Reversible policy and history

`requirement-subdivision/1` is stored in the owning workflow database, with status `PROVISIONAL`, peer confirmation `pending` and an incrementing per-parent subdivision revision. Each named decision chooses `count_basis`:

| Choice | Parent count | Subitem count | Retained content |
| --- | --- | --- | --- |
| `subitems` | 0 | 1 per subitem | Full parent and linked subitems |
| `parent` | 1 | 0 per subitem | Full parent and linked subitems |

There is no option to count both. The default UI choice of `subitems` is temporary and is not collaborator approval. Changing the choice or spans is a new guarded B decision. `clear_subdivision` requires an explicit classification of the complete parent and a reason. Removing and later restoring subitems never resets the subdivision revision or reuses retired generated IDs. Prior parent context, spans, policy and reviewer decisions remain in history. Ordinary `classify` cannot silently discard an existing subdivision.

The current two-to-100-subitem submission bound is an engineering request-size limit, not a recommended semantic granularity or a quality threshold. Each child presently binds one contiguous field interval; shared qualifications remain in full parent context. Noncontiguous evidence composition and alternative proposed parent-delivery shapes are not implemented by this schema.

## Invalidations and drafts

A source/version, effective A content, location or shared-context change makes the old subdivision stale. Reaccepting A does not silently revive the old B decision: the old subdivision remains visible, and B must be rechecked or explicitly removed. Existing source eligibility and confidence-policy gates continue to apply. Request replay is idempotent; stale unit/dependency guards are rejected.

B drafts leave previously accepted A content intact but suspend B completion and delivery. A drafts suspend A completion, including earlier human acceptance. Any remaining draft prevents its affected stage from appearing completed. Drafts and failures are not review-history completions. A submitted decision clears only that reviewer's own draft.

## Delivery and Excel

The database keeps one parent delivery envelope per A unit with nested subitems, avoiding separate A units or partial-load orphan deliveries. `feed.current_requirements` projects only counted rows; `feed.requirement_parents` retains full subdivided parents separately. Each envelope explicitly identifies the provisional policy and each row's `requirement_count`. Parent-envelope `replace`, `suspend` and `withdraw` events govern all nested subitems: an incremental consumer must retire that parent's previous child set before applying its replacement. System3 remains unconnected; this is a future interface boundary, not semantic enrichment.

The [Excel register](requirement-workbook.md) retains the full parent row and adds linked B rows on the same source sheet. `Available` identifies counted deliveries. A non-counted parent says `Parent context; subitems available`; non-counted children in parent-count mode say `Included in parent; not counted`. `Counted Requirements` is additive, with zero on continuation rows. Original number, generated label, parent ID, temporary policy and exact quotation span are separate columns. Source index and workbench counts use the same counting rule.

All exports remain one-way, coherent, background-generated snapshots with existing version, retry and cached-output protections. Excel is never a B decision input.
