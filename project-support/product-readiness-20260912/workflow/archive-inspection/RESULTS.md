# Assigned archive inspection: progress and finding recovery

2026-09-13. **PASS for saving/reopening progress, recording/reopening a finding, and preserving the archived acceptance.** This is an engineering browser check on isolated reviewer `http://127.0.0.1:58814/`, copied public PA001 and the existing engineering-only task. It is not business review, a whole-document pass, finding resolution, or full scenario-7 acceptance.

## Actual interface evidence

The assigned task opened against archive revision 2. [Opening](opened.txt) showed its reason, assigned reviewer and complete-HTML range. Saving a note with both checkboxes clear produced “Spot-check saved. Archive unchanged.” ([saved](progress-saved.txt)). Browser refresh, Open materials and the task button restored the exact note, one history entry and unchecked scope ([reopened](progress-reopened.txt)).

The original reader visibly reported “Image unavailable in offline snapshot: Lovdata-logo”. Record a problem stored that exact resource/location limitation, without certifying the complete HTML range. The task became finding open ([saved](finding-saved.txt)). Archive still displayed accepted revision 2 and its original confirmation timestamp, `2026-09-12T21:17:46.947038+00:00` ([archive](archive-retained.txt)). Opening the finding again restored the exact note and unchecked range ([reopened](finding-reopened.txt)). Expanding Check history exposed the separate save and finding actions, both bound to archive revision 2 ([history](check-history.txt), [browser capture](finding-history.png)).

## Preservation and recovery

[Before manifest](before.json) identifies three integrity-checked SQLite backups. [Read-only verification](verification.json) compares all material tables in personal and master stores: every row remains identical. Among existing collaboration objects, only the assigned inspection changed; it now has revision 2, finding_open, zero checked ranges and two history entries. The imported archive payload and existing receipts remain unchanged. No original files, algorithm, master version or service were changed.

Recovery backups are evidence, not instructions to overwrite newer work. If rollback is needed, stop only the owning isolated reviewer and reconcile later task actions before using the named backup. Never restore these engineering stores over business data.

## Remaining gate

The observed missing-resource limitation remains open. A pass or resolution cannot be inferred from saved progress or a finding. A bounded fully reviewed fixture still needs the actual explicit pass/resolution branch, including a guarded current-version check; task-result package return and acceptance remain separate. Windows and colleague usability are unmeasured. No new regression run is claimed for this observation-only checkpoint.

## Stale inspection recovery blocker and repair

Two actual reviewer tabs opened task version 2. The first saved; the stale second save was rejected with “Spot-check changed. Reopen it before saving.” The task reopen then demanded saving first, leaving no usable reconciliation route ([stale save](conflict-before.txt), [blocked reopen](conflict-reopen-blocked.txt)). This is a core recovery blocker admitted to fixed closeout C2, not discretionary polish.

The repaired UI exposes Compare saved check. It shows the newer saved note, the local note, check versions and checked scopes. An explicit reviewed combined note opens unsaved progress against the newer version; range checks and final declaration reset. Closed/assigned-away tasks remain nonwritable. Same-material Reload saved now obeys unsaved-inspection protection.

Actual repair verification loaded the frontend in two pages. After the first saved task version 4, the stale page retained its input on Save and Reload saved ([guard](conflict-reload-guarded.txt)). [Comparison](conflict-comparison.txt) displayed both notes and required the checkbox. [Opening the combined result](conflict-combined-unsaved.txt) reported not saved; a separate Save succeeded ([confirmation](conflict-save-confirmed.txt)). Reopening restored both concurrent markers at task version 5, finding open, with no checked ranges ([reopen](conflict-reopened.txt)). The original pre-repair stale note was retained in its evidence and browser until its full text was present in this saved combined note.

[Preservation](conflict-verification.json) confirms unchanged personal/master material tables and retained inspection history. [Pre-conflict recovery](pre-conflict.json) has three additional integrity-checked stores; exact preceding frontend files are siblings prefixed pre-conflict. Focused recovery tests and all frontend checks pass ([focused](conflict-tests.log), [full](frontend-closeout.log)). The repair belongs to frozen local-delivery-rc1; full integrated acceptance is separate. No backend/service restart, business decision or original change was made for this repair.


## TS002 explicit pass and task-result return

Candidate local-delivery-rc1, isolated coordinator 55542 and reviewer 58814. Existing engineering TS002 was compared to its saved original (A1:C2 merge, B3=12, C3 formula `=B3+1` with unavailable cached value, Z105, empty and hidden sheets). The previous personal revisions remain history. Explicit candidate application and separate master adoption/confirmation created engineering archive revision 2; no real business material was confirmed.

Assigned check `3014718c-83dc-442f-97d6-061b75fb4e24` covers only Empty sheet. Its actual downloaded work package was imported into the reviewer workspace. The original was opened there and the empty range checked; **Pass selected checks** saved a passed task ([original](ts002-reviewer-empty-original.txt), [passed](ts002-reviewer-passed.txt)). The returned result was downloaded, matched byte-for-byte to the frozen artifact, and imported through the coordinator UI. It remained pending until [explicit comparison and adoption](ts002-task-return-comparison.txt); the [receipt](ts002-task-return-adopted.txt) preserves contributor and adopter. This does not confirm other ranges or Requirement structuring.

A later click on the same adoption action returned the existing decision. Every receipt, inspection and collection object remained identical ([delayed replay](delayed-task-replay.json)). Archive revision 2 remains visible in both workspaces. Package provenance is recorded in [work package](ts002-work-package.json) and [returned result](ts002-return-package.json). Finding resolution and returned table conflict remain separate pending checks.


The separate injected TS002 follow-up was recorded as a finding, then opened against the current master revision 2. The displayed formula/warning and previously checked workbook scope showed that the suspected calculated value was not present. A new evidence note and explicit range/final checks saved **resolved**, with two history entries ([actual UI](ts002-finding-resolved.txt)). This is a deliberately injected recovery scenario, not a discovered extraction defect or a new accuracy result. The accepted archive remains revision 2. C1's pass, resolution and task-result return are now locally verified; independent colleague/Windows acceptance remains later work.


## Returned table conflict and reduced-preference keyboard path

Actual TS002 reviewer revision 3 deliberately changed B3 from original 12 to engineering input 13. A separate coordinator revision adopted engineering input 14 without content confirmation. The [downloaded table package](ts002-table-package.json) was imported through the UI. The [comparison](ts002-returned-table-conflict.txt) showed two unresolved conflicts (cell and notes), kept the master unchanged and disabled adoption. Explicit edited results set B3=12 and retained both contributors' test rationale in notes. Separate adoption saved master revision 4, still requiring review; [adopted](ts002-table-adopted.txt) and [reopened](ts002-table-reopened.txt) show the retained formula, warning and merged notes. Both earlier inputs remain in history. [Preservation](ts002-preservation.json) verifies all 40 pre-existing material revisions at the pre-pass checkpoint and the passed/resolved task histories.

The same conflict path was completed with macOS reduced-motion and reduced-transparency enabled, confirmed by browser media queries. Enter opened the cell editor, keyboard input supplied 12, Tab exposed visible focus, Enter saved the preview, and Space/Tab/Enter explicitly adopted it. The [dialog screenshot](reduced-preferences-adopt-dialog.png) shows unobstructed controls and readable text; [record](reduced-preferences-keyboard.json) binds the preferences/actions. Both system preferences were restored to their original off state and browser queries confirmed false.

Actual browser zoom remains **UNMEASURED**. In-app and Chrome shortcut attempts did not change the measured zoom. Native Chrome accessibility IDs repeatedly expired and its coordinate fallback reported no window; that method was stopped. [Tool limitation](browser-zoom-limitation.json) retains the facts. Narrower viewport testing is not counted as browser zoom, and this missing required local check prevents declaring the local trial gate reached.

## Rc1 post-restart UI readback

Actual background in-app browser control remained available despite the native Mac lock. On the already restarted rc1 coordinator 55542 and reviewer 58814, Pending materials reopened TS002 with the correct named actor. Coordinator [personal revision 4](rc1-restart-coordinator-personal.txt) and explicitly opened [master revision 4](rc1-restart-master.txt) show B3=12, both earlier inputs in the reconciliation note, and only 2/3 ranges checked. The master is read-only and unconfirmed. Reviewer [personal revision 3](rc1-restart-reviewer-personal.txt) still shows B3=13 and its separate note; the original remains B3=12. No save, adoption or confirmation was triggered by these reads.

Both [coordinator archive](rc1-restart-coordinator-archive.txt) and [reviewer archive](rc1-restart-reviewer-archive.txt) show accepted revision 2, its earlier confirmation and 3/3 checked ranges. Expanded [inspection history](rc1-restart-inspection-history.txt) retains Ana's passed task and Weijie's resolved task against archive 2. The [actual receipt dialog](rc1-restart-adoption-receipts.txt) retains the adopted task result and separate material adoption at revision 4 with Review In Progress, explicitly distinguished from content confirmation. This completes C4's final post-load UI readback, reusing the frozen-candidate regression, mixed-workload and recovery evidence. No product code changed. C3 real browser zoom remains the sole local checklist blocker.

## Final actual browser zoom acceptance

After the user unlocked the Mac, native Chrome View > Zoom In and application shortcuts successfully changed the actual browser zoom from 100% to 200%. Native UI reported 200%; devicePixelRatio changed from 2 to 4 and the CSS viewport from 1470×779 to 735×389, without a viewport override. [Recorded measurements](browser-zoom-pass.json) supersede the earlier control limitation for C3; earlier failed attempts remain retained.

At 200%, the isolated reviewer opened TS002, expanded the workspace, switched Original/Content panes, read original B3=12, and edited the existing personal B3 value back to exactly 13. The ordinary textarea accepts Enter as text; that transient newline was removed before saving. [Original](zoom200-original.png) and [editing](zoom200-edit.png) captures show the usable scrollable surfaces. Save produced personal revision 4 and explicitly stated that saving does not confirm content ([saved](zoom200-saved.txt)). [Reload saved](zoom200-reopened.txt) retained 13, the original formula-warning/conflict note and 2/3 checked ranges. No master adoption or human confirmation occurred.

The independent confirmation dialog remained readable and scrollable. It identified the unchecked range and disabled completion ([top](zoom200-confirm-top.png)). Keyboard Tab reached Close with a visible 2px focus outline and scrolled it into view ([bottom](zoom200-confirm-bottom.png)); Enter closed the dialog without a confirmation. Expanded view exited successfully. Chrome was restored to 100%, confirmed by native UI and the original viewport/devicePixelRatio, and only the agent-created test tab was closed.

C3 is PASS for the fixed key-task scope, combined with the existing keyboard, actual reduced-preference and matched-width evidence. No product code changed, so candidate rc1 and the applicable C1/C2/C4 regression evidence remain valid. The final isolated reviewer save is later than the stopped recovery checkpoint; preserve newer saved work before any restoration. The local C1-C5 checklist is complete. This is not automatic extraction-quality, real colleague, Windows or formal-deployment acceptance.
