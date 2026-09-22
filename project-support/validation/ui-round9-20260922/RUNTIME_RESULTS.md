# R9 runtime report continuity

R9-01/02 implemented and independently reviewed. The existing material-navigation suite passed **20/20**, including a failure/retry, pending-read deduplication, reordered/removed-component, focus and disclosure regression. The full frontend suite run at R7 handoff included this change and passed 483/483.

Direct Chrome checks on the isolated fixture confirmed:

- A failed first read shows no invented component health, with Retry status and Close available.
- Opening the source component's retained failure and refreshing preserved that disclosure and the Refresh focus.
- A subsequent read failure kept the last successful checked time and report, explicitly labelled as possibly out of date.
- A scheduled background read advanced synthetic read 5 to 6 while keeping focus on `history:source` and the source disclosure open.
- A deferred read kept the last report visible, displayed Reading status and exposed `aria-busy`/`aria-disabled`; the automated check confirms repeated activation sends one request.

Only `/api/runtime-status` is simulated, with no service operation or business write. Native 200% zoom remains unverified while the Mac is locked. Reproduce with `workbench/.venv/bin/python project-support/validation/ui-round9-20260922/runtime_fixture.py`, then open the printed loopback address. This fixture is separate from the remaining eight R9 settings items.
