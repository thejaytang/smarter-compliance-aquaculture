# Checkpoint 45: source-first reference collection in the shared workbench

Decision: **CONTINUE** with the assessment and receipt boundary. Source-reference drafting is now implemented and exercised through the actual shared workbench against an isolated development store. Complete-reference confirmation and revision have engineering transaction coverage; an actual independent human reference and a browser confirmation of a complete reference remain unverified. The PDF quality goal stays active.

## Implemented behavior

System2 Content proofreading has a **PDF reference samples** entry. A task starts blank from one governed original PDF page, with at most two supporting pages. It does not preload extracted text, detected regions or verifier answers. The full original remains visible, including areas without an output record. A reviewer can enter original regions, text, tables and cells, spans, notes and typed relationships, and use either page coordinates or the implemented drawing control. Original magnification stays inside the left pane; the reference form is on the right.

Drafts, confirmed candidates and full before/after history belong to System2's database. Tables are created transactionally only when a reference task is explicitly created; merely opening the reference list does not migrate normal state. Named session identity, source eligibility and bytes, page bounds, revision guards and request replay protect writes. Saved receipt replay remains available even when the original subsequently becomes unavailable; a new write still needs a current governed original. Reads use a consistent database snapshot.

Incomplete editor text can be saved without pretending it is a finished region. Unfinished forms, incomplete table grids, unresolved surveys, missing text, invalid positions, unknown exposure and inconsistent relationships prevent confirmation. A saved candidate cannot be edited in place: a reasoned revision preserves its earlier answer and marks dependent assessment stale. Old local drafts with a different saved version retain a separate comparison copy instead of being overwritten by current-version edits.

Every task is currently `development` and `unqualified`. `reference_saved` means **Reference saved · assessment pending**, not extraction accepted or independently qualified. Engineering fixture origin is assigned by the isolated runtime, not accepted from browser fields. The current approved reviewer roster is unchanged. Reference activity uses its own history and does not emit A/B delivery events or initiate an Excel rewrite. Ordinary repair and delivery remain separate business operations.

## Actual browser experiment

The service used the actual Workbench Handler, UI modules, System1 read adapter and System2 subprocess adapter. Its runtime was `workbench/runtime/pdf-reference-pilot`, seeded with the already exposed 48-unit CS004 development window and paused. System1 operations were read-only; the fixture allowed only reviewer selection and reference submissions, with no workers. Its explicit engineering banner and temporary **Engineering validation** identity avoided representing test actions as real human review.

On PDF pages 19 and 20, the browser exercise:

- Created a blank page-19 task with page-20 context.
- Saved unfinished text, then observed confirmation refusal with the text retained and the form still editable.
- Entered a heading, a table, a footnote and one table cell, with footnote and cross-page context relationships.
- Used page selection, numeric coordinates, reference-only highlights and 150% magnification.
- Saved the explicitly partial engineering draft and reopened the browser. Four regions, two relationships, cell fields and unresolved text survived.
- Attempted confirmation again. The incomplete table was refused, with an actionable message; revision stayed 3 and history stayed at the three successful create/save/save events.

The [browser observations](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/browser-observations.json), [saved draft](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/reference-task.json) and [history](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/reference-history.json) bind this limited claim. The entered draft is an engineering interaction example, not a complete transcription or a quality label. It was deliberately left unfinished. Pointer drawing is implemented and its coordinate mapping unit-tested, but the actual browser exercise used numeric coordinates. Mobile layout, actual human effort and a complete-reference browser confirmation were not tested.

## Failures and adjustments

Initial fixture seeding lacked document defaults and rolled back; the isolated seed was repaired. Initial tests supplied the actor twice in a helper, which was corrected before the passing run. A fixture-only banner placed as an additional body child broke the page layout; moving it inside the workspace restored the normal layout. The nested task queue also made the two comparison panes too narrow, so reference mode now places its task list above the comparison. Final inspection at 1280 × 720 had no horizontal page overflow or browser warnings/errors.

Review also identified local stale-draft replacement and receipt replay after source loss as avoidable recovery gaps. Both were fixed and have focused regression coverage. This was one productive implementation checkpoint, not another attempt to infer PDF accuracy from the same method.

## Validation and preservation

- Full System2 suite: **803 passed, 1 existing skip**, with the existing Starlette/httpx deprecation warning. Sixteen reference transaction controls cover drafts, confirmation/revision history, table spans, cross-page notes, malformed inputs, owner/source/guard protection, rollback and receipt replay.
- Workbench suite: **29 passed**, including actual HTTP session identity, forbidden client fields, host/origin/CSRF boundaries and reference reads/writes without policy or Excel side effects.
- Frontend suite: **23 passed**, including draft retention, status semantics and reverse-direction/bounded coordinate mapping.
- The isolated business comparison retained documents, 48 source units, dependencies, ordinary events/history, policy, weekly state and deliveries unchanged. Only reference tables, their sequence and successful request receipts changed. See [the comparison](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/isolated-business-after.json).
- The [normal preservation check](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/preservation.json) matched all 18 tables in two normal stores, 73 managed files and 51 retained Gold files against the checkpoint-41 baseline. No source decision, threshold, scheduler, provider or normal A/B decision changed.

The [artifact manifest](../../outputs/runs/pdf-verifier-reliability-20260910/cp45/artifact-manifest.json) includes frozen verified code and test logs. No new dependency, external model, source discovery or full-document parse was used. Temporary test service cleanup does not remove its retained database/evidence. The pre-existing normal Workbench service was not restarted; the new server routes need the updated application on its next normal restart. This checkpoint does not claim a live normal-service deployment.

## Next bounded experiment and necessary inputs

Bind a saved reference revision to frozen effective records and the matching verifier report, then support extraction-error inventory and finding adjudication in the same workbench. Keep the source-first pass separate from later displayed machine answers. Test exact bindings, completeness, omissions with no output/alarm, false alarms, duplicates, location judgments and stale-reference invalidation. Exercise the complete-reference confirmation/revision browser path using an explicitly engineering-only controlled case before claiming that interaction is verified.

An actual independent reference owner, qualifying real scanned-body material, separate calibration/held-out source families and user release thresholds remain unresolved. Source-first collection is necessary preparation; it does not resolve those inputs or establish extraction/verifier precision, recall, human burden or automatic release quality.
