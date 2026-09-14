# System2 workbench review demo

Status: interactive practice UI, 2026-09-07. Live System2 tasks and decision receipts are not connected. Runtime and parsing contracts remain owned by System2.

## UI contract

- Reuse System1's vertical queue, search and selected-item styling. A pending queue contains only pending and follow-up items. Reviewed items appear in history; reopening appends an event and returns the item to pending.
- A named reviewer chooses an explicit, issue-specific action. Notes and text edits save drafts, never decisions. Accept confirms the selected text only; a merge preserves the footnote reference. HTML relationship and Excel column mapping require explicit choices.
- Missing content, unreadable evidence, reprocessing requests and keep-pending actions require a note and remain unresolved. No parser is started by the demo.
- History preserves actor, time, before/after values and notes. Reaccepting a reopened correction retains the corrected value.
- On small screens, source and extracted-result tabs share the same draft. Source zoom and the full PDF reader keep the editor available.

## Evidence and examples

Three PDF scenarios reuse the retained CS005 historical extraction from 2026-08-31. They are not claims about the current parser. PDF source hash, segment IDs, page indices, boxes and original run provenance are recorded in `../ui/demo-assets/provenance.json`. Rendered pages 20 and 21 were visually inspected against the source; the table review box was manually located for the demo.

The registered System1 original must match the demo hash before the full reader opens. A user-selected local file must have a PDF header and matching SHA-256. Only then is a PDF blob created, rendered and revoked when leaving; no upload request is made. Registered-original download and the official publisher link remain available. The page CSP allows self-hosted frames and this local blob reader; original HTML never executes.

HTML list and Excel header examples are synthetic, identified on screen. The XLSX view is a fixed illustrative grid, not an implemented workbook parser.

## Implementation and persistence

- `ui/system2-demo-data.js`: cases and evidence provenance, separate from real queues.
- `ui/system2-review-state.js`: draft/decision state, action constraints, history and progression.
- `ui/system2-review.js`: review UI and source reader.
- `ui/system2-review.css`: comparison layout. Queue styling is shared with System1 in `style.css`.
- Browser localStorage: versioned `workbench.system2-demo.*` namespace, separate per actor and origin. No production review API writes or Dashboard contributions. Conflicting tab edits and unavailable storage block recording and preserve entered text.

Production integration must replace this demo state adapter with version-bound System2 tasks, server-bound actor requests and applied receipts. It must preserve source checks and unresolved states. Demo history is not eligible for migration into formal audit or QA history.

The local service reuses its prior port when available to keep the browser origin stable. This is runtime state, not shared machine-specific configuration. Port-specific session cookie names isolate multiple loopback instances; an old same-workspace reviewer cookie is accepted during transition.

## Verification

Workbench tests cover actor binding, HTTP/PDF boundaries, local-instance cookie isolation, origin reuse, state transitions and existing dashboard behavior. Browser checks use an isolated service and verify correction drafts across reload, full PDF page 20/89, incorrect and matching local PDF selection, missing-table follow-up, explicit list/column selection, history and narrow-screen draft retention. These checks validate the prototype behavior; they do not constitute acceptance by business reviewers or System2 production readiness.
