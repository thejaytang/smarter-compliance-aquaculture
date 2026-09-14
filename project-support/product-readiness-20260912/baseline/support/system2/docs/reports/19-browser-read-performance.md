# Browser loading correction | 2026-09-09

## Diagnosis

The user's System2 page remained at `Loading actual extraction results…`. The browser's state request synchronously reconciled every document, returned the complete stored evidence graph and then regenerated the Excel workbook before responding. Production inputs brought the workflow store to roughly 470 MB and the register above 100 MB. This coupled routine navigation to expensive export and large response serialization.

## Change

A read-only `system2-browser/1` projection now carries source/task state and compact unit lists, retaining full body text for queue search. Complete unit evidence is fetched separately by document/unit ID, with snapshot document/policy revision checks before the browser shows an editable form. Navigation discards late responses. Original evidence, Canonical, acceptance rules and mutation guards are unchanged.

Display requests do not apply policy or regenerate Excel. The workbench's dedicated workbook thread attempts a refresh every 60 seconds after the preceding attempt finishes. Parser work uses small summary readback. Saved decisions return without waiting for an export; explicit Excel downloads continue to request fresh, reconciled exports. The legacy full state adapter remains available.

## Evidence

- Production direct browser projection: 3.7 seconds, 9,603,709 JSON bytes, 38 sources and 19,228 units at that sample.
- Live summary HTTP request after service reload: 5.85 seconds and 35,486 bytes. Production processing was active during measurement; these are point-in-time timings, not a latency guarantee.
- A later live HTTP sample while parsing/export continued returned the full compact list in 13.62 seconds (10,757,294 bytes) and one full unit in 4.34 seconds. Browser blocking on Excel has been removed; active processing still creates variable read latency.
- Browser verification showed CS002's 9,135 pending units, a 60-item queue page and the full coverage form with evidence controls. A subsequent Refresh progress returned the complete editable form again; no production review was submitted.
- System2 full regression: 587 passed, one missing PDF fixture skipped. Workbench Python: 21 passed. Existing frontend tests: 14 passed. Three additional frontend checks verify exact-version evidence loading, stale-detail rejection and cancellation after navigation.
- The service was reloaded on the same loopback origin. Existing parsing jobs continued, and Weijie Tang's session/history remained present. Production timing/readback evidence is stored in `tmp/browser-read-evidence.json`.

## Remaining scope

The Excel register itself remains large and expensive to refresh. Browser list size still grows with total source text; server-side queue pagination is a further scaling step if needed. Persisted display snapshots can lag reconciliation; decisions and downstream exports still perform authoritative validation. PDF accuracy and acceptance of all source content are separate gates.
