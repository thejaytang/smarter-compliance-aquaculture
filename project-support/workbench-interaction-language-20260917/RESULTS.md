# Third-pane interaction consistency, 2026-09-17

## Delivered

- One editing state for saved and unfinished Requirements. All mutation paths, including MIN–MAX input, reopen an unsaved preview consistently. Stale sources, readonly workspaces and pending/uncertain requests stay protected.
- One source annotation surface per ordinary entry. The floating toolbar identifies its destination with Add to; choosing an outer Group supports shared context without relocating source marks implicitly. Same-field nesting restricts available field actions. Whitespace-only selections do not offer annotation actions.
- Split on fields; Group selected only with two or more checked siblings; Ungroup only where quantities and metadata can survive it. Implicit single-member wrappers stay in the model but do not add redundant frames. Quantity and grouping actions sit above their children.
- Root Exception/Subrequirement dropdowns remain visible. Nested Groups reveal the same link selectors with Link requirement. Link is enabled after selecting a target. Existing links keep their vertical rows and individual removal controls.
- Header disclosure is presentation only. Card crosses remove only their owning item (a Group includes descendants); whole-Requirement Remove retains its existing confirmation and recoverable history.
- One sticky Save / Save & close / Discard area. Save permits unfinished work. Save & close appends validation/completion operations to the existing atomic save batch and produces one revision. Failed or uncertain saves keep the draft; retry retains the exact request identity. Closing already complete, unchanged work does not write history. Discard confirms and targets only this Requirement.
- Errors appear beside saving controls. Help contains the action definitions. No changes to source wording, IDs, stored quantities, existing examples or fourth-pane legal interpretations.

## Verification

- Frontend: **366 / 366** Node tests pass. Added coverage for direct editing parity, same-field toolbar scope, eligible grouping controls, atomic completion payloads, validation rejection, exact retry identity, new-entry and cross-session save identity, pending ranges on collapse, and confirmed discard.
- Backend: **299 / 299** owning-environment unittest tests pass. Added real SQLite tests showing Save & close commits one replayable history revision and rejects an empty Group without partial history or foreign-key failures.
- Live normal service at 127.0.0.1:62742: selected including, changed the toolbar destination between G4 and R2, verified Relationship gating, selected two siblings, grouped them, attempted incomplete Save & close, observed validation failure with retained draft, cancelled Discard, then discarded explicitly. Split and same-field selection were checked independently. All browser test changes were discarded.
- Layout: 1440, 1280 and 640px viewports inspected. The source toolbar remains inside the narrow viewport; bottom actions remain available; pane-level horizontal scrolling remains intentional on narrow screens. Header actions, source selection, group indentation and card removal do not overlap in the inspected layouts.
- Current example revisions are R1=6, R2=3, R3=1, R4=2, unchanged by this work. Original user tabs and their unsaved work were not reloaded or discarded.
- Source modules and styles load directly from the normal service; no runtime/database migration or service restart was needed.

## Boundaries

No real model request was made. Windows automated runtime verification is recorded below. Windows desktop browser interaction, OS-level 200% scaling and the cross-computer reviewer round trip were not exercised for this increment. The implementation uses the existing browser/standard-library components and no new platform-specific dependency.

The interaction contract is [here](../../workbench/docs/manual-requirement-splitting.md#interaction-language-current-2026-09-17). These local checks establish the tested workflow; colleague acceptance remains separate.

## Publication

2026-09-17: implementation commit `0fae54eac5990a8229fb1f934358771aac7c6baf` was pushed to `origin/codex/workbench-optimization-20260916`. The remote branch reference was read back and matched that commit. Main was not merged. This receipt is maintained separately from local runtime data.

## Windows verification, 2026-09-17

Inspected the completed [portability run 35160637346](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35160637346), including full job logs and the reported checkout SHA. It ran automatically after the implementation push, on commit `0fae54eac5990a8229fb1f934358771aac7c6baf`. At verification, HEAD `5bc96ff81567d23716f839b768bbe5d3ac5863f0` differed only by this report's publication receipt; the tested source/UI/test paths had no uncommitted changes. No duplicate run was needed for unchanged executable code.

The actual runner was Microsoft Windows Server 2025 (`windows-2025-vs2026`), with Python 3.12.10 and Node 22. All three Windows jobs and all three Ubuntu counterparts succeeded.

| Windows check | Result | Evidence |
| --- | --- | --- |
| Workbench backend and HTTP | 299 tests, OK | [Workbench job](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35160637346/job/105010335877) |
| Frontend state/rendering logic | 366 passed, zero failed/cancelled/skipped | Same Workbench job |
| Workbench Python compilation | Passed | Same Workbench job |
| System2 material/platform contract subset | Passed; progress reached 100% with no failures | [Material job](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35160637346/job/105010335556) |
| System1 source contract suite | 168 tests, OK | [Source job](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35160637346/job/105010335766) |

The material subset covers material content/body/Markdown, reader navigation, API environment, platform memory, SQLite lifecycle and platform-support integration. Its existing pytest quiet configuration suppresses a numeric summary; it is not the full System2 suite. Logs include non-failing dependency/action deprecation warnings and a dependency-cache hardlink fallback. No source change or dependency upgrade was required by this verification.

These are real Windows OS/runtime tests on isolated CI fixtures. Frontend tests run in Node, so this does not establish Windows Chrome/Edge pointer selection, layout/scaling, native Office behavior, fresh-user launcher setup or reviewer ZIP round-trip acceptance. The user's running Mac service, open drafts and business data were untouched.
