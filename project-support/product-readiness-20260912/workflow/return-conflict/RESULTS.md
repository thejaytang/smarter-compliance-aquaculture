# Returned text conflict and saved-package recovery

2026-09-13. **PASS for this bounded isolated text-conflict round trip; the complete collaboration and product goals remain open.** Coordinator 55542 and reviewer 58814 use separate engineering stores and public PA001. No real business confirmation was made.

## Actual browser outcome

The reviewer saved personal revision 4 and exported a second submission based on the original assignment. The coordinator imported the actual ZIP through the file chooser. Comparison showed one unresolved text conflict and disabled adoption. An explicit edited combination resolved the conflict in preview. Leaving and reopening retained that choice; the master changed only after explicit adoption into revision 4, still Content draft. Archive revision 2 and prior confirmations remain retained. The reviewer imported the downloaded adoption receipt and retained their own revision 4 text, without the coordinator-only merge marker.

Evidence: [initial conflict](comparison-before.txt), [resumed choice](resumed-choice.txt), [adopted master](adopted-master.txt), [receipt import](receipt-import.txt), [received receipt](received-receipt.txt), [personal work retained](personal-retained.txt), [submission package identity](package.json).

## Delivery defects and corrections

Package freezing formerly announced a completed download without browser or disk proof. Downloads now distinguish frozen work from a requested download and expose a durable authenticated link to the same immutable package. Existing parent processes retain their frontend import routes. The actual recovered receipt matched the frozen server ZIP byte for byte: [download evidence](receipt-download.json). Browser download-event registration was necessary for reliable observation in this automation environment; its cause is not attributed to the product. Delayed tool calls are excluded from stability evidence.

Receipt exports also discarded the user's completed-scope summary. Future freezes now preserve that text; historical packages and same-request replay bytes remain unchanged. A new actual UI export retained the exact 166-character summary with one newline: [downloaded summary evidence](receipt-summary-download.json), [entered text](entered-receipt-summary.txt). This second package was downloaded and inspected; the preceding receipt is the one imported into the reviewer workspace.

[Backend recovery checks](download-recovery/backend/RESULTS.md) and [summary checks](download-recovery/backend/receipt-summary/RESULTS.md) retain focused evidence. Current full Workbench Python regression is **160/160 PASS** with unchanged code during the run ([binding](../workbench-python-08/result.json)); all frontend checks are **178/178 PASS** ([binding](../workbench-python-07/result.json)). Python /07 retained one failed assertion that incorrectly required the new helper URL in the startup graph. The corrected assertion enforces use of the existing export-status route for compatibility, while retaining actual HTTP, JavaScript content-type and exact-byte checks for the whole graph. No production code changed in that correction.

## Preservation, loading and recovery

[Preservation](preservation.json) verifies 79 prior immutable rows and five original hashes at its recorded checkpoint; it predates the last summary-only freeze and is not a blanket unchanged-store claim. Ten integrity-checked store backups are in [pre-return checkpoint](../pre-return-conflict/manifest.json), with a later [pre-restart checkpoint](download-recovery/pre-restart/manifest.json). Restore only the matching isolated fixture if needed; never overwrite business data.

Coordinator session 29169 on 55542 loads the current reader, download endpoint and summary fix. Reviewer session 69115 on 58814 loads the reader and download endpoint; its parent predates the final summary fix, which is coordinator-only. Fault session 6250 on 60905 retains its reader backend. All three ports were observed listening at this checkpoint. Normal 62742 was not restarted; an actual read-only overview compatibility check succeeded, without opening business materials. The isolated launcher remains the [resume entry](../../serve_isolated.py).

Remaining: returned table-cell conflicts and the other uncovered exception cases, browser preference/zoom acceptance, a newly frozen integrated workload, independent extraction quality, actual colleagues and Windows round trip. This checkpoint does not make Requirement recognition or semantic processing connected.
