# Workbench User Guide

## 1. Opening and saving work

After the first installation, double-click the root launcher for your computer. Select your name before editing. The service is local to your computer; colleagues run their own installations.

Source Management retains the source register, originals, source versions, human decisions and unresolved work. Materials opens the existing four-pane workspace:

1. Original document and source location.
2. Continuously editable extracted content, with current text and changes views.
3. Requirement entries, source colours, fields, Groups, quantities and links.
4. Scope, Conditions, Demands and editable check-design logic belonging to the selected Requirement.

Registered HTML opens as a safe webpage reading view with headings, lists and tables. Existing links to a unique target within the saved document work, and declared alphabetic, Roman and reversed list numbering is retained. Source website styling and active controls are removed; preserved original bytes remain available separately. PDF search supports previous/next matches; clearing the query removes highlights. **Open reader** retains the current page, zoom and rotation. Invalid page or spreadsheet locations keep the current view and show the allowed range.

Spreadsheet continuation keeps already-read rows and the selected range if the next read fails; **Retry next rows** retries that window. Exact absolute cell references are supported. Version comparisons show changed passage order with stable identities and show differing human review declarations separately. Recorded table merges are displayed only when they preserve every stored cell; inconsistent merges retain the complete grid with an explanation.

In extracted content, **Current text** and **Changes** share the same page-memory Undo/Redo history. Table Tab/Shift+Tab moves through existing cells; a rectangular tab-separated paste fills cells from the current position. Cell and image-caption corrections retain their source and attachment details, table merges and notes. Use the row/column controls for structural table changes. Enter continues a list; Enter on its empty final item exits one level. These edits still need an explicit Save.

In Requirement Groups, checked items survive redraws and invalid quantities remain visible for correction. Linked Requirement choices show their full original wording before you link them. Combining source passages retains their original order, with a limit of 100 passages and 100,000 characters. **Save** at the top of the page retains incomplete splitting along with the other panes. Switching between Requirement entries retains each unsaved draft in page memory. The completion control at the bottom of the third pane checks every entry, including collapsed entries, for unfinished Groups, quantities and relationships.

The fourth pane follows the selected Requirement and shows only **Scope · A**, **Condition · B** and **Demand · C**, followed by their set relation. Each module displays **Combined extract**, a deterministic combination of the third-pane words, Groups and quantities, and its interpreted **Set**. The program does not infer Scope from the grammatical Subject or fill missing meaning. The set notation is `A = { x | scope }`, `B = { x ∈ A | condition }`, `C = { x | demand }`; the intended requirement is **B ⊆ C**, with B selected within A. These are definitions for a later assessment, not compliance results.

Linked concepts appear in double quotation marks inside the Set. Exact term matches keep the original wording and casing. Labels that do not occur in the text remain available in the editor; the display does not guess synonyms or add a separate concept list. Nested AND/OR/NOT is preserved. Click a Set to expand its existing rule/concept editor, or activate a quoted concept to inspect its exact linked meaning. Shared concepts keep one identity across their rules. **Review notes** inside that editor retains supporting information, quotations and open questions; shared object/period fields are in A's notes. Closing it does not save. Separate Evidence, More, concept lists and data-integration panels are removed from the reading view; stored evidence, mappings and history remain unchanged.

A prepared quotation and selected source stay in page memory until **Add citation**. Saving other edits keeps that quotation and reports it as still unsaved. Removing a Set rule offers one temporary **Undo removal**; restoring its content keeps any invalidated approval pending.

**AI Gen** requests all three candidate Sets together, including their supporting notes and proposed concepts, after provider configuration and context confirmation. Opening a Requirement never generates content. Each candidate remains separate until its own **Approve … candidate** replaces that module in the draft; **Dismiss candidate** keeps existing text. Manual and previously saved Sets have their own **Approve scope/condition/demand** actions. Expand the Set to inspect/edit its evidence and confirm concept meanings. Approvals remain bound to the exact card content and source context; changes invalidate affected approvals. **Save** records the draft and explicit approvals with reviewer/time, never grants approval by itself. The completion control at the bottom of the fourth pane checks all Requirements, not only the selected one. It requires saved current approvals, resolved review questions and confirmed concept meanings. API configuration remains in Settings; unavailable generation says **Not connected**. No schema, saved-record or external Site Model change is made by this presentation simplification.

Use the single page-level **Save** to save all edited content, Requirement entries and interpretation drafts. Per-pane Save buttons are removed; Ctrl/Cmd+S uses the same whole-page action. Unsaved edits stay in page memory. Page navigation offers **Save and leave**, **Continue editing**, and **Leave without saving**. The last action is disabled for three seconds as a strong warning; the countdown never saves or leaves automatically. A failed save keeps the page open. Browser tab close and refresh use the browser-native unsaved warning, which cannot support this custom countdown. Selecting text, resizing panes, expanding an entry and reading history do not create business revisions. Save, review, accept a suggestion and archive have separate meanings. Save does not mark processing complete. Confirm completion at the bottom of panes 2, 3 and 4; their 0?3 progress count describes the material. Archive requires all three current confirmations, enforced by the server. An upstream change invalidates affected downstream confirmations; reopening a stage also reopens downstream stages.

Whole-page Save uses the existing version-guarded owning stores. It saves interpretations against their original saved context before changed Requirements and content. Upstream edits can therefore make saved downstream work stale without losing or silently rebinding its human text. If a component fails, the page reports an incomplete save, retains saved parts and unsaved drafts, and retries uncertain requests with the original identities. Resolve malformed inputs, unadded quotations or source conflicts before leaving; there is no claim of an atomic transaction across stores.

If another saved interpretation is newer, **Compare saved and local** keeps both versions available. Explicitly reload the saved version or continue with your reviewed local draft, then Save separately. An uncertain AI Gen start offers a retry of the same request; **Retry status** reads the known generation without replacing your manual text.

The shell refreshes status every five seconds and waits for an unfinished refresh before starting another. Unsaved edits remain in the page during these updates.

**Runtime status** keeps an open component history and your reading position during refresh. If its read fails, the last successful report stays visible with its checked time and a stale-status explanation. **Retry status** only reads service status.

Saved Requirement and S/C/D work is visible to named colleagues in the same workspace. Each version retains its editor and time. If a saved Requirement changes, existing S/C/D keeps its original binding and asks for review; it is not silently rewritten. Preserve that distinction when explaining results.

The repository includes a [complete Norwegian law example with saved annotations](workbench/resources/examples/README.md). A fresh installation can restore its Example-only seed; an existing installation imports its scoped Collaboration package explicitly. Git updates do not overwrite your local source or material versions. The prepared annotations remain pending human review.

## 2. Collaboration between computers

All collaborators use the full local installation. Install the application, restore the supplied initial data once, and select your own reviewer name.

1. Save the work you want to share.
2. Open **Collaboration** and export the saved-work package.
3. Transfer the ZIP through your agreed channel.
4. On the recipient computer, import it in Collaboration and inspect the comparison.
5. Resolve conflicts explicitly, then confirm the displayed import.
6. Continue editing and export a new package when ready.

The package includes coordinated snapshots of four business databases, originals/attachments, derived human-history files, a manifest and a logical merge payload. The receiving application validates them and applies logical changes. **Do not replace your local database files with files from a colleague's ZIP.**

Incoming history retains the original authors and timestamps. Conflicting saved branches remain evidence; a choice determines which version continues locally. Repeating a completed import does not apply it twice. Interrupted imports retain progress and can be resumed. An incompatible package is rejected with an explanation rather than partially interpreted.

Legacy `full-workspace-snapshot/1` and `/2` packages retain their validated logical-import route. Older work/submission/collection formats keep their existing legacy routes; they are not accepted as full snapshots merely because they are ZIPs.

## 3. Fixed downstream delivery

In Collaboration choose **Export downstream delivery**. The resulting ZIP fixes the current saved versions and their necessary source evidence. It contains four SQLite files, human-history JSONL files and a manifest listing file hashes, schemas and bindings. Its README explains independent reading without running Workbench.

A delivery contains check designs, not measured `Satisfied` results. It cannot be imported as a Collaboration merge. Use a Collaboration export when another Workbench must continue the work.

Local copies are kept under `workbench/workspace/packages/`. History exports under `workbench/workspace/logs/<package-id>/` are derived from that exact snapshot; the databases remain authoritative. Do not edit exported logs to change saved history.

## 4. Settings and privacy

The shared API is configured in **Settings**. Only an explicit AI action sends the displayed material scope to the configured service. Unconfigured processing remains **Not connected**. You can complete the manual route without an API.

Private settings and credentials stay under `workbench/runtime/settings/`. Business packages exclude runtime settings, login sessions, caches and diagnostic logs. Originals and human work are business data: share a package only with intended recipients.

## 5. Updating the application

Close the running Workbench first. Ask your local Copilot to follow `AGENTS.md`, check for local code changes, and update the intended branch using a fast-forward update. It must preserve both `workbench/workspace/` and `workbench/runtime/`, and rebuild dependencies only when needed.

Do not restore initial data during updates, delete either local-data directory, or use Git reset/clean to resolve a local change. If an update asks for an explicit migration, follow [ENVIRONMENT.md](ENVIRONMENT.md). Reopen the same workspace and verify your saved work before continuing.

A useful local Copilot request is:

> Read AGENTS.md and ENVIRONMENT.md. Check this installation, update the application from the agreed Git branch without overwriting local code changes, and preserve all workspace and runtime data. Do not restore initial data or publish anything. Rebuild dependencies only if required and verify that saved work reopens. Report anything not verified on this Windows computer.
