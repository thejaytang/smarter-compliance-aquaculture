# Unified source-bound groups: delivery evidence

## Result

Implemented the source-selection editor with inline clause containers, recursive same-role field groups, independent group NOT and exact/range QC. Shared outer conditions and paired subject/action/object clauses survive the fourth-pane source projection. Subrequirements reference complete Requirements through Rx labels. Selectable original wording is read-only; source highlights and source-bound IDs remain intact. Multiple membership changes leave QC unresolved rather than guessing All. Human saves remain the only way to append history.

The additive `requirement-structure/1` tree is validated, projected to relational owner/parent/source/reference rows and included in interpretation context/fingerprints. Delivery uses `requirement-delivery/2` when tree history is present, with legacy `/1` import/export retained for legacy-only bundles. Prior records are not rewritten on read.

## Verification

- Full Workbench backend: **281 passed** (`python -m unittest discover -s workbench/tests`).
- Full frontend: **325 passed** (`node --test workbench/tests/*.mjs`).
- New regressions cover shared-condition branch binding, NOT at different nesting levels, Chinese/emoji/Norwegian/newline source offsets, invalid bounds, actor isolation, reference cycles, manual-save-only previews, idempotent replay, stale conflicts, immutable restore, delivery/source tampering and interpretation/tree round trips.
- Normal browser on `http://127.0.0.1:62742/`: selected source text, created a clause Group, assigned Subject, applied NOT, decomposed the Subject again and assigned a nested fragment. Nested selection exposed only Subject and Group. Attempted typing did not modify the original. The latest collapsed Reference a Requirement picker opened the Rx selector.
- Visual inspection at 1440 px; viewport checks at 1280 and 1920 px confirmed the document did not overflow horizontally. This is not a complete 200% or native Windows desktop acceptance run.
- Strong leave warning appeared. Test edits were explicitly discarded; example retained saved personal revision 1. Temporary viewport sizing was reset and user-owned browser tabs were not changed.

## Activation and preservation

Nine owning SQLite databases were consistently backed up before normal-service activation. Readback after browser testing verifies preserved saved splitting/material/interpretation business records, clean foreign keys and matching served assets. Backups, raw runtime records and temporary logs remain local and are excluded from Git. The new normal parent serves both new frontend modules. Shared AI remains Not connected and automation remains disabled.

Local cloud-backed source reads stalled during activation. Narrow file recovery and replacement of the task-owned blocked startup process restored the standard launcher. A broader directory recovery request was rejected by automatic approval review and was not performed. No unsaved user work was overwritten.

## Boundaries

No real model call, online source lookup, executable Site Model rule or compliance result was produced. Native Windows desktop interaction remains unverified for this change; branch CI tests synthetic cross-platform behavior separately. Saved example content was preserved rather than replaced with the temporary UI test structure. Arbitrary mixed grammatical fields do not receive a shared count: complete clause alternatives and same-role field alternatives are represented separately.

## Publication

Implementation commit `190962142cbf65ec66cf32dd156d66ace3acae53` was pushed to `codex/workbench-optimization-20260916` on 2026-09-16 and verified as the head of [PR #2](https://github.com/thejaytang/smarter-compliance-aquaculture/pull/2). [Windows/Ubuntu CI](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35095530574) was started for that exact code commit; the initial check showed Ubuntu material-contract passed and five other jobs running. This is not a claim of completed Windows acceptance.
