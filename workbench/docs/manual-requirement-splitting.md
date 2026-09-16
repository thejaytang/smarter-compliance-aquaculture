# Manual requirement splitting

## Entry identity and selection toolbar (current)

One source entry displays one Rx in both the third and fourth panes. Local historical child units retain their IDs and saved interpretations but appear as Groups within that entry, not additional Requirements. Only another complete entry is offered by the Requirement reference picker. Historical multi-clause entries retain access to their saved clause interpretations under the single entry heading.

The entry header shows Locate then Remove; Remove asks for explicit confirmation and keeps recoverable history. No completion badge is shown there. Only the arrow beside Rx expands or collapses the entry. Clicking coloured original wording never toggles it. One entry is open at a time. Expanded original text is selectable but read-only; selection opens a floating toolbar beside the pointer (or keyboard selection) with two sections: **Group / Degroup** and **Subject / Modal Verb / Main Verb / Object / conditions / ❌**. Collapsed source text has no annotation toolbar. Escape or clicking elsewhere dismisses the toolbar. The complete source uses a full-width row in narrow panes.

Group retains existing whole source marks inside its selected range. A boundary through an existing mark must be adjusted or cleared first. ❌ clears field marks only in the selected range, including matching local child-unit marks, preserving original text and explicit Groups. Degroup preserves fields and refuses to discard existing alternative quantities or NOT implicitly. Plain single fields have no QC; explicit combinations retain exact/range QC. Explicit NOT controls and operations are unavailable, including Conditions. Select the complete negative wording (for example, “not installed in the North of Norway”) as an ordinary Condition; no extra operator is inferred. Historical stored NOT remains visibly read-only and retains its recorded projection; no migration rewrites saved history.

**Exception remains an independent relationship.** Exception has a full clause structure, may have its own Scope/Conditions/Demand and can reference a complete Requirement. It is not automatically negated or merged into the main Scope. Use the separate Reference a Requirement controls and choose Exception or Subrequirement. The contextual field toolbar excludes both relationship types. A source-defined exception may be incomplete; do not invent a missing demand or deadline. Prior saved records remain readable and unmodified.

These rules supersede conflicting descriptions below, including the earlier conversion of every Exception into a negated Condition. Editing a completed entry from its original text reopens an unsaved preview; explicit Save is still required.

## Unified source-bound groups (current)

Select wording in the original text inside an open Requirement, then choose **Subject**, **Modal Verb**, **Main Verb**, **Object**, **conditions** or **Group** from the contextual toolbar. The original is selectable but read-only. Coloured source marks remain above each entry when its editor is collapsed. **subrequirement** opens the existing-Requirement picker; references retain real IDs and display Rx labels.

Explicit Groups indent their children one level and show connecting guides; siblings remain aligned. Source colours preserve inner grammatical fields for parent/child references and duplicate same-field marks; unrelated conflicting field annotations still show overlap.

A **Group** created in a clause holds a complete subject/action/object association. Put shared conditions on its enclosing clause. For example, an outer clause can contain one shared condition and two child clauses for “Alice checks A” and “Bob checks B”. The combination of those child clauses has QC; the mixed grammatical fields within a clause do not.

Every field supports multiple source fragments and nested same-role groups. **Decompose** replaces a fragment with an empty group over the same exact source span; select its wording again to fill the children. A condition subgroup offers only Conditions and Group, and a Subject subgroup offers only Subject and Group. Select sibling checkboxes and choose **Group selected** to wrap them without losing their IDs. **Ungroup** is permitted only between unnegated All groups; other flattening would change meaning.

QC counts direct children, with nested groups counting as one child:

- **All**: exact N; **Any**: [1,N]; **Only**: exact 1.
- **Not All**: [1,N-1], deliberately excluding zero. It is not the Boolean NOT operation.
- **MIN–MAX** is a selectable option alongside the shortcuts. Bounds are disabled until it is selected, and accept inclusive integer values within 0…N. Choosing a shortcut disables the bounds again. Selecting the mode alone does not save anything. The separate QC heading is omitted; the current count/range stays visible.
- Explicit Boolean NOT authoring is disabled in this version. Negation stays in the selected source wording. Existing historical NOT annotations remain read-only.

Adding/removing/wrapping members leaves multi-item QC unresolved until the operator chooses its meaning. Empty groups and unresolved QC prevent Finish. Legacy exceptions appear as independent exception clause/reference groups without automatic negation; opening a record does not rewrite its history.

Unsaved edits remain in page memory. Only explicit Save creates a saved revision. The `requirement-structure/1` tree is stored alongside the unchanged legacy units, and its nodes are projected to relational source/owner/parent/reference links. Interpretations, source colouring and delivery consume the tree once it exists. JSON inspection exposes it. Older saved records remain readable and restorable.

The following sections describe the earlier editor and remain historical context where they conflict with the current workflow above.

## Inline conditions and quantity shortcuts

Condition children are edited within their owning Conditions field. **Decompose** opens the child directly below its source header and before the next sibling; recursive children use the same layout. Attached conditions are not duplicated as separate top-level cards. Detached condition units remain accessible. Editing a child keeps its previously finished ancestors open.

Each group has quantity controls above its direct children:

- **All (N)** requires all N direct items and stores scalar N.
- **Any (OR)** requires at least one, permits several, and stores [1,N].
- **Exactly one** stores scalar 1; it is distinct from inclusive OR.
- **Range** exposes minimum and maximum, applied explicitly as [min,max].

A nested group counts as one direct item; its own control governs its children. Shortcuts count the current group, not all descendant leaves. Existing saved scalar/range values are retained on opening. As before, adding an item to an all-items group updates its scalar count, while explicit non-all bounds are preserved and may become a custom range for the larger group. Choose a shortcut again to apply it to the new membership.


## Current relationship editor

The [simplified workflow contract](requirement-interpretation.md#simplified-relationship-and-interpretation-workflow-2026-09-16) owns the current coloured relationship fields, condition-only decomposition, visible counts, whole-Requirement references and synchronized Rx selection. It supersedes conflicting descriptions below.

## Latest interaction revision, 2026-09-16

This section supersedes earlier autosave and second-pane annotation descriptions below. Unsaved splitting and interpretation changes stay in page memory only. Splitting steps are validated as previews; **Save splitting** or **Save & collapse** commits their final version. **Save interpretation** commits fourth-pane fields. Leaving warns about unsaved work. Earlier saved histories and legacy recovery records are retained, but new edits are not automatically journalled in the browser or database. Semantic colours render over the exact source at the top of each third-pane entry, including when collapsed. Conditions can be decomposed recursively, and one entry may reference multiple source blocks. Second-pane Current text and Changes remain separate from this coloured preview.


## Use the workbench

Open a material in personal work and save any content edits. Beside a text block, choose **To requirements**. The saved block enters a source-bound card in the Requirements pane. Cards follow source-block order; editing a card does not move it to the bottom. The former source selector, saved-passage selector and three phase pages are removed.

Work directly inside each requirement card. Select exact wording in the original text, then click its `Subject`, `Modal Verb`, `Main Verb` or `Object` field below. The field fills in place. Preserve grammatical subjects, passive forms and negation; a main-field value is terminal and is not automatically subdivided.

The **conditions**, **exceptions** and **subrequirement** buttons are visible directly alongside the field controls. Selected wording becomes a linked source-span unit. A plain condition only needs its original text. To continue inside an existing child, choose **Decompose** beside that child: its own source text opens for the same field and recursive relationship operations, even if the entry was previously completed. This is an unsaved edit until explicit Save. Use **Relationships between requirements** for outer grouping and quantity controls; linking an outer unit moves it into the chosen relationship rather than inferring scope from sentence order.

Choose **Finish & collapse** when a requirement is ready. It stays in its original position and can be expanded again. Once all units are finished, **Save & collapse** saves completion of the splitting pass. **Resume editing** reopens completed work in the same card. Disclosure itself is presentation state, not a save or review decision. No separate phase-navigation action is needed before field assignment or relation extraction; legacy phase values remain readable in saved history.

The material header leads with the document title. The close button immediately after **Save** returns to the material list after unsaved work is saved or explicitly discarded. Previous/Next material controls are removed. In-flight or uncertain requirement saves block closing until resolved.

Each operation validates an in-memory preview; only explicit Save adds a saved revision. Saving failures retain the error and, for uncertain network outcomes, the same request ID for retry. Step history supports restore into a new revision without deleting earlier revisions. Save/reopen, material review and splitting completion remain distinct.

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

**Locate text** lives at the right of each top coloured source header and works while the entry is collapsed. It locates that entry in both source panes; multi-passage entries offer their linked passages. Selecting a saved Requirement also loads its fourth-pane interpretation without a separate Interpret requirement button.
