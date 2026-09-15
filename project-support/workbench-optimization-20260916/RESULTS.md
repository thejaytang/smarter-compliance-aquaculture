# Workbench optimization | 2026-09-16

## Delivered design

The Workbench retains one shared service and API configuration. Each saved interpretation now has immutable relational links through its six fields, citations and optional rule nodes to the saved splitting step, Requirement ID, material revision, source version and passage coordinates. Existing JSON histories remain authoritative; additive indexed projections support joins and enforce parent ownership. Active Requirement relationships retain nested exact/range quantities without flattening them into AND/OR.

The optional `requirement-check-design/1` contract accepts bounded, typed AND/OR trees with explicit `table.column` mappings. It projects the documented QueryBuilder filter shape and links each leaf back to one interpretation field. This is an interchange design, not execution against a Site Model. Unknown mappings stay null; source prose never silently becomes SQL. Consumers must provide a field allowlist, joins, assessment/event context and evidence semantics. References: [SQLAlchemy QueryBuilder](https://sqlalchemy-querybuilder.readthedocs.io/en/latest/) and [jQuery QueryBuilder](https://querybuilder.js.org/).

## Human workflow

- Completed Requirement cards provide a direct Interpret action.
- The six formal text fields remain the main editing surface. Six basis selectors, six gap editors, citation tools and candidate panels are collapsed behind Evidence & gaps / AI assistance.
- Source trail is one action. It identifies the frozen extracted passage separately from original source metadata, with field citations and rule mappings.
- Save remains distinct from review; a sticky action area and Ctrl/Cmd+S reduce scrolling. Details and reading position survive rerenders. Drafts remain Requirement- and reviewer-bound.
- Optional rule editing supports nested groups, typed values and a live read-only QueryBuilder preview. Invalid values cannot be silently saved; correcting their type clears obsolete browser validation errors.

## Verification matrix

| Area | Automated evidence | Direct observation / boundary |
|---|---|---|
| Source intake, tasks and ownership | System1 full regression: 168 passed; Workbench source-intake, source-workflow, origin/HTTP suites | No live downloads, source checks or business decisions triggered |
| Materials, provenance, Markdown and review | System2 full regression: 1163 passed, 2 skipped; Workbench material HTTP/navigation/confirmation/Markdown tests | Original/current text/changes and existing annotations retained; no normal material content modified |
| Requirement splitting and annotations | Requirement lifecycle, exact/range nesting, cross-passage references, actor/revision/replay tests; Unicode/Markdown/overlap frontend checks | Existing finished card opens interpretation directly; four panes and collapse/restore remain usable |
| Interpretation and relational lineage | 245 Workbench tests passed, including new frozen source/history/retired-unit joins, orphan rejection, citation offsets, rule restore, actual HTTP authorization and read-only guards | Synthetic Scope and typed `staff.role in [farm_staff, manager]` saved; service restart/reload retained revision 3; keyboard save created revision 4; Source trail showed exact saved IDs/revisions/passage |
| Candidate generation and Settings | Local synthetic Chat Completions tests; candidate/formal separation, invalid citations, full context limits, stale/timeout, key exclusion | No real provider calls; normal API remains unconfigured |
| Collaboration, archive and recovery | Full Workbench merge, snapshot, package, reviewer, recovery, schedules and request suites | Collaboration ZIP still excludes splitting/interpretations; complete local database recovery includes them |
| Frontend interactions | Full Node regression: 278 passed, including validation recovery | 1280/1440/1920 browser widths; horizontal overflow confined to workspace; first-two-pane collapse, keyboard resize, source dialog and keyboard save observed |
| Windows | Branch CI runs Workbench backend/frontend and affected System2 material contracts on Windows and Ubuntu | Results pending. Native Windows desktop behavior is not established by CI |

System2 skips are the opt-in supplied real PDF preflight and native Windows peak-memory test on macOS. The full test commands use each component's own environment. Local logs are retained beside this report and are not product data.

One bounded design detector pass identified semantic field/outer-relationship borders and a warning accent. Semantic indicators implement the required global mapping and remain; the decorative warning accent was replaced by a full thin border. The final visual pass confirmed the simplified four-pane layout and source dialog. A subsequent native Chrome 200% check was interrupted by the locked Mac; the preceding four-pane delivery's successful 200% test remains historical, not fresh acceptance of these edits.

## Delivery status

Normal service 62742 now loads the implementation. Eight owning databases were copied while the service was stopped and writer reservations were held. All existing rows in every store were unchanged after activation; new lineage/index tables were additive and foreign-key checks were clean. Served UI assets matched source files, shared AI remained Not connected and automation stayed disabled. A final citation-bound check is pending the next controlled reload. GitHub portability checks remain in progress. No real AI quality, Site Model satisfaction result or native Windows desktop acceptance is claimed.
