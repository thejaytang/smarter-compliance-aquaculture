# Source workflow browser verification

2026-09-14, isolated coordinator at 60515. All review mutations used synthetic TS003 or a newly invented engineering candidate; normal sources were not scored or confirmed.

- Manual URL intake for `https://example.invalid/ui-redesign-source` with title, publisher and version returned “Added to the source review queue. No inclusion decision was made.” It appeared as one pending candidate. The candidate detail correctly showed the publisher/version and a missing-original explanation without a false download link; empty optional fields were collapsed.
- Source register showed five numbered fixture sources, with ID, title, publisher, version, selection and downloaded original link. TS003 opened read-only and disabled all ratings/selection.
- Request review created a pending TS003 task while its effective selection stayed INCLUDE. Opening Source review showed five H/M/L criteria and its bound task check.
- Changing Authority H to M left the selection control at INCLUDE. Save returned “Personal source progress saved. Effective source unchanged.” The previous H remained visible until explicit application.
- A deliberate PENDING choice and explicit task check were previewed and applied. The result remained PENDING with unresolved reasons. This is an engineering behavior check, not a substantive source acceptance.
- The action-history projection initially omitted applied reviews whose task remained open. It now projects existing adoption receipts, and after restart the actual UI displayed one Apply source review action, its operator/time and PENDING result. Expanding preserved the exact receipt and source link. No parallel ledger was introduced.
- Source details initially failed because sourceDiff was omitted during consolidation; the method and a rendering regression were restored. A first-mount navigation failure introduced during context retention was also fixed and has a focused regression.
- The native PDF iframe was visually black in the in-app browser despite a valid original URL. Source review now opts into the existing local PDF.js reader. Actual PDF rendering verification is recorded below when complete; the former black frame is not counted as a rendering pass.

The original normal shell was read without editing business data at 1280×720: header height 80, main origin x232/y104 and width1032. The redesigned global row is44 and full-width; material-specific dimensions are in material-browser-evidence.md. These are different surfaces, so this is a shell-space comparison, not a same-document readability score.

Final source PDF check: TS003 rendered selectable native page 1 in the shared PDF.js reader. Next page changed to page 2 of 3 with “No selectable text; read the page image”; an actual screenshot showed the scanned fixture heading and sentence. Source title, read-only ratings and source ID remained visible beside the original. This is a bounded three-page fixture check, not broad PDF fidelity acceptance.
