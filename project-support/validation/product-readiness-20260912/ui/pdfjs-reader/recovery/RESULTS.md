# Original-reader recovery, 2026-09-13

**PASS for these bounded manual-reading scenarios.** This work follows the user's instruction to prioritize human review and stop further recognition-accuracy optimization. It changes neither extraction nor review decisions.

## Problems and correction

Before this change, the standalone reader displayed page 2 while its address retained opening page 3; refresh returned to page 3. The original source code retained here only reloaded the initial URL. A rapid next-page/zoom sequence also exposed PDF.js restoring an earlier visible location. Reading now updates only the current address's page, zoom and rotation. Explicit zoom/rotation preserves the selected page across the viewer's internal location update. Refresh and Retry reuse that location; source identity and view stay fixed. No search phrase or review text is stored in the URL.

An initial source failure previously exposed the internal request URL and suggested a Page image control unavailable in the standalone page. It now shows a plain recovery message, Retry, a real registered-original link and a Workbench link. Invalid material identity never requests a file. The Workbench footer link is hidden when embedded, preventing a nested-workbench navigation. Footer links wrap and retain visible keyboard focus.

## Actual browser checks

All source requests used public CS010 in the existing isolated fault fixture, with the existing reviewer session. No Extract, save, adoption, confirmation or business-store mutation was invoked.

- Page 3 → Next → page 4 → 150% zoom → refresh: page 4 and 150% remain after rendering settles. [Readback](page4-zoom150-refreshed.txt).
- Rotate to 90 degrees → refresh: page 4, 150% and rotation=90 remain. [Readback](rotated-refresh.txt). Display was then returned to 0 degrees and Fit width, retaining page 4.
- A temporary GET-only proxy injected an HTTP 503 for the original endpoint, while forwarding local reader assets. The UI showed the failure, disabled document controls and exposed Retry/Open original. [Initial failure](initial-failure.txt).
- After removing the fault and clicking the actual Retry button, the reader displayed the same source at page 3 and 125%, with normal reading controls and no failure banner. [Successful readback](retry-restored.txt).
- [Final screenshot](reader-confirmed.jpg) was visually inspected: correct original page content, source name, readable controls, page 4, Fit width and unobstructed footer links. It is a standalone reading observation, not full responsive/zoom acceptance for the three-pane workspace.

The first proxy recovery attempt omitted the existing reviewer cookie when forwarding to the same local fixture, so the upstream correctly refused personal-view access. [Failed harness attempt](retry-without-reviewer-cookie.txt) is retained. The proxy was corrected to forward that existing cookie locally without printing or saving its value. It did not weaken the product guard. Both proxy sessions were explicitly stopped; the temporary browser tab was closed. No normal service was stopped or restarted.

## Regression and loading

**164 Workbench Python tests and 184 frontend tests PASS**, zero failed/skipped frontend cases, with no source changes across [the regression freeze](regression-freeze.json). See [result](regression-result.json), [Python log](python.log), [frontend log](frontend.log), and the four focused cases in `workbench/tests/pdf-reader-recovery.test.mjs`. The focused mock deliberately moves to an earlier page during scale changes to detect the observed defect; it also checks source identity, invalid display parameters, failure controls and page-specific errors.

The three first-party reader files are served from disk and were actually reloaded at isolated 60905. No server route or vendor file changed. Older parents without PDF.js capability still use the image reader. No normal-business loading or colleague/Windows acceptance is claimed.

Exact preceding JS/HTML/CSS bytes and hashes are in [pre-change](pre-change/manifest.json). The CSS baseline was reconstructed by removing only the appended rule and verified against the prior frozen SHA before retention. A reviewed rollback replaces only these reader files, preserves all originals/history and is verified after reload.

Remaining: actual clipboard round trip, full three-pane keyboard/zoom/preference checks, complete manual-review scenario coverage, the integrated workload and colleague/Windows acceptance. This checkpoint does not make the overall goal complete.
