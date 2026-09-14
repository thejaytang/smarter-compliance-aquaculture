# Source workflow revision, 2026-09-14

## Delivered behavior

- Add sources expands into selected nested sidebar pages: Official website, Upload file and Source discovery routes. URL-only intake fetches a public original and proposes metadata before staging a pending candidate. File intake requires an explicit Parse file action; suggestions stay editable and re-parsing preserves edited fields. An official URL is optional for a validated uploaded original. Remove file (×) resets the upload form. Leaving a subpage or module clears unsubmitted intake fields/files and collapses manual details. Source-review and material draft protections remain separate.
- Source discovery separates registered-URL file comparison from API-backed expansion. API discovery remains Not connected. Update checks report changed/unchanged/skipped/failed, preserve originals and request re-review for changed files. A file hash change is not a legal-version judgment; this is not a whole-web search.
- Review needed supports trigger-type filtering (including secondary tasks) and ID/type/age sorting. Pending-Include represents human INCLUDE intent with pending effective eligibility. Open source re-review/replacement tasks block downstream INCLUDE; routine QA alone does not. Automatic recovery cannot close the human re-review gate; consolidated replacement tasks preserve the gate without duplicating reported issues.
- Source register uses Open file to dispatch the registered, fingerprint-verified classified original to the OS default application. Explicit version numbers remain intact. The fallback is the latest recorded system check attempt in DD-MM-YY, with the complete timestamp in a tooltip. It combines existing retrieval attempt evidence and persisted update-check receipts, excludes skipped checks, normalizes the configured timezone and never uses publication dates or page-open time.

## Verification

- 194 frontend tests pass.
- 146 System1 tests pass, including explicit re-review restoration and automatic-repair retention. The changed automatic-resolution test now enforces the user's new rule; existing duplicate-issue and QA workflows still pass.
- 19 source Workbench tests pass. 15 System2 metadata/handoff checks pass.
- Actual isolated browser on 63355: URL-only example.com intake reached a pending receipt; public ASC PDF metadata returned ASC Farm Standard / Aquaculture Stewardship Council / V1.0.1 / Certification scheme; an edited title survived re-parsing; file-only intake with blank official URL reached a pending receipt. Test records belong only to the retained fixture.
- Isolated update check produced five failed checks for synthetic example.invalid URLs; these were not labelled unchanged. Unit checks cover changed and unchanged content, ownership, transport guards and registered-only native opening.

- Actual desktop launch test: a registered TS003 PDF opened from the fixture classified folder in the OS default application (Chrome on this Mac), confirmed by its local file URL. A sandbox-launched service could not use LaunchServices; a normal desktop process succeeded. No browser download was substituted. Windows native dispatch remains code-tested only.
- Actual browser UI: nested Upload file selection was visibly highlighted; × removed the attachment and collapsed its fields; leaving Upload file for Source discovery and returning cleared both file and edited title without a confirmation dialog.

- Final normal runtime: PID 65122 at 62742. In-app browser showed PA057 fallback 28-08-26, matching persisted retrieval/check timestamps; CS010 retained version 6.0. Clicking PA057 Open file produced its classified system1/Data/A_Public_Authority local PDF URL in the default application. No normal candidate or selection was changed.

## Limits

Metadata is a local heuristic: PDF metadata plus at most five pages, HTML metadata/text, or a bounded uploaded XLSX preview. Missing facts stay blank and classification can stay pending. OCR, search API connection and broad automatic accuracy are not claimed. No normal business candidate, original replacement or human Include decision was submitted by engineering verification.
