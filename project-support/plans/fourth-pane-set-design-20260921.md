# Fourth-pane set definitions and check-design plan

Status: implemented locally on 2026-09-21 after the user explicitly authorized implementation. The final flow is mapped third-pane wording → editable Logic → generated A/B/C definitions and checking relationship. See [implementation validation](../validation/fourth-pane-sets-20260921/RESULTS.md). No Goal, publication or external model run was started.

## 1. Verified baseline

- Fetched `origin/main` on 2026-09-21. Its tip is `b221b162b767c6f93a46ea9886cff472b52a695e`; the local `main` reference already matched it. The active `developing-only-jay` checkout was missing four product commits.
- Merged those commits into the active development branch as `badc2ce05ba4dd6c2a4fa734bba9478bbbcfbdd6`, retaining development files and pre-existing uncommitted work. No conflicts, database migration, dependency rebuild or push.
- Updates cover training resources, shorter Windows extraction paths, source backup directory creation and preservation of superseded candidate history. They do not change the fourth-pane implementation inspected below.
- Restarted the same local workspace at `http://127.0.0.1:62742/`. Browser readback shows PE001 personal revision 12, Saved, and R1-R3 with their existing structure. The four business stores and private setting files remain byte-identical across synchronization and restart.
- Validation: 32 Workbench tests, 12 System1 tests and 33 System2 tests passed; deployment environment, development-index boundary and stopped-workspace integrity checks passed. Native Windows behavior and real model calls were not tested.
- [Synchronization evidence](../validation/main-sync-20260921/sync-result.json) and its adjacent test logs record this operation. Local recovery copies remain under `workbench/runtime/backups/main-sync-20260921/`.

## 2. Decisions and completion target

Keep the existing column order: Original document, Extracted content, Requirements, Interpretation & check design.

The third pane retains the original text, grammatical/structural annotations, Groups and relationships. The fourth pane interprets the complete relevant saved context into definitions of objects and checks. `Subject` is evidence for interpretation; it is not a fixed mapping to Scope. The same distinction applies to source `conditions`: measurement depth and recurrence can constrain Demand instead of applicability.

The fourth pane must produce:

| Output | Meaning |
| --- | --- |
| Scope / Set A | A definition of the objects to which the Requirement refers, including relevant concept and relationship constraints. |
| Condition / Set B | A definition of the applicable objects selected from A in an explicit assessment context. |
| Demand / Set C | A definition of objects with sufficient evidence of satisfying the required action or state in that same context. |
| Checking Logic | A readable and structured composition of the definitions: every object in B must belong to C. |

For a declared object domain U and assessment context k:

```text
A(k) = {x in U | Scope(x, k)}
B(k) = {x in A(k) | Applicability(x, k)}
C(k) = {x in U | EvidenceSatisfiesDemand(x, k)}
Required relationship: B(k) subset_of C(k)
```

These are definitions until a consumer supplies site data. A, B and C refer to the same object identity/domain; evidence documents and weather events are related records, not replacement element types. Context carries the relevant event or assessment period so that evidence for a different event cannot satisfy the current obligation.

Only a reviewed unconditional interpretation makes B equal to A. An unresolved or empty Condition must not silently mean unconditional, false, or an empty set. Missing evidence is not proof of failure; an empty result from incomplete data is not proof of satisfaction.

Completion means a reviewer can edit and save context-supported A/B/C definitions, inspect their combined logic, reopen the exact saved result, and hand off versioned structured rules without losing source bindings or unsupported semantics. Running production site queries or issuing compliance verdicts is outside this adjustment.

## 3. Pre-implementation findings and reusable pieces

| Verified code path | Finding | Planned treatment |
| --- | --- | --- |
| [interpretations.js](../../workbench/frontend/components/interpretations.js), `sourceSections`, `editorMarkup`, `save` | Source Subject becomes Scope; source conditions become Condition. The preview overlays these values, and `save` overwrites the three formal fields with the source projection. | Keep source projection as evidence display. Stop using it to determine or overwrite formal interpretations in both preview and save. |
| [interpretations.py](../../workbench/backend/system3/interpretations.py), `context`, `validate_fields`, `save`, `_generate` | Already has six interpretation fields, full saved-material context, related-material support, citations, gaps, version guards and candidate adoption. The model instruction already warns against Subject = Scope, but the visible workflow only asks for the three information/verification fields. | Reuse these capabilities; expose independent S/C/D editing and context-supported candidates. Preserve explicit save and adoption. Do not solve the issue by prompt changes alone. |
| [check-design.js](../../workbench/frontend/components/check-design.js) and [check_design.py](../../workbench/backend/system3/check_design.py) | Existing native rule editor and validated three-group handoff. Rules currently require simple `table.column` comparisons; output comprises independent filters. | Evolve this editor and format into one coherent set design. Do not replace the whole frontend or introduce another parallel rule store. |
| [site_catalog.py](../../workbench/backend/system3/site_catalog.py) | Versioned field/type/operator catalog; no relation paths, event correlation or temporal-count capability contract. | Reuse and extend only the mappings required by the agreed examples. Preserve unresolved concept/mapping needs explicitly. |
| [interpretation_lineage.py](../../workbench/backend/system3/interpretation_lineage.py), [interpretation_continuity.py](../../workbench/backend/system3/interpretation_continuity.py), [requirement_delivery.py](../../workbench/backend/system3/requirement_delivery.py) | Rule indexes, stale-source checks, history and imports assume the current design schema and deterministic logic generator. | Update together with a versioned design change; never silently reinterpret older saved records. |

Local business inspection found no saved fourth-pane interpretations and an empty Site Model catalog in this workspace. Compatibility is still required for colleague work and previously exported packages.

## 4. Recommended product and data design

### 4.1 Fourth-pane review flow

Retain the selected Requirement at the top. Show four primary sections in order:

1. **Scope / Set A**: interpreted object type, object selection definition, and the fields/relationships needed to find those objects.
2. **Condition / Set B**: applicability rules explicitly evaluated within A, including relevant event and location bindings and source-supported exceptions.
3. **Demand / Set C**: required action/state and the evidence predicates needed to determine membership, including measurement constraints, recurrence and alternatives where relevant.
4. **Checking Logic**: a generated readable chain and set relationship, with an expandable structured handoff preview and precise unresolved items.

Show the mapped third-pane wording first in each section, followed by editable Logic. Keep additional quotations and context links under the section's evidence control. Do not label a mechanical Subject quotation as the final Scope. Preserve the source annotations even when interpretation classifies a phrase differently. Allow a reviewer to add relevant saved material through the existing context mechanism.

Reuse existing save, history and review actions. Saved, reviewed and ready for downstream mapping remain distinguishable. An incomplete draft can be saved safely; it cannot be advertised as ready for execution. Unsupported queries remain `Not connected` or explicitly unmapped. Do not show fabricated object counts or compliance results.

### 4.2 One authority for each kind of information

- Original evidence remains in its existing immutable source/material/Requirement bindings.
- Reuse the six interpretation fields for editable explanations, evidence quotations, rationale and information gaps.
- Make the structured set design the authority for machine logic. Generate the rule-readable view, A/B/C composition and QueryBuilder projection from it; do not maintain independently editable copies of the same formula.
- Editing an explanation, source dependency or catalog mapping invalidates the relevant reviewed/mapped status until reconciled. Do not pretend free text and an old rule tree remain equivalent after an edit.
- Recommend a versioned successor to `requirement-check-design/1`, retaining stable rule/group IDs and interpretation-field references. Add the minimum explicit object-domain, assessment-context and set-composition information. Freeze exact keys after the example contract check in phase 1.

The expression vocabulary must preserve the agreed use cases: nested conjunction/disjunction, explicit negation and exception ownership, relationships such as `partOf`, event-linked existence and period-specific occurrence counts. A plain string containing a relationship is not an implemented relationship query. Missing mapping or unsupported operations remain visible in the saved design and block a complete executable handoff; no flattening or silently dropped clauses.

### 4.3 QueryBuilder and SQLAlchemy boundary

The [jQuery QueryBuilder documentation](https://querybuilder.js.org/) defines a rules editor with nested groups and JSON output. The [sqlalchemy-querybuilder documentation](https://sqlalchemy-querybuilder.readthedocs.io/en/latest/) shows those rules applied to supplied models/queries and explicitly says it does not validate rule syntax.

Keep the current native editor and QueryBuilder-compatible interchange unless a demonstrated missing interaction requires the jQuery widget. The installed frontend already has a rule editor; adding jQuery/Bootstrap is not a prerequisite for a compatible output. No SQLAlchemy runtime is currently declared by the Workbench project.

The complete handoff consists of the versioned A/B/C definitions, shared object/context bindings, their composition and provenance. QueryBuilder-compatible filters are projections of supported mapped predicates inside that handoff. The whole envelope is not passed directly to `Filter.querybuilder`.

The consumer must provide allowed models/fields, relationship joins, event/time bindings, correlated evidence rules and any aggregate implementation. Test that bridge against an isolated declared consumer fixture before describing a mapped case as executable. Preserve application-side validation, bounded nesting, typed values and rejection of arbitrary SQL. Unknown semantics must not become unrestricted filters.

### 4.4 Saved data and compatibility

- Preserve the four database ownership boundaries and existing Requirement IDs, author/time, source hashes/spans, revisions and history.
- Read existing `/1` designs without changing them. Starting a revised interpretation produces a new explicitly saved revision; never bulk-convert Subject into Facility or mark historical records reviewed.
- Do not rename old fields merely for UI labels. Extend existing saved JSON and indexes only as required by the final contract.
- Keep save conflict detection, idempotent retry and source/catalog freshness checks. Candidate generation must not overwrite human edits, including edits made during a request.
- Update history readback, lineage indexes, collaboration validation and downstream delivery together. Older consumers must reject unsupported schema versions clearly rather than discard fields. Historical logic validation must dispatch by its saved version.
- Update [review-workflow.md](../../workbench/contracts/review-workflow.md), [storage-and-exchange.md](../../workbench/contracts/storage-and-exchange.md) and the user guide when implementation lands. Their current descriptions remain current-behavior documentation until then.

## 5. Implementation sequence and checkpoints

| Phase | Bounded work | Evidence required to continue |
| --- | --- | --- |
| 1. Prove the semantic contract | Use the seawater-temperature and anchoring-line examples to specify target objects, context, A/B/C definitions, source evidence and one structured handoff. Label meeting assumptions and missing source support explicitly. Check which operations the intended consumer can map. | A human-readable rule and structured rule express the same obligation; object identities and event/time context are consistent. Unsupported parts are preserved and named. |
| 2. Correct interpretation and persistence | Remove the source-to-formal overwrite from preview/save. Expose editable S/C/D interpretations, evidence links and existing context selection. Retain AI suggestions as optional candidates. | A manually interpreted Facility Scope survives save/reopen/retry while the original Subject remains Seawater temperature. Source changes flag review without rewriting text. |
| 3. Implement the set-design output | Evolve the existing three-group editor and schema to include the agreed object/context bindings and A/B/C composition. Generate readable logic and a supported QueryBuilder projection from the same structure. | Nested rules, relation/event bindings and period counts survive roundtrip without semantic loss. Unsupported mappings block only readiness, not safe draft preservation. |
| 4. Complete exchange and acceptance | Update versioned validators, history/lineage, collaboration and fixed deliveries. Verify a mapped fixture against the declared consumer when available. Update product guidance. | Save/reopen/export/import preserve definitions, source lineage and versions; real browser review passes. Native Windows verification is performed on Windows or explicitly left unverified. |

Proceed through these phases only after implementation is requested. Reuse existing modules, tests and storage; do not introduce a new service, database, general ontology engine or production compliance evaluator. Changes stay local until a separate publication milestone is authorized.

## 6. Acceptance cases

| Case | Required result |
| --- | --- |
| Temperature with supported facility context | Subject remains Seawater temperature; Scope can be Facility with its cited contextual basis. Three metres and at least once every week constrain measurement evidence in Demand. They are not automatically applicability filters. |
| Temperature without sufficient context | Facility is a proposed interpretation or unresolved object domain, not invented source wording. Missing week/calendar interpretation remains a gap until agreed. |
| Temperature across two assessment periods | Evidence that covers only one period cannot satisfy both by a total-count shortcut. The same measurement record must meet the relevant location/depth/time constraints. |
| Anchor-line components | The Scope preserves `partOf` and its agreed direct/indirect meaning. A component linked only to a Bridle is not silently included without the necessary relation evidence. |
| Storm-triggered checks | Applicability connects the component/location to the relevant event; an inspection before that event or for another component cannot establish C membership. No one-day limit or integrity criterion is invented from the shorter source sentence. |
| Combined conditions and alternatives | Preserve all delivered-by/installed-by/location/event predicates, `check OR replace`, and the owning exception. Do not turn a source quantity group into a different object count. Ambiguous event type/threshold remains unresolved. |
| Unknown applicability or evidence | Missing data does not silently produce an empty B or a satisfied verdict. B minus C, if shown by an isolated demonstration, means not established as satisfying, not automatically proven noncompliance. |
| Human edits and concurrent versions | Save/reopen, edits during AI generation/save, uncertain-save replay and stale-source handling retain intended human work and avoid duplicate revisions. |
| Legacy and delivery | Existing `/1` records and original history remain readable. New unsupported schemas are rejected explicitly by incompatible importers; complete consumers reproduce the definitions and composition. |

Use the existing `interpretation-simple.test.mjs`, `check-design.test.mjs`, `test_interpretations.py`, `test_check_design.py`, interpretation continuity/save-response tests and collaboration/delivery tests. Add a small set of counterexamples covering the failures above rather than tests that merely mirror the implementation. Browser acceptance must exercise actual edit/save/reopen and the rendered A/B/C relation, not only markup snapshots.

## 7. Next useful step

When implementation is authorized, start with phase 1: produce one complete temperature design and one anchoring design against the existing saved context and a clearly labelled consumer fixture. Resolve the target-object/context/relationship mapping before freezing a schema or building a broader interface. Keep any unsupported downstream operation explicit so progress on source-bound human interpretation does not depend on pretending a site evaluator is connected.
