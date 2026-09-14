# Source intake content inspection | 2026-09-14

The URL entry previously performed narrow metadata inspection and immediately staged a candidate; uploads could bypass inspection. Both routes now require real basic content inspection, show loading, preserve evidence and let the operator review/edit generated fields before a PENDING candidate is created. No automated acceptance or inclusion is introduced.

## Behavior and boundaries

- System2 proposes source metadata and five reasoned rating suggestions from original native text. Unknown values stay unknown. Summary text is original metadata or a selected original excerpt, not a generated legal opinion.
- PDF inspection reads at most 300 pages and reports unreadable pages; HTML skips active/navigation blocks and rejects explicit access/error pages; original XLSX inspection spans sheets, bounded by 50,000 cells, 250,000 characters and ZIP limits. Text analysis is capped at 250,000 characters. No OCR, external model, latest-law verification or legal applicability claim.
- Workbench retains a server-owned inspection bound to actor, original bytes/hash and URL. Missing inspection triggers mandatory parsing before intake. Forged/reused evidence, changed originals and parser failures cannot bypass the intake guard. A durable bound payload preserves ambiguous retries.
- System1 retains the complete candidate field set and basic inspection in its database; duplicate pending candidates can receive missing inspection without losing prior human fields. Its existing INCLUDE/Pending-Include controls remain intact. Missing suggestion values no longer inherit legacy ratings.
- UI: Inspect source / Parse file, actual spinner and stage text, disabled repeated actions while busy, editable results, explicit Add to review, retained input after failure. Source review displays the same machine evidence. No artificial wait or fake progress percentage.

## Validation

| Scope | Result | Evidence |
| --- | --- | --- |
| Frontend full regression | 209 passed | [log](source-front-tests.log) |
| Workbench full Python regression | 193 passed | [log](source-workbench-all.log) |
| System1 full regression | 146 passed, 1 preview-test failure initially | [original log](source-owner-all.log) |
| Corrected System1 preview contract | 2 passed | [rerun](source-owner-contract.log) |
| System2 full regression | 1131 passed, 1 skipped, 1 dependency warning, exit 0 | [log](source-system2-all.log), [1132 collected items](source-system2-collected.txt) |

The preview-only System1 failure came from filtering human operations by source_id: two pending unregistered candidates have operation IDs but no source IDs. The test now counts operation IDs, matching the generated dashboard formula; runtime database access was not changed to read Excel. The initially failed run remains recorded. Targeted parser cases additionally cover a publisher on PDF page 6, a blank page, multiple XLSX sheets, full metadata/reason generation and access-page rejection.

The Codex in-app browser exercised the current code against the isolated [fixture](fixture) on port 55395, with business workers disabled:

1. Real GET of https://example.org/ through Inspect source, observed disabled inputs and retrieval/inspection loading; displayed an excerpt, read coverage and five evidence rows. No queue task until explicit Add to review.
2. Added that URL to review, then read its retained inspection and PENDING candidate in Source review.
3. Uploaded the synthetic [engineering original](inspection-source.html), observed Reading file and generating review suggestions, verified generated title/publisher/version/classification and review suggestions. Changed the title to Human corrected engineering source and added it to review; both human title and machine evidence survived database readback.
4. A loopback URL failed the public-address guard; its input remained available for retry, with no Add to review or new task. Automated tests cover parser failure and stale/foreign inspection binding.
5. Native side-browser screenshot showed usable wrapping/scrolling; no console errors/warnings were recorded before the intentional failed-URL check. File chooser transport stalled once, then completed; this is not parser latency evidence.

[Database readback](fixture-inspection-readback.json) contains exactly two new PENDING candidates and their retained basic inspections. No candidate was registered or included by engineering. All test writes were isolated.

## Normal activation

The normal page showed PA004 personal revision 0, Saved, before shutdown. The existing Exit workbench control stopped the parent; the root launcher restarted it in the desktop environment to retain native default-file opening support. New PID 29697 on port 62742 reports no changed parent source files. Normal source pages were refreshed and visibly display Inspect source and the expanded parsing wording. No normal source parsing, registration or business review was exercised.

[Before](normal-before.json) and [after](normal-after.json) bind the activation health records and identical System1 governance logical hash. Startup evidence does not prove every code path or broad extraction quality. System1/System2 parsing workers load current source per call. [Code hashes](code-manifest.json) bind the tested changes.

No dependencies, APIs, schedules, source sweeps, source selections, original files, Canonical or material reviews were changed. Existing Requirements and independent quality/Windows limitations remain as recorded by their owning states.

Temporary browser tab and fixture server were closed after readback; port 55395 is no longer reachable. The normal Official website tab remains open on 62742. Changed-document links and git whitespace checks pass.
