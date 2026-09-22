# Fourth-pane implementation validation

Date: 2026-09-21. Local `developing-only-jay` changes over `badc2ce05ba4dd6c2a4fa734bba9478bbbcfbdd6`, which includes main `b221b162b767c6f93a46ea9886cff472b52a695e`. No commit, push, new dependency or database migration.

## 1. Delivered behavior

The four panes retain their order. Each fourth-pane section shows mapped third-pane wording before editable Scope/Condition/Demand Logic. Source projection no longer replaces the interpretation on preview or save. Exact contextual citations, supporting information, open questions and related saved materials remain available. Generated A/B/C definitions and B ⊆ C follow the adopted Logic. C contains objects supported by Demand evidence, not the evidence documents themselves.

`requirement-check-design/2` adds shared object/context metadata and mapping confirmation, preserves stable rule IDs, supports explicit group NOT and retains unmapped relation/time predicates. Unsupported branches block the complete affected QueryBuilder projection. Missing applicability does not become an unconditional filter. Neither confirmation nor save produces a site verdict or completes interpretation review. Existing `/1` records retain deterministic historical/import behavior; explicit new saves upgrade drafts.

Reused the existing native editor, catalog, history, provenance and package flow. No jQuery/Bootstrap/SQLAlchemy runtime was added. The official [QueryBuilder documentation](https://querybuilder.js.org/) and [SQLAlchemy QueryBuilder documentation](https://sqlalchemy-querybuilder.readthedocs.io/en/latest/) informed the existing JSON interchange boundary. Relation joins, correlated evidence and temporal aggregates still require an agreed downstream mapping.

## 2. Automated checks

- [Workbench suite](workbench-tests.log): 333 passed, including interpretation saving, history, concurrency/replay, lineage and collaboration validation.
- [Frontend suite](frontend-tests.log): 376 passed.
- After the final missing-information and disclosure-state refinements, [affected backend tests](final-targeted-tests.log): 43 passed; [affected frontend tests](final-frontend-tests.log): 21 passed.
- New regressions cover independent facility Scope, depth/frequency retained in Demand, unaccepted candidates, OR/NOT fail-closed projection, mapping confirmation invalidation, mixed `/1` and `/2` histories, restore, exchange and tampered handoff rejection.
- JavaScript `setHandoff` output equals the saved Python handoff exactly for the final browser-saved synthetic example.
- Environment check, development-index boundary, whitespace check and [stopped-workspace integrity verification](workspace-integrity.json) passed.

## 3. Browser and real-service checks

Chrome tested the real application against a separate synthetic workspace. A context sentence explicitly established an aquaculture facility, followed by the user's temperature example. The third pane retained `Subject = Seawater temperature` and the two source conditions. Through the UI, Scope was interpreted as the facility, an exact contextual citation was attached, and depth/frequency were written into Demand. The Condition was deliberately left blank and remained unresolved.

The native rule editor saved an explicitly unmapped weekly measurement predicate and assessment context. Adding a rule now keeps its disclosure open. Save and Reload saved interpretation retained the wording, citation and incomplete status; the page showed no console errors. Screenshot inspection confirmed the existing horizontally scrollable pane layout and accessible sticky save action.

Two independent services then passed real business-package export/import, receiver re-export and restart readback. The exact fields, design and generated logic survived. Both test services were stopped. See [isolated round-trip results](isolated-roundtrip.json).

The actual user workspace was stopped safely after confirming Saved state, verified, then restarted at `http://127.0.0.1:62742/`. Browser readback confirmed PE001 personal revision 12, Saved, existing R1–R3 and the new fourth-pane controls. No interpretation or other business revision was saved in the real workspace. All four business databases, five protected settings files and eight unrelated local files remained byte-identical to the pre-sync baseline. See [preservation results](preservation.json).

## 4. Limits

No production Site Model evaluator, real AI provider, native Windows run or external publication was exercised. Relation/time predicates are preserved as unmapped expressions, not implemented queries. A ready mapping means ready for downstream consumer validation, never an executable or satisfied compliance result. The complex anchoring example is covered by rule preservation/negation tests, not a live site evaluation.
