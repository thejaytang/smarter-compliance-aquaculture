# Local Workbench User Guide

The daily entry point is [Open Workbench.command](../Open Workbench.command) at the root of `05_Working area of requirements side/`. Double-click it to start the local service and open the default browser; subsequent launches reuse the same service. Closing the browser does not stop submitted jobs. Select “Exit workbench” at the bottom left to stop safely. No login startup or operating-system background service is installed.

## Overview and navigation

The workbench serves the full Requirement workflow across System1, System2 and System3. Requirement overview presents source management, extraction review and semantic completion side by side. Each area shows its responsibility, connection status, pending count, key outputs and entry point. Unconnected metrics display “Not connected”; this does not mean zero tasks or completed work. System2’s “Open review demo” opens a separate demonstration whose activity is excluded from the production overview and weekly accuracy.

Weekly random-check accuracy compares the three systems over the latest five weeks. System1 details is collapsed by default. Expand it to see registered sources, pending sources, stored originals, included sources, source selections, pending reasons and source composition. These details use the same System1 snapshot and do not depend on Excel chart caches. Select a pending-reason bar or priority source to open the corresponding list. “Review sources” returns to the complete queue; “Show all” also clears filters.

Select a System in the sidebar to expand or collapse “Pending review” and “Review history”. System1 history combines named workbook records with browser receipts, showing each successful decision once. System2 and System3 have no production queues connected yet; their pages state this explicitly.

Counting rules: System1 counts sources, System2 counts extraction review items, and System3 counts semantic completion items. These are not added into a single pending total. System1 pending counts use source IDs. A source may have several issues, so reason bars cannot be summed to obtain the pending total. A stored original indicates storage only, not verified parsing or content.

## Weekly random checks

The workbench service schedules checks independently of Codex, personal accounts or a particular device. While running, it checks each minute for a missing current-week batch. Weeks follow Monday boundaries in Europe/Oslo, with five items sampled per connected system. No checks run while the service is stopped; on restart it creates the current week’s batch without fabricating checks for missed historical weeks. Preserve the production workbook and runtime when migrating the project so registered batches are not sampled again.

System1 randomly samples currently effective included sources with no unresolved tasks, excluding items still awaiting a previous check. If fewer than five are eligible, it samples all and records the actual count; zero eligible items produce an empty batch. Tasks appear under System1 → Pending review. Dashboard’s “System1 checks” opens the filtered list. Check the links, original and register details, then select “Correct”, or enter a note and select “Report an error”. An error creates a corrective task.

Dashboard shows the current week and four preceding weeks, with one line each for System1/2/3. Accuracy is correct items divided by the actual sample size. A point appears only after every item in the batch has a named, applied receipt. Incomplete, missing and unconnected results remain blank; the detail table retains progress and actual denominators. Equal values overlap, including three results of 100%. This is sample accuracy, not whole-register accuracy.

System1 is currently connected. System2/3 display “Not connected” until they provide production task and decision interfaces. No operating-system background task or Codex automation was created. Run this service on the deployment device.

## Daily operation

1. At the top right, select Ana Jokic, Daniel Restad or Weijie Tang, listed alphabetically by first name, then select “Use this name” or “Switch reviewer”. This identifies the operator on a trusted local machine; it is not password authentication. Switch names when the operator changes.
2. Select a System1 task and inspect the official page, registered retrieval link and local original. PDFs open in a full reader with paging, zoom, search and a separate-window option. The reader verifies the registered version and file fingerprint. HTML has a read-only text preview; open the original through the download link. Source scripts do not execute in the workbench.
3. When scoring is required, select H / M / L for each criterion. Light styling shows the previous score; dark styling shows this review’s selection. A previous score is not confirmation. All five selections trigger submission automatically. Scoring and original-file gates remain separate.
4. Deferring a source or removing it from scope requires a reason. Notes save automatically as drafts; saving a draft does not complete a decision.
5. Correcting a link saves register information only. It does not download a file or claim verification. After checking a reported issue, mark it verified, enter the evidence and record the verification result.
6. Replacement files are staged locally first. After the initial format check, a person confirms identity, completeness and usage permission before submitting acceptance. System1 validation and snapshot rules still apply. A format check does not prove regulatory identity or semantic completeness.
7. Recent submissions show submitted, applying, waiting for release, applied, needs attention or stale-page states. Processing waits while Excel is open and resumes after it closes. If the submission result is unknown, “Retry submission” reuses the original request ID. Stale or field-invalid decisions remain available; reload and check them again. A source-version change preserves note and corrected-link drafts while clearing confirmation of old scores.
8. Review history presents both named workbook history and browser requests. Complete sources and receipts are retained; the interface is not a second source register. Imported Excel reviews display the original ACCEPT / REJECT / INCORRECT result and notes. If the original has no review date, the displayed date is explicitly the synchronization time. Sources with remaining tasks show colleagues’ previous decisions and the unresolved reasons. An old ACCEPT does not backfill five-criterion scores.

Connected actions cover scoring, selection, link correction, verification of reported issues, replacement files and random checks for existing sources. A dedicated browser registration form for new source candidates is not implemented. Such candidates remain pending for the maintenance entry point; scoring must not be treated as candidate acceptance. System2 and System3 have no production tasks connected. System2 provides separate sample practice clearly labeled “Review demo”, described below.

## System2 review demo

System2 → Pending review uses the same vertical queue and search field as System1. Items display their source ID, title and pending status. Only unfinished and “Needs follow-up” items remain in the queue. Completed items move to Review history, where the original and decision details remain accessible. “Reopen sample” returns an item to pending review.

Five samples demonstrate PDF text checking, sentence joining, omitted tables, HTML list relationships and Excel header ownership. For PDFs, the historical source page and red box appear on the left, with zoom and full-page viewing. On the right, “Accept & next” or “Correct text” advances after saving. An omitted table records its scope and requests reparsing without requiring transcription of the whole page. Illegibility, omissions and reparse requests remain follow-up items, not accepted reviews.

“Screenshot does not match? Open full PDF” expands the full reader while preserving the draft on the right. “Choose PDF” selects the same original from the desktop and checks the PDF header and complete SHA-256. A matching file is displayed only in the browser and is not uploaded. Page buttons are English; the operating system controls its native file-dialog language. HTML and Excel are clearly labeled synthetic examples, retaining adjacent headings, headers and cell coordinates in the source panel.

Demo drafts and history are stored per operator in the current browser. Refreshing or switching items preserves drafts. Clearing browser data removes practice records; they do not synchronize across devices. The demo does not call production decision, parsing or upload interfaces and does not enter production history or Dashboard accuracy. See the [System2 demo contract](docs/system2-review-demo.md) for boundaries and provenance.

## File ownership

- `ui/`: browser interface.
- `src/local_workbench/`: HTTP service, operator/request storage, serial worker, environment adapters and launcher.
- `runtime/workbench.sqlite`: operators, sessions, note drafts, requests and receipts. This is persistent data that requires backup, not disposable cache.
- `runtime/uploads/`: staged files and source records. Retain pending files and failure evidence.
- `runtime/server.json`, `listen-port.json`, lock files and `service.log`: local runtime information, excluded from shared configuration.
- The System1 workbook and Data retain authoritative source business state. Excel opens the updated Instructions by default and exposes only Instructions, Categories and Source Register. Dashboard and Human Operation Desktop are `veryHidden` compatibility sheets preserving calculations and review history. Daily dashboards and human actions use the browser. Controlled saves maintain this layout; do not delete hidden sheets or rewrite formulas.

This component uses its own `.venv` and the standard library only. Follow the shared [environment guide](../ENVIRONMENT.md#system1-and-the-workbench-on-macos) to recreate the workbench and System1 environments on a new computer. Copying an environment directory is not a portable installation.

Validation commands, run in this directory:

~~~text
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
node --test tests/*.mjs
PYTHONPATH=src .venv/bin/python -m local_workbench --no-browser
~~~

Frontend state tests use the development machine’s existing Node.js; it is not part of the production Python environment.

The service listens only on `127.0.0.1`, preferring the previous port recorded in runtime and choosing an available port if occupied. A port change creates a separate browser storage space; demo records remain in the old space. POST requests validate Host, Origin, CSRF and the local session. Originals are not sent externally. Remote access, automatic downloading, external models, full parsing and publication are not authorized.

See [PROJECT_STATE.md](PROJECT_STATE.md) for current status and [Workbench design](docs/local-workbench-design.md) for design rationale. The shared operating rules are in [AGENTS.md](../AGENTS.md) at the `05` workspace root.
