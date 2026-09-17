# Shared workspace and colleague handoff

## Implemented and locally verified

- Shared saved Requirement sessions, searches, annotation projections and interpretations across named reviewers. Stable creator storage keys, actual `edited_by` plus time in history; concurrent saves still conflict. No autosave or real AI calls introduced.
- Shared Requirement delivery v4 includes all authors and cross-author references in one consistent graph. Two independent SQLite peers complete export/import, conflicting edits, explicit choice, return export and continued interpretation editing. Original histories and foreign keys are checked.
- Readable import comparisons cover delivery versions 1–4, group quantities, source relationships and requirement links. Source markup is escaped.
- Explicit development cleanup removed 16 Requirement sessions, 15 current interpretations, 5 main material documents and their personal/legacy test stores from active runtime. Before/after row fingerprints match for every System1 authority/assessment table and Workbench actors, source drafts, source request journal and review policy. A source-only full snapshot captures 88 source heads and zero material/Requirement heads.
- Local recovery is under `local-backup/`, ignored by Git. Historical engineering backups outside active storage were not broadly erased. No source original was deleted.
- Initial source seed: revision 13, 88 sources, 137 operations, 240 history rows, 73 verified source-version links, retained source drafts and four human assessment holds. 83 files, 22,320,677 bytes. SHA-256 `6c141d49199a01975d0cc559cc930afbbc6137a604d6b5d46e7fee84b92d8e1a`. Materials annotations and credentials excluded.
- 6,827 historical development snapshot paths, test Collaboration ZIPs and duplicate/legacy output workbooks also leave the current Git tree; local files and earlier Git history remain. Historical reports referring to these retired paths describe local/archive evidence, not a current application dependency.
- Active originals, local config, generated registers and selected data archives are removed from Git tracking while local copies remain. Initial data is delivered separately; future application updates leave ignored local work in place. Git history still retains earlier published files.
- Rebuild scripts create missing local config only and disable schedules in fresh config. Initial restore verifies checksums/paths and refuses an existing workspace or original. Dependencies use component environments and existing declarations/locks.

## Validation

- Local Workbench regression: 307 Python tests passed, plus the new shared full-snapshot round-trip test and two application-boundary checks passed independently (310 total).
- Frontend: 371 tests passed.
- New tests cover cross-author editing, attribution, stale versions/sources, cross-author link exchange, shared graph conflict resolution, safe initial restore and readable conflict rendering.
- [Windows/Linux CI for `3d02898`](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35202684306) passed all six jobs after retiring historical snapshots: Workbench backend/HTTP/frontend/launcher checks, System1 and the System2 material/platform subset. The initial attempt exposed tests reading live business Excel; they now use a synthetic fixture. Native Windows desktop/pointer/scaling and the user's Windows refinements remain separate from CI.
- The final 83-file seed restores into a fresh application layout with its tracked storage guide already present. The real System1 bridge reads 88 sources; both databases pass integrity/foreign-key checks and Requirement sessions remain zero.

## Delivery boundary

Fresh colleagues clone the separated application version, rebuild environments and restore the initial source seed once. Existing older clones must preserve formerly tracked originals/config/output before this transition; Git removes those tracked paths when applying the separation commit. Daily application updates must never reapply the seed. All collaborators update before exchanging shared Requirement v4 packages; older apps reject the new contract rather than silently discarding its contents.

## Published milestone

On 2026-09-17, GitHub `main` was fast-forwarded without force to verified functional commit `3d0289865328a2d03227892a9775f111625eb885`. Later status-only commits retain this tested implementation. The [initial-data release](https://github.com/thejaytang/smarter-compliance-aquaculture/releases/tag/initial-source-data-20260917) was published at `2026-09-17T09:05:36Z`, targeting that commit. GitHub confirms all four assets and their SHA-256 digests.

- Source seed: `6c141d49199a01975d0cc559cc930afbbc6137a604d6b5d46e7fee84b92d8e1a`.
- Environment kit: `be0133aec4efeb2d83c0515bcb27cf15df9fb0c95d15cb778d693d8014dfe64b`.

New colleagues should use the guide's shallow `main` clone to avoid downloading old Git history, rebuild environments and restore the initial seed once. Real subsequent work is exchanged through Collaboration. The normal Mac service has the shared-workspace implementation loaded and its source register still lists 88 entries.

## Completion audit: colleague installation, Collaboration and updates

The follow-up `workbench/tests/integration/colleague_handoff.py` closes the gap between separate module tests and a real colleague workflow. It uses two independent installations, a synthetic initial source seed, actual System1/System2 subprocess adapters and the real HTTP service. It mocks no domain service. Windows runs the shipped `Rebuild environments.cmd` and `Open Workbench.cmd`; Mac/Linux run the same Python entry implementations.

| Required outcome | Authoritative evidence |
| --- | --- |
| One initial data delivery retains genuine source work | Published immutable source ZIP and checksum above; restored 88 source records and source history, checked all 73 original bindings, and verified zero Materials/Requirement test records. |
| Later Git updates contain application files while local data remains | `check_app_boundary.py` passes on the current index. The integration journey performs a real `git pull --ff-only` from a local application remote and compares all local SQLite stores, source HTML and configuration before/after. |
| Windows users can rebuild and launch locally | Native Windows CI executes both shipped `.cmd` entry points, creates all declared component environments and opens two independently bound Workbench services. |
| Colleagues exchange and continue each other's work | Real full-workspace export/import/return includes a saved material, Requirement field edit and interpretation. Both reviewers can read the returned work; the actual editor is retained in history and source text remains linked. Separate regressions cover conflicts and cross-author Requirement links. |
| Application updates preserve collaboration history and saved annotation | The complete journey stops both services, updates each Git checkout, verifies unchanged database/original/config bytes, restarts, and reads back the saved Requirement and interpretation with the correct author. |
| Mac development can feed Windows validation and the shared app branch | The same journey passed on Mac and on the Windows/Linux CI matrix; code and environment declarations use relative component paths. The colleague guide describes Mac development, Windows refinement and subsequent `main` pulls. |

The first Windows journey completed its work exchange but exposed an unclosed SQLite connection in the test's fingerprint checker. The checker now explicitly closes it. Separately, a Windows source regression exposed timestamp-only workbook replacement detection: an external save can retain the same modification timestamp. `save_workbook_atomic` now checks original bytes as well. A forced equal-timestamp/equal-size edit reproduced failure before the fix and is preserved after the fix; all 169 System1 tests pass locally and on Windows/Linux.

The application-only follow-up is commit `790b10ccd33daa8482b679627baa5aa1a95dd13c`; all eight jobs in its [CI run](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35204654433) passed, including both native colleague journeys. Initial source/environment release assets are unchanged. This proves local installation, launch, data exchange and update behavior. It does not claim native browser pointer/scaling acceptance on the user's particular Windows PC or acceptance by the actual team.
