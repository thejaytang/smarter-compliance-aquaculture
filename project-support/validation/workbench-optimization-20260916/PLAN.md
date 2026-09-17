# Workbench optimization | 2026-09-16

## Confirmed scope
Source-to-field traceability and relational integrity; validated QueryBuilder-compatible rule design; simpler human review flow; backend/frontend/integration/browser checks without real AI; Windows compatibility; safe synchronization to the existing GitHub repository. Preserve source/history, reviewer isolation, explicit human decisions and the shared API configuration. No Site Model execution.

## Current checkpoint
Audit found interpretation fields/references mainly embedded in JSON with no relational projection, full run-table scanning on each interpretation read, and repeated per-field metadata/candidate controls dominating pane four. QueryBuilder documentation explicitly supplies no syntax validation. Add a validated boundary and immutable version-bound lineage, rather than deriving queries from unchecked prose.

## Near-term actions and evidence
1. Add append-only lineage snapshots, field/citation/requirement relationships and bounded rule validation. Test migration, SQL joins, source revision changes, repeated quotes, ownership and restored histories.
2. Simplify six-field editing with on-demand evidence/candidates, source trail, separate rule design and recoverable drafts. Measure exposed controls and actual path steps; browser-check navigation, save/reopen, conflict, keyboard and responsive behavior.
3. Build functional coverage inventory for source/material/splitting/interpretation/settings/collaboration/recovery and run relevant component checks. Inspect Windows resource lifetimes and portable setup; obtain native Windows CI where available and label desktop-only gaps.
4. Update owned contracts and current state, inspect existing dirty work and remote state, stage only reviewed shareable changes, synchronize and verify remote commit/checks.

## Acceptance evidence
Code and consistent Workbench database baseline: `before/` (local only). Tests, browser observations, preservation comparisons and remote receipts will be linked here as produced. Real provider quality is excluded. Native Windows UI cannot be claimed from macOS or mocked checks.

## Implementation checkpoint

- Added version-bound relational origins, six fields, citations and rule nodes with foreign keys. Their parent is immutable interpretation/splitting history, not mutable active units. Old records are projected only from their saved splitting step; missing citation anchors are labelled legacy-unlocated.
- Bounded AND/OR trees, typed operators, unique rule IDs and explicit table.column mappings now form a separate optional check-design contract. Each comparison links to its interpretation field. No database query or satisfaction result is executed.
- Fourth-pane metadata/candidates are now on demand, saved source trail is one action, completed Requirement cards have a direct Interpret action, and keyboard Save stays scoped to the pane.
- Local regression: 246 Workbench backend, 278 frontend, 168 System1 and 1163 System2 passes (2 environment skips). See RESULTS.md for scope.
- Added branch-scoped Windows/Linux CI for reproducible backend/frontend, source and material-contract checks. This is test infrastructure; no business schedule or real model provider is enabled. Native Windows desktop interaction remains separately unverified.

## Completion checkpoint

Implementation, isolated verification, normal activation and safe branch synchronization are complete. All six Windows/Ubuntu jobs passed on code commit `3f502d5`; [RESULTS.md](RESULTS.md) owns counts, direct observations, PR #2 and unverified boundaries. Normal business tables are unchanged. The main branch is not merged.
