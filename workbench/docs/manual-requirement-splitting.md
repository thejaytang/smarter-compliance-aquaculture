# Manual requirement splitting

## Latest interaction revision, 2026-09-16

This section supersedes earlier autosave and second-pane annotation descriptions below. Unsaved splitting and interpretation changes stay in page memory only. Splitting steps are validated as previews; **Save splitting** or **Save & collapse** commits their final version. **Save interpretation** commits fourth-pane fields. Leaving warns about unsaved work. Earlier saved histories and legacy recovery records are retained, but new edits are not automatically journalled in the browser or database. Semantic colours render over the exact source at the top of each third-pane entry, including when collapsed. Conditions can be decomposed recursively, and one entry may reference multiple source blocks. Second-pane Current text and Changes remain separate from this coloured preview.


## Use the workbench

Open a material in personal work and save any content edits. Beside a text block, choose **To requirements**. The saved block enters a source-bound card in the Requirements pane. Cards follow source-block order; editing a card does not move it to the bottom. The former source selector, saved-passage selector and three phase pages are removed.

Work directly inside each requirement card. Place the cursor at a statement boundary and choose **Split at cursor** to create adjacent units. Select exact wording in the original text, then click its `Subject`, `Modal Verb`, `Main Verb` or `Object` field below. The field fills in place. Preserve grammatical subjects, passive forms and negation; a main-field value is terminal and is not automatically subdivided.

Expand **Add a condition, exception or subrequirement** when needed. Selected wording becomes a linked source-span unit. A plain condition only needs its original text. Use **Relationships between requirements** for outer grouping and quantity controls; linking an outer unit moves it into the chosen relationship rather than inferring scope from sentence order.

Choose **Finish & collapse** when a requirement is ready. It stays in its original position and can be expanded again. Once all units are finished, **Complete & collapse** records completion of the splitting pass. **Resume editing** reopens completed work in the same card. Disclosure itself is presentation state, not a save or review decision. No separate phase-navigation action is needed before field assignment or relation extraction; legacy phase values remain readable in saved history.

The material header leads with the document title. The close button immediately after **Save** returns to the material list while retaining the open draft; **Return to open material** resumes it. Previous/Next material controls are removed. In-flight or uncertain requirement saves block closing until resolved.

Every applied operation is a separate server save. Saving failures retain the error and, for uncertain network outcomes, the same request ID for retry. Step history supports restore into a new revision without deleting earlier revisions. Save/reopen, material review and splitting completion remain distinct.

## Quantity semantics

A combination is `[quantity, child, ...]`. Each child is a unit ID or a nested combination. A nested combination counts as one direct child.

- Scalar `k`: exactly k direct children.
- `[min,max]`: an inclusive permitted range.
- `[3,A,B,C]`: all three.
- `[[1,3],A,B,C]`: one, two or three.
- `[[1,2],A,[3,B,C,D]]`: A or the complete B/C/D group, with both allowed.

Controls validate integers, bounds and duplicate references. Structural changes reset affected group counts to all remaining direct children; review and set the intended count after restructuring. They never infer AND/OR from the wording.

## Fixed unit format

Each unit has `id`, `text`, `Subject`, `Modal Verb`, `Main Verb`, `Object`, `conditions`, `exceptions`, `subrequirement`. Missing values serialize as `null`. Conditions and other relation values are recursive combinations when present. Human-facing R/C labels remain stable through saved steps; globally unique IDs own identity.

Source metadata, text offsets, original references, actors, progress and step history belong to the session envelope and relational tables, not additional fields in the unit template. Source text and scalar fields are constructed from server-validated original spans. Browser UTF-16 selections are converted to Unicode code-point offsets before submission.

## Link requirements under an extracted chapter

Use **Link an existing requirement**, search by original wording, extracted heading/chapter text or ID, then select the actual requirement. The relationship contains the requirement ID, never a chapter object or a filename. The linked source evidence is retained and **View linked original** exposes the corresponding document.

Search currently covers saved manual units belonging to the selected reviewer on this installation. It does not invent IDs for chapters that have not yet been split, expose another reviewer's private work, or automatically convert legacy requirement schemas.

## Storage and protection

Workbench's `runtime/workbench.sqlite` owns `requirement_sessions`, `requirement_steps`, `requirement_units` and `requirement_requests`. Units have relational session/material/actor/source bindings and a current searchable projection. The material store, originals and existing content review records remain separate.

Source passage or original-reference changes make an earlier session read-only; start a new session from the current saved passage. Version checks reject concurrent stale writes. Request replay is idempotent. Circular links and operations that would remove a referenced ID are rejected. Restoring an earlier step is subject to the same integrity checks.

**Current storage boundary:** personal splitting sessions are local. Existing collaboration/full-review ZIPs do not yet include these new tables. Preserve this database with the owning material/original stores for local recovery. Do not describe those ZIPs as a backup of requirement splitting work.

Automatic requirement extraction, ontology enrichment, machine learning and compliance evaluation remain disconnected. No external model or dependency was added. Native Windows verification of this new interaction remains pending.

## Verification

[Initial implementation evidence](../../project-support/requirement-splitting-20260915/RESULTS.md) records the storage and integrity contract. [Continuous editor evidence](../../project-support/requirement-inline-20260915/RESULTS.md) records the revised interaction and local validation.

## Relational relationship projection

`requirement_relationships` indexes active conditions, exceptions and subrequirements by session, owner, target and nested group path. `quantities` retains the ordered ancestor counts along that path: a scalar remains exact `k`, and an array remains inclusive `[min,max]`. It is not reduced to AND/OR. Deferred foreign keys bind both ends to active units, allowing an atomic splitting update to rebuild rows while rejecting dangling links at commit. `requirement_relationship_versions` prevents repeated legacy migration. Immutable `requirement_steps` remains the historical authority; saved interpretation origins reference those fixed revisions even after active units change.
