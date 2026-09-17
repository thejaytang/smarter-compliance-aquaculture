# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users and purpose

Business colleagues read aquaculture regulations and standards, verify extracted source content, repair errors, identify Requirement candidates and exchange review work. Their complete task is find, read, explicitly extract, compare, correct, save/resume, explicitly confirm and exchange. They should not require developer explanations or direct database work.

These facts and constraints come from the user's activated [2026-09-14 redesign goal](workbench-ui-redesign-goal-20260914.md); this is the design skill's concise product context, not another implementation-status source.

## Operating context

A local browser workbench combines Source Management System governance and a material-centered Requirement Extraction System. Existing implementation is plain JavaScript/CSS and component-owned Python environments. The normal macOS launcher is `Open Workbench.command`. Offline work packages support independent reviewer work; actual Windows acceptance remains a separate gate.

## Capabilities and constraints

- Source Management System owns source eligibility, identity and originals.
- Add sources expands into nested sidebar pages, with the selected subpage clearly marked. Unsubmitted intake fields, selected files and manual-detail expansion reset when leaving the page; the file picker has a Remove file action. It provides Official website (URL only), Upload file (explicit local metadata parsing, editable suggestions) and Source discovery (registered-source update checks; separately, API-powered new-source discovery).
- Source modules are Add sources, Source review, Source register and Review history. Material modules are Material review and Archive; extraction and review share the same detail.
- Content-level archives are permitted and labelled Content finalized · Requirements unfinished. Periodic review creates tasks without changing the archived version.
- Original, editable source content, manual Requirements and interpretation/check design occupy four adjustable panes, including collapse/restore and accessible overflow. Daily interpretation shows six values, with references, candidates and downstream mappings available on demand.
- A collapsible left sidebar holds workspace/module navigation, with the Smarter Compliance mark at the top and collaboration/reviewer controls at the bottom (2026-09-14 user revision). One record task bar leads the remaining full-space lists/details. No material register, material action-history module or mandatory Overview.
- Personal saves, explicit master adoption, content confirmation and Requirement review are different decisions.
- Source extraction and Requirement identification are separate capabilities. The full semantic processor and Site Model are not connected by default.
- Preserve originals, Canonical, Gold, historical outputs and human decisions. No downstream processing on reading, navigation or saving.
- Local work does not depend on remote decoration, external models or newly enabled schedules.

## Product principles

1. Protect source evidence and human effort before improving speed or appearance.
2. Make material, version, next action, remaining scope and recovery visible.
3. Use explicit decisions at version adoption and confirmation boundaries.
4. Report measured capability at its actual scope; engineering fixtures are not business review.

## Accessibility and visual commitment

The user requests restrained Apple-like translucent navigation and controls, with opaque readable documents, tables and editors. Verify 1280/1440/1920 widths, zoom, keyboard operation, visible focus, 4.5:1 normal-text contrast and reduced-motion/transparency fallback. Do not add a new theme solely to enlarge scope. [DESIGN.md](DESIGN.md) owns visual decisions; current delivery evidence remains in the owning state files.
