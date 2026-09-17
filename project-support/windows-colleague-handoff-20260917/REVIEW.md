# Windows colleague handoff review, 2026-09-17

Historical audit. The implementation and cleanup that address these findings are tracked in [the subsequent handoff result](../shared-workspace-20260917/RESULTS.md).

## 1. Decision and retained data

**Not yet ready for unattended colleague onboarding and application-only updates.** Local execution and explicit package synchronization exist. The application/data boundary, initial source-only package, and usable cross-author Requirement handoff still need work.

The user's clarification during this review is authoritative: existing Materials, splitting and interpretation records are development/test traces, not real work to retain in the initial delivery. Retain genuine **System1 source-management review**, its history and original dependencies. This is an export-selection decision, not permission to delete local stores. Source-related state and material-related state share parts of Workbench storage; do not discard an entire database based on its filename.

Reviewed executable commit: `0fae54eac5990a8229fb1f934358771aac7c6baf`; local HEAD at review: `cd6708b808c1c588e9715f839bb22a8a6f6b13d7`. Later commits contain verification documentation. Existing uncommitted update-milestone instructions remain intact. No code, live records, credentials, repository visibility, branch or release was changed by this review.

## 2. Findings

### 2.1 High: Git still owns mutable business files

`git ls-files` identifies 73 source HTML/PDF/XLSX originals under `system1/Data/`, the live `system1/Code/config/config.json` and `schedule.json`, and generated source/material workbooks. Runtime paths themselves are untracked, but this does not make the whole installation application-only. Normal source synchronization writes managed originals, and local configuration/output can change after installation.

Consequences: a pull can conflict with local work or update unchanged tracked configuration; removing tracked originals in a later application commit can remove those files from colleagues' checkouts. `.gitignore` does not untrack existing files. Evidence: [ignore rules](../../.gitignore), [System1 config](../../system1/Code/config/config.json), [source synchronization writes](../../system1/Code/src/system1/source_snapshot.py).

Required before app-only updates: establish an explicit local data/configuration home; migrate and verify retained originals and records before removing tracking; ship configuration templates rather than operational settings; add a tracked-data guard. Test an upgrade from the prior release with saved local edits, not just a clean checkout.

### 2.2 High: the current export does not match the initial-data scope

[SnapshotWorkspace.capture](../../workbench/src/local_workbench/snapshot_workspace.py) exports all saved materials and Requirement bundles as well as source records. The existing `Export full workspace` button has no source-only initial-delivery choice. Using it on the current development instance would deliver the user's unwanted Materials test traces.

The existing [System1 revision-8 archive](../../system1/saved-records/RESTORE.md) is a source authority recovery package, not a Collaboration import ZIP. Its referenced originals are separate files in `system1/Data/`. A reviewer-only installation cannot import that archive through `Import work`.

Required: prepare a source-only initial package from a verified isolated source snapshot, with a manifest, originals, review history and hash checks. Account separately for any source review proposals that are not applied decisions. Keep development Materials out. If offering both a full-installation seed and a reviewer import ZIP, label their different purposes and never let one be mistaken for the other. Initialization must refuse to overwrite an existing workspace and must not recur on application updates.

### 2.3 High for future joint annotation: imported Requirement work is inaccessible under the receiver's own name

[Delivery.apply](../../workbench/src/local_workbench/requirement_delivery.py) retains the exported actor, while [Requirements.listing/load](../../workbench/src/local_workbench/requirements.py) filter by the selected actor. An isolated reproduction imported Weijie Tang's saved Requirement and interpretation into a second SQLite store: import returned `synchronized`, Weijie Tang saw one Requirement, Ana Jokic saw zero, and her interpretation read returned `Requirement is not available to this reviewer.` The current Collaboration text recommends using the original reviewer to resume it.

This preserves author isolation, but does not implement another person continuing the same work under their own identity. Switching identities is not an acceptable authorship solution. The finding no longer blocks retention of the current Materials, which the user excluded, but it matters before real collaborative annotation begins.

Required: an explicit received-work view and a source-bound continuation/contribution action under the actual reviewer, retaining origin and ancestry. Do not fix this by dropping actor checks. Include two different reviewers in the round-trip acceptance scenario.

### 2.4 Medium: new Requirement conflicts fall back to raw JSON

[global-settings.js `displayValue`](../../workbench/ui/global-settings.js) handles only `requirement-delivery/1` as a readable Requirement summary. Both `/2` (groups) and `/3` (relationships) fall through to JSON. Direct rendering confirmed `/1` gives a summary, `/2` and `/3` give `<pre>` JSON.

[snapshot_graph.compare](../../workbench/src/local_workbench/snapshot_graph.py) also treats each reviewer's entire Requirement bundle as one atomic choice for concurrent changes. Concurrent work on separate Requirements under that identity can require choosing a complete bundle. Historical versions are retained, but that does not provide a usable merge for nontechnical colleagues. Add readable source/field/group comparisons for supported versions and explicit conflict boundaries; do not silently flatten quantities or relationships.

### 2.5 Medium: setup, profile and update steps remain maintainer-oriented

Windows launchers exist and component environments are portable. Setup still requires Python 3.12 plus `uv`, reports missing prerequisites in a console, and there is no guided update/rollback entry. `Rebuild environments.cmd` is dependency setup, not an application updater. [The launcher](../../workbench/src/local_workbench/__main__.py) detaches the local service; closing the browser alone does not stop it. **Exit workbench** is the actual stop action.

Reviewer mode isolates local data and suppresses coordinator workers, but cannot execute governing source decisions/retrieval/jobs. Full mode owns those functions and starts its worker loops. These profiles must not be presented as interchangeable. Publish one explicit colleague profile, prerequisite checks, persistent failure messages, backup-before-update, compatibility/migration checks, restart and verification. Do not copy a coordinator's active jobs/schedule intent onto every colleague computer.

Remote verification found the repository **public**, default branch **main**, and the current development branch **42 commits ahead** of main (`95ca3903ea172357208ddc2f247b700c4a50d432`). A plain default clone does not select this implementation. A maintainer must select the tested release/update channel at a publication milestone. No merge was performed.

One-time data distribution should be a separately identified initial asset, followed by application-only updates. Removing data from the current branch later does not retract public Git history, existing release assets or colleagues' copies. No change to visibility or history is part of this audit.

## 3. Source preservation evidence

Read-only SQLite queries used an explicit read transaction. No live database file was copied.

| Item | Retained checkpoint | Current local authority |
| --- | --- | --- |
| Revision | 8 | 13 |
| Sources | 88 | 88 |
| Operations | 136 | 137 |
| History rows | 232 | 240 |
| Artifact identities | 74 | 76 |
| Source-version links | 71 | 73 |
| Named assessment holds | 4 | 4, identical rows |

The archive checksum matches its committed checksum file. All three packaged files match their manifest hashes and sizes; all 71 referenced original files are present and match their expected hashes. Comparing checkpoint/live rows found only `PE001` changed in Sources, one changed and one added operation associated with that example, and eight appended history rows. All original history rows are identical and none are missing. Revisions 9–13 concern PE001; the non-example source rows are unchanged. Therefore the lower archive revision does **not** establish loss of real source review.

There are no `source_draft` records in the current collaboration journal. There are three source-task proposal records associated with example/intake work, and ten legacy source-review draft rows, one with nonempty note/score content. Their business status was not reclassified from storage alone. The retained revision-8 archive covers applied System1 authority and named holds; it does not include those legacy Workbench rows. Preserve them locally and classify source-related proposals explicitly when constructing the seed. No material database should be copied wholesale into that seed.

## 4. Verification and limits

- 59 targeted Workbench tests passed: full snapshot graph, conflict/replay/interruption behavior, package validation, identity, interpretation continuity, Group relationships, environment rebuild and platform helpers.
- 46 frontend tests passed: peer settings, collaboration comparison/order/relationship interactions.
- 20 System1 checks passed when loading the source-snapshot test module (including its imported fixture suite): stale input, replay, protected originals and source/save failure behavior.
- Two direct isolated reproductions confirmed the cross-author visibility limitation and version-2/3 raw-JSON conflict display. Passing existing tests therefore does not mean the requested workflow is complete.
- The earlier [Windows Server 2025 CI run](https://github.com/thejaytang/smarter-compliance-aquaculture/actions/runs/35160637346) passed the same executable commit. This review did not run a new Windows desktop installation, upgrade with saved data, or physical two-computer round trip. Current targeted tests ran locally on macOS.
- No real model request, live material export, data deletion, commit, push, merge or release publication occurred.

## 5. Recommended release gate

1. Build and verify the source-only seed without Materials development history; include the correct source proposal scope and referenced originals.
2. Separate mutable data/configuration from tracked application files and complete a safe migration before a code-only release removes tracking.
3. Provide the chosen Windows setup/profile and guided update path; document one release channel. Preserve local work through a previous-to-next-version upgrade.
4. Resolve cross-author continuation and supported-version comparison before real joint Requirement annotation.
5. Exercise two isolated, differently named Windows users: install, import the seed, save independent source/material work, exchange, resolve conflicts, reimport, restart, update code, then verify saved work, history and original hashes. This is the acceptance gate, not another claim based on unit tests.

The [colleague guide](../../workbench/docs/windows-colleague-guide.md) and [Copilot repository guidance](../../.github/copilot-instructions.md) are prepared locally. They identify pending release steps rather than advertising a completed installer. Future uploads remain user-controlled milestones.
