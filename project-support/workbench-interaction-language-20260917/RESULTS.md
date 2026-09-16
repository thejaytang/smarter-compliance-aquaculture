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

No real model request was made. Native Windows and OS-level 200% scaling were not rerun for this increment. The implementation uses the existing browser/standard-library components and no new platform-specific dependency. The earlier Windows limitation remains.

The interaction contract is [here](../../workbench/docs/manual-requirement-splitting.md#interaction-language-current-2026-09-17). These local checks establish the tested workflow; colleague acceptance remains separate.
