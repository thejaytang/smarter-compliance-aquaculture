# Windows colleague guide

## 1. The two channels

- **GitHub `main` supplies the application**, its tests, dependency declarations and instructions.
- **Collaboration exchanges saved work** between local installations. Use your own name. Received Requirement decomposition and interpretation are visible and editable by every named reviewer. Saved history records the editor and time.
- Each computer keeps its own databases, originals, settings and Collaboration history. Collaboration is ZIP exchange, not a live shared server. Unsaved browser edits are not included.

## 2. First installation, once only

1. Clone `main` into a short local folder, such as `C:\Users\YourName\Aquaculture`. Keep this clone for subsequent updates.
2. Give your local agent or IT helper [ENVIRONMENT.md](../../ENVIRONMENT.md). Install Python 3.12 and `uv`, then run `workbench\deployment\Rebuild environments.cmd`. It recreates the component environments from declared dependencies. It does not start the app or change existing data. Node is needed for frontend development/tests, not daily use.
3. Download `source-initial-data-20260917.zip` and its checksum from the [one-time initial-data release](https://github.com/thejaytang/smarter-compliance-aquaculture/releases/tag/initial-source-data-20260917). The release also provides `windows-environment-kit.zip`, a copy of the rebuild scripts, dependency declarations and instructions to use with this application clone. It is not a prebuilt Windows virtual environment and needs access to package repositories.
4. **Before the first launch**, have the helper run from the repository root:

   ```powershell
   py -3.12 workbench/deployment/restore_initial_data.py "C:\path\source-initial-data-20260917.zip" --sha256 e24c566133f8829688017ddac01ffb61e7f2bdbac7ce62560f80329c71e8267b
   ```

   Success reports `restored` and source revision `13`. The script verifies every package entry and refuses to overwrite an existing workspace. The package retains source review and required history/originals; it contains no Materials annotations. It is an installation package, not an **Import work** ZIP.
5. Open `workbench\deployment\Open Workbench.cmd`. Select **your own name**. Confirm the source register is available and Materials begin as **Not extracted**. New local configuration leaves automatic schedules off.

Keep the initial data package separately. Never restore it over later work. An existing development clone predating this separation needs a backup before pulling this milestone: Git removes formerly tracked original/config/output files from that old checkout. Preserve those local files first, then restore the preserved files after updating. This migration concern does not apply to a fresh clone of the separated version.

An optional isolated reviewer installation still uses `Open Reviewer Workbench.cmd` and a Collaboration ZIP supplied by the team. It does not restore the full source seed or run coordinator jobs.

## 3. Daily work and Collaboration

1. Save your edits explicitly. Unsaved work remains in the browser and can be lost on leaving.
2. Open **Settings → Collaboration → Export full workspace → Download full workspace**. Send this ZIP through the team's agreed channel. Keep it outside Git.
3. To receive work, select **Import work**. Compare conflicts and choose **Keep this version** or **Use imported version**, then **Confirm synchronization**. Both versions remain in history. Group comparisons show fields, source text, quantities and links.
4. Inspect **View synchronization history** and the affected records. Import does not complete review. Use **Refresh comparison** if saved work changed after preview; use the unfinished-import entry if interrupted.

Third/fourth-column saved work is shared within the local workspace. Each save records the actual editor. Source-version and concurrent-save checks still apply. Source content working copies remain versioned; if the selected content differs from the annotation's source, reconcile it before editing that annotation.

All collaborators should update before exchanging new shared Requirement packages. Older private Requirement bundles can initialize an empty Requirement workspace; merging them over existing shared work requires re-export from the updated app. Do not switch identities as a workaround.

## 4. Application updates

1. Save, export a Collaboration copy, and choose **Exit workbench**. Closing the browser tab alone leaves the service running.
2. In GitHub Desktop, choose the same clone and `main`, then **Fetch origin → Pull origin**. If there are local code changes, retain them and ask your local agent to merge them. Do not discard them or replace the whole folder.
3. Run **Rebuild environments.cmd** when the release changes dependencies. Existing local settings are preserved; initial data is never restored during an update.
4. Reopen Workbench and inspect your known source records, saved annotation and Collaboration history.

For developers: Mac development → Windows validation/small fixes → commit and push application changes → colleagues pull `main`. Keep production data and credentials out of commits. CI exercises Windows backend/frontend contracts; actual Windows pointer, scaling and office-to-office use are separate acceptance checks.

Never use `git reset --hard`, `git clean -fdx`, whole-folder replacement or database deletion as an update procedure.

## 5. Asking an agent for help

GitHub.com's chat sidebar can explain repository instructions; it does not itself operate your Windows computer. A local agent can perform setup when installed and authorized. Paste this request into the appropriate chat:

> Read AGENTS.md, ENVIRONMENT.md, PROJECT_STATE.md and workbench/docs/windows-colleague-guide.md. Help me install or update the Workbench on Windows, one step at a time. First distinguish a fresh installation from an existing workspace. Preserve my local source records, annotations, original files, configuration and Collaboration history. Use Python 3.12 and the shipped rebuild scripts. Restore initial data only into an unused installation; never during an application update. Do not reset/clean the repository or upload business data to GitHub. If you cannot access my local computer, explain the exact buttons or commands and what success looks like. My question is: [question or short error message].
