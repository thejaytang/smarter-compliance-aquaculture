# Missing original, failed job and retained human work

## Scope and result

**PASS for the bounded isolated recovery sequence observed here.** Synthetic TS004 was used on `http://127.0.0.1:60905/`. The test temporarily moved only its pinned engineering HTML copy, retained the exact bytes, and used the existing worker lock to control a user-requested candidate. No business original, Canonical, Gold, real decision, master version, normal service, dependency or extraction algorithm was changed. This is recovery evidence, not an automatic-quality score or full workflow acceptance.

Both owned fault controllers finished; the original is restored with its unchanged SHA256 and the worker locks are released. [Fault manifest](manifest.json), [reader fault manifest](reader-manifest.json) and [verification](verification.json) record the reversible actions, separate integrity-checked store backups and current result.

## Actual browser sequence

1. Explicit Extract on saved personal revision 6 queued one candidate while its worker lock was held. [Running before refresh](running-before-refresh.txt) retained the manual text. Browser refresh, reopening the task list and reopening the material restored [Extraction running](running-after-reopen.txt). No second Extract was used to resume observation.
2. The pinned original was made temporarily unavailable and the worker lock released. Automatic UI polling then displayed [Extraction failed, saved content retained](failure-after-reopen.txt), ending at saved revision 8. The exact original error was retained in the candidate.
3. Reloading the material with the original still unavailable retained the editable content. The pre-fix [reader evidence](missing-original-reopen.txt) exposed internal file paths and no direct read retry, prompting the scoped UI fix below. An HTML Go action only navigated the already-rendered document; it was not counted as a fresh source-availability check.
4. After restoring the source, changing the UI and refreshing it, a second bounded missing-original injection verified the [readable failure prompt](missing-original-after-fix.txt). On the original pane, [Retry reading original](reader-retry-unsaved.txt) remained usable while a new engineering note was unsaved.
5. After exact source restoration, Retry reading original loaded the [HTML reader](reader-retry-restored.txt). [The unsaved input](unsaved-input-after-reader-retry.txt) remained exact and was separately saved as personal revision 9. The candidate list remained one old merged attempt plus the same failed attempt; reading retry did not create extraction work.
6. A separate explicit Extract produced [an empty result](retry-empty-with-human-work.txt): one processed original range, zero usable ranges and one unresolved range. The manual text remained intact. [Comparison](empty-candidate-comparison.txt) exposed one conflict: current personal text versus machine Not present. Keep current and the separate application confirmation produced [personal revision 12](empty-candidate-kept.txt), Candidate resolved / current content kept, Content draft, and an explicit master-unchanged reminder.
7. Final Reload saved was attempted, but the next observed page was [Source Management System](navigation-after-reload.txt). Browser interaction stopped rather than redirecting that page. **A post-application revision-12 browser reopen is not claimed.** Current saved revision 12 was independently verified in its owning store.

All checklist/application clicks were engineering transition tests. No final content confirmation or real colleague review occurred. Existing automatic empty/failure results remain empty/failure.

## Implemented recovery changes

- Original-read errors give a concise explanation, retained-work assurance, Retry reading original and source-report entry. Detailed error text remains under Reading failure details.
- Read retry retains the original location parameters, has no dependency on a successfully loaded reader, and changes no draft or candidate. The existing request identity guards reject stale reader responses.
- Failed extraction cards give recovery advice; the failure describes the attempt, not a continuing claim about source availability. Older-input flags retain their existing priority. Raw errors remain available in Processing details under Recorded failure details. Failed attempts no longer offer candidate adoption through Compare / resolve.

Only first-party materials.js and its existing materials-ui test module changed. [Pre-change UI](materials-before.js) and [pre-change tests](tests-before.mjs) preserve the preceding checkpoint; inspect later edits before restoring either.

## Verification and remaining work

**190 frontend tests PASS**, zero failing/skipped cases: [final full frontend log](frontend-final-tests.log). The two new tests check reader-only retry at the same page with an unchanged dirty draft, and recovery advice with retained raw failure evidence. The prior 164-Python regression is unchanged backend evidence from the confirmation checkpoint; it was not rerun for this UI-only delta.

Read-only verification preserves all **7 pre-existing revision rows**, with **13 current rows** including version 0. Final personal revision 12 has content revision 3, no confirmation and no checked ranges. Original source binding and file hash are unchanged; candidate statuses are merged / failed / kept. The final code hashes are recorded in verification.json.

Remaining: the post-application reopen check noted above; integrated mixed-operation recovery after a candidate freeze; actual duplicate/delayed operations and assigned archive checks; remaining accessibility scope and Windows/colleague acceptance. The comparison currently labels a resolved deletion difference as Deletion / choice recorded even when Keep current was selected. The actual application retained the text, but that label needs clearer choice wording in the next manual-review checkpoint.

## Subsequent reopen and comparison-label checkpoint

The later isolated browser reopened [TS004 personal revision 12](revision-12-reopened.txt), retaining manual text, Candidate resolved / current content kept, Content draft and unchecked scope. This closes the earlier post-application reopen gap without changing that earlier observation.

Comparison headers now distinguish the proposed change from the selected outcome. An omission is labelled Candidate/Submission omits content; explicit retention is Selected: Keep current. Automatic suggestions do not claim human selection. Actual UI evidence shows [Suggested: Adopt submitted](choice-suggested.txt) becoming [Selected: Adopt submitted](choice-selected.txt) after the individual preview choice. No final master adoption was performed. The omission/retention branch has focused regression coverage, not an additional claimed browser observation. All **192 frontend tests pass** ([log](choice-label-frontend.log)); [binding](choice-label-binding.json) records this later code/evidence checkpoint. Backend remains at the prior 164-Python checkpoint.
