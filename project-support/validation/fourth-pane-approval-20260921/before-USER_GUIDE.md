# Workbench User Guide

## 1. Opening and saving work

After the first installation, double-click the root launcher for your computer. Select your name before editing. The service is local to your computer; colleagues run their own installations.

Source Management retains the source register, originals, source versions, human decisions and unresolved work. Materials opens the existing four-pane workspace:

1. Original document and source location.
2. Continuously editable extracted content, with current text and changes views.
3. Requirement entries, source colours, fields, Groups, quantities and links.
4. Scope, Conditions, Demands and editable check-design logic belonging to the selected Requirement.

The fourth pane follows the selected Requirement in the third pane. It opens in a reading view with **Scope · A**, **Condition · B**, **Demand · C** and their linked concepts. Choose **Edit** to change rules, concepts or supporting information; nested AND/OR/NOT and quantitative or temporal wording remain intact. **Done editing** returns to reading without saving. **Evidence** brings together the third-pane wording, earlier explanations, quotations and identification or verification notes. Earlier prose-only records remain editable until you explicitly choose **Define logic**. The grammatical Subject is evidence, not an automatic Scope: a facility can be the scoped object while seawater temperature, depth and weekly frequency constrain Demand.

While editing, link local **Concepts**, **Relations**, **Properties**, **Events** and **Actions** to each rule. Names have stable IDs and a proposed/confirmed meaning status. Expand a term to edit its name/type, attach quotations, or confirm its meaning in context. Shared terms keep the same ID across cards. This does not bind them to an external ontology. Unconfirmed meanings remain in **Review questions** and block interpretation confirmation. **More** contains generation, source-context management and history. **Generate interpretation draft** requires an explicitly configured provider and context confirmation; compare and accept or dismiss each candidate card separately. Accepting a candidate does not save or confirm it.

The summary shows **B ⊆ C**: every applicable object selected from A must meet Demand in the same assessment context. **Check context** holds the shared object and assessment period; edit it in editing mode. **More → Data integration** holds Site Model identity/field mappings, QueryBuilder filters and the full set handoff. Mapping readiness is separate from semantic review and stays outside the everyday reading view. Unsupported predicates and NOT block their whole filter. **Confirm data mappings** is separate from **Confirm interpretation**. **Save draft** appends a version; confirmation requires resolved interpretation questions and concept meanings. Missing evidence is unresolved, and no compliance result is executed. Existing history and exact Requirement bindings are retained.

Use the relevant **Save** action to create a saved version. Unsaved edits stay in page memory. Leaving, reloading or closing may lose them and triggers the existing warning. Selecting text, resizing panes, expanding an entry and reading history do not create business revisions. Save, review, accept a suggestion and archive have separate meanings.

The shell refreshes status every five seconds and waits for an unfinished refresh before starting another. Unsaved edits remain in the page during these updates.

Saved Requirement and S/C/D work is visible to named colleagues in the same workspace. Each version retains its editor and time. If a saved Requirement changes, existing S/C/D keeps its original binding and asks for review; it is not silently rewritten. Preserve that distinction when explaining results.

The repository includes a [complete Norwegian law example](workbench/resources/examples/README.md). Follow its instructions to keep a separate permanent Example copy; Git updates do not overwrite your local source or material versions.

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
