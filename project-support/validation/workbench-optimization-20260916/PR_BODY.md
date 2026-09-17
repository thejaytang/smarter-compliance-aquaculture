## Result

The manual material workflow now continues from source-preserving Markdown through Requirement splitting and field annotations to a fourth pane for interpretation and check design. Six editable Scope/Condition/Demand fields have separate AI candidates, explicit adoption, versioned saves and deterministic checking logic. One Settings form configures the shared optional API.

Saved interpretation fields, citations and optional typed AND/OR rules now join to immutable Requirement/splitting history and frozen material/source locations. QueryBuilder output uses explicit downstream field mappings; it does not execute a Site Model query or infer missing legal requirements. The default editor exposes fewer controls, with evidence, candidates, source trails, advanced rules and recovery available on demand.

## Verification

- macOS: 246 Workbench backend/HTTP, 278 frontend, 168 System1 and 1163 System2 tests passed; 2 System2 environment skips.
- GitHub Windows/Ubuntu jobs cover Workbench, source workflow and affected material/platform contracts. See the PR checks for the current commit.
- Browser checks covered source trail, typed rule save/reopen, keyboard save/resize, collapse/restore and 1280/1440/1920 widths. Native 200% recheck was interrupted by the locked desktop.
- Normal-service activation preserved existing business rows across eight database snapshots; foreign-key checks were clean. Shared API remains Not connected.

## Boundaries

No real model calls, automatic Requirement extraction or actual compliance conclusions. Site Model field definitions, joins and evidence semantics still require downstream agreement. Native Windows desktop interaction is unverified. Collaboration ZIPs still exclude splitting and interpretations; full local database recovery includes them. Credentials, runtime databases, source originals and local backup artifacts are excluded from this change.
