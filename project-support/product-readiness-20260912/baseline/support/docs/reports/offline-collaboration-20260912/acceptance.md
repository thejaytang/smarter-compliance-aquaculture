# Offline collaboration acceptance

Status: **LOCAL_VERIFIED_WINDOWS_PENDING**, 2026-09-12. The implementation is loaded in the normal macOS workbench. Actual Windows evidence is **PENDING_ACTUAL_WINDOWS**, so the approved round is **not fully complete**.

## Human workflow and scenario evidence

| Acceptance scenario | Local result | Evidence |
| --- | --- | --- |
| Independent distribution, personal save, return and adoption | PASS; one coordinator and two distinct reviewer roots/databases | `workbench/runtime/offline-collaboration-acceptance/latest-check.json`, `browser-evidence.json` |
| A reviewed, B edits afterward | PASS; original A history retained, only unaffected pages inherit A checks, combined global confirmation remains empty | `edge-cases.json`, `serial_ranges` |
| Same paragraph / same table cell | PASS; both values and common baseline displayed; keep, submitted and manual edit exercised | `browser-evidence.json`, table-conflict screenshots |
| Different parts edited by two people | PASS; combined preview plus contributor provenance and impact checks | `edge-cases.json`, provenance regression tests |
| Human/machine disagreement and unchanged machine portions | PASS; real extraction does not overwrite human text; explicit inline choices; identical result reuses recorded decision with audit | `machine-cases.json`, `browser-evidence.json` |
| Partial work and combined checks | PASS; no full confirmation inferred; unresolved scope/candidate/source issues remain visible | `edge-cases.json`, material collaboration tests |
| Source rating, issuer, note and issue review | PASS; actual System1 rules, separate partial receipt, append-only notes and explicit issue evidence | `edge-cases.json`, System1 collaboration tests |
| Unknown/repeated/bad packages, changed original and restart | PASS; no guessed merge, identity conflict rejected, original retained, saved work recoverable | `edge-cases.json`, `exchange-safety-tests.log`, `workbench-final-tests.log` |
| Main changed after comparison | PASS; stale comparison refused before application | `edge-cases.json`, `machine-cases.json` |
| Failure after source success, before material success | PASS; exact persisted operation resumes without repeated source application; global UUID and atomic final receipts tested | `edge-cases.json`, identity regression tests |
| Real Windows round trip | **PENDING** | Prepared local code/work ZIPs and the Windows checklist; no actual Windows claim |

## Verification scope

- Workbench current regression: 104 tests passed (`archive-service-tests.log`). Frontend: 102 tests passed (`archive-ui-tests.tap`); preceding results are retained. Source collaboration plus existing bridge/database checks: 30 passed. System2 final focused material/impact/collaboration/provenance checks: 61 passed. An earlier broader System2 run in this round passed 1,008 with one skip; final focused checks cover the later provenance fixes. These counts support the listed behaviors rather than replace scenario acceptance.
- UI checked against the explicitly requested ui-ux-pro-max and Impeccable skills after their invocation. Read `ui-ux-review.md` for actual checks, interpreted detector findings and limits. Desktop and narrow-screen captures are in `output/playwright/offline-collaboration/`.
- Normal browser load: no console errors, 60 captured GET requests, no POST, no opened normal material; `normal-browser-load.json` and `normal-browser-requests.txt`.
- Normal runtime: current parent loaded without source drift, six components with recent success/no current error; `normal-runtime.json`. This is current operating evidence, not a multi-day stability claim.
- Migration protection: complete backup verified with 6 stores, 8,389 resource files and 327 source files. `normal-preservation.json` confirms all 73 originals, 75 Canonical artifacts and existing business tables unchanged. Only a maintenance session and the additive collaboration table changed. Normal material/candidate counts remain zero.
- Actual isolated recovery checks preserve bodies, histories, original evidence and branch paths without symlinks. `restored-service-evidence.json` covers six materials; recovery tests include personal WAL data, assets and local-root resolution. Older attempts and their diagnosed errors were retained.

## Navigation correction

Removed the obsolete standalone System3 navigation, Overview card and incoming-feed UI route. Source management and Materials are the two work areas. The unconnected third pane remains inside each material; internal history and backend interfaces are retained. Inactive reserved threshold editing and empty reserved-stage weekly series are no longer presented as active work. Actual historical observations, if present, remain visible as legacy records. The real browser check is retained in `navigation-browser.json`.

## Prepared Windows handoff

`windows-reviewer-code.zip` and its inventory contain allowlisted code, UI, dependency declarations, templates and setup guidance, with no runtime environments, accounts or normal business files. `windows-review-work-TS001.zip`, `TS002.zip` and `TS003.zip` contain synthetic HTML, Excel and PDF fixtures; exact files/hashes are listed in `windows-work-packages.json`. All are local and not sent.

The office user must run startup, package import, original reading, Extract, correction, partial save, restart and submission export, then manually return the package for macOS import/conflict/adoption checks. The [Windows checklist](../../../workbench/docs/windows-offline-review-checklist.md) records the required evidence. Missing actual Windows evidence is the remaining cross-platform completion gate.

The third-pane nested Requirement structure, forms and semantic processor are intentionally deferred. Process remains disabled. No engineering action represented content confirmation as completed structured Requirements or a compliance judgment.

## Pending, Archive and expanded work area

The actual `content_confirmed` main revision and its human confirmation determine Archive membership. Partial personal work, active candidates, source changes and open spot-checks remain Pending without replacing the archived version. `archive-inspection.json` records the real isolated extraction, main adoption, acceptance, check/progress/restart, problem/repair/resolution and new-archive journey. Old accepted revision 2 remains readable after revision 4 is confirmed.

`archive-focus-browser.json` records the real Chrome task creation/save/pass, expanded viewport, pointer and keyboard resize, browser reload proportion recovery, Escape restoration and 600px no-overflow check. The final displayed form values were verified after correcting a submission-cache mismatch. Screenshots were visually inspected. The earlier synthetic source read timeout and browser driver issues are recorded rather than treated as service-stability evidence.

`archive-focus-runtime.json` is the latest normal runtime snapshot: new parent loaded, no source drift, six healthy components. `archive-focus-preservation.json` confirms 73 originals, 75 Canonical files and existing business table fingerprints unchanged. The new complete stopped-service backup is `workbench/runtime/archive-focus-pre-load-backup/` (6 stores, 8,389 resources, 329 source files). No new schema migration or real business review was performed.

New spot-check task records remain local to their workbench and are not included in offline work/submission ZIP exchange. Material drafts/submissions retain their existing offline path. Actual Windows acceptance and cross-computer task delivery must not be inferred from these local checks.
