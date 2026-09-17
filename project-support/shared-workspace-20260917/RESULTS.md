# Shared workspace and colleague handoff

## Implemented and locally verified

- Shared saved Requirement sessions, searches, annotation projections and interpretations across named reviewers. Stable creator storage keys, actual `edited_by` plus time in history; concurrent saves still conflict. No autosave or real AI calls introduced.
- Shared Requirement delivery v4 includes all authors and cross-author references in one consistent graph. Two independent SQLite peers complete export/import, conflicting edits, explicit choice, return export and continued interpretation editing. Original histories and foreign keys are checked.
- Readable import comparisons cover delivery versions 1–4, group quantities, source relationships and requirement links. Source markup is escaped.
- Explicit development cleanup removed 16 Requirement sessions, 15 current interpretations, 5 main material documents and their personal/legacy test stores from active runtime. Before/after row fingerprints match for every System1 authority/assessment table and Workbench actors, source drafts, source request journal and review policy. A source-only full snapshot captures 88 source heads and zero material/Requirement heads.
- Local recovery is under `local-backup/`, ignored by Git. Historical engineering backups outside active storage were not broadly erased. No source original was deleted.
- Initial source seed: revision 13, 88 sources, 137 operations, 240 history rows, 73 verified source-version links, retained source drafts and four human assessment holds. 84 files, 22,321,771 bytes. SHA-256 `e24c566133f8829688017ddac01ffb61e7f2bdbac7ce62560f80329c71e8267b`. Materials annotations and credentials excluded.
- Active originals, local config, generated registers and selected data archives are removed from Git tracking while local copies remain. Initial data is delivered separately; future application updates leave ignored local work in place. Git history still retains earlier published files.
- Rebuild scripts create missing local config only and disable schedules in fresh config. Initial restore verifies checksums/paths and refuses an existing workspace or original. Dependencies use component environments and existing declarations/locks.

## Validation

- Local Workbench regression: 307 Python tests passed, plus the new shared full-snapshot round-trip test passed independently (308 total).
- Frontend: 371 tests passed.
- New tests cover cross-author editing, attribution, stale versions/sources, cross-author link exchange, shared graph conflict resolution, safe initial restore and readable conflict rendering.
- Fresh Windows/Linux CI and publication are pending at this checkpoint. Prior Windows results do not certify this new patch. Native Windows desktop/pointer/scaling and the user's Windows refinements remain separate from CI.

## Delivery boundary

Fresh colleagues clone the separated application version, rebuild environments and restore the initial source seed once. Existing older clones must preserve formerly tracked originals/config/output before this transition; Git removes those tracked paths when applying the separation commit. Daily application updates must never reapply the seed. All collaborators update before exchanging shared Requirement v4 packages; older apps reject the new contract rather than silently discarding its contents.
