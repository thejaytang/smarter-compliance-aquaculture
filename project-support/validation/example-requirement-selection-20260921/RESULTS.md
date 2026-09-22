# Example Requirement selection, 2026-09-21

## Result

The permanent PE002-001 example now has **21 active Requirements**, including the explicitly historical 2013 transition duty, and 21 matching saved interpretations. The user requested this correction after identifying the purpose clause as context rather than a Requirement. No application code or schema was changed.

- Thirteen non-duty entries were soft-removed: purpose, applicability, addressees, definitions, zone-rule power, repeal notice, broodstock permission, supervision/enforcement, coercive-fine power, fine period, penalty, dispensation and commencement. They remain in the complete source and every active interpretation context. The enabling-law preamble also remains context.
- Former R10 counting and R11 slaughter exemption were replaced by one combined R5 sourced from `s6-2` and `s6-3`. Both negative applicability statements are copied verbatim into its conditions; they are not separate demands. The two duty clauses retain paired temperature/frequency branches and the seven Annex links. The fourth-pane fields and Boolean design were reviewed and copied to the new source binding without inventing new terms.
- Twenty other Requirement/interpretation identities, revisions, annotations, quantities, source spans and saved designs are unchanged. Former temperature R9 is now R4, with the same nine proposed concepts and interpretation revision 3.
- Fifteen removed entries, all earlier Requirement steps, all previous interpretation heads and every interpretation history record remain retained. R labels are source-ordered display labels, not persistent identifiers.
- Material revision 3, all 85 body blocks, title/metadata, original HTML bytes and pending human-review declarations remain unchanged. No Site Model execution or legal compliance result is claimed.

## Current source order

| Label | Source blocks | Selection key |
| --- | --- | --- |
| R1 | s4-1 | plan-basis |
| R2 | s4-2, s4-3, s4-4, s4-5, s4-6, s4-7 | plan-content |
| R3 | s4-8 | plan-maintenance |
| R4 | s6-1 | temperature |
| R5 | s6-2, s6-3 | counting |
| R6 | s8-1 | limit-south |
| R7 | s8-2 | limit-north |
| R8 | s8-3 | limit-action |
| R9 | s9-1 | medicine |
| R10 | s9-2 | treatment-method |
| R11 | s9-3 | treatment-evaluation |
| R12 | s9-4 | resistance-action |
| R13 | s10-1, s10-2, s10-3, s10-4, s10-5, s10-6, s10-7 | weekly-report |
| R14 | s16-1 | transition |
| R15 | annex-1, annex-2, annex-3, annex-4 | annex-stages |
| R16 | annex-5 | annex-south |
| R17 | annex-6 | annex-north |
| R18 | annex-7 | annex-procedure |
| R19 | annex-8 | annex-records |
| R20 | annex-9 | annex-averages |
| R21 | annex-10 | annex-pre-treatment |

The exact old/new UUID mapping and per-entry classification reasons are in [selection-manifest.json](selection-manifest.json). The complete earlier 35-entry review is retained as historical evidence; its entry count is superseded by this selection.

## Verification

Run from the repository root:

```sh
workbench/.venv/bin/python project-support/validation/example-requirement-selection-20260921/verify.py
```

The check uses fresh API readbacks captured before and after the owning-API writes. It verifies exact text spans/citations, complete source/context retention, 21 active entries, unchanged retained identities/designs, both merged source blocks, all seven live Annex references, all old history-row hashes, and 12 temperature/broodstock/slaughter boundary cases. All passed. See [verification.json](verification.json).

The live browser was reloaded and verified: 21 ordered Requirement cards; R1 starts with the § 4 coordinated-plan duty; R4 is temperature; R5 is combined counting; Removed entries shows 15 recoverable entries. R5’s fourth pane displays saved/pending status, the correct facility/fish-group object, both NOT exemptions, and the 7/14-day frequency branches. The first pane remains a sandboxed rendered HTML reading view; source context is preserved.

## Recovery and limits

A coordinated local Collaboration recovery export was created before writes: `6a6bc764-50ea-48aa-a8f3-e57983247126`, 72,357,016 bytes, captured at `2026-09-21T11:26:30.044246+00:00`. The receipt is [backup-receipt.json](backup-receipt.json). No package was published.

Use Removed entries to restore individual contextual entries if a reviewer revises the classification. To undo the counting replacement, remove the combined entry, restore the old exemption first, then restore the old counting entry because it links that exemption. Their saved interpretation histories remain bound to the old identities. Do not restore the old pair while treating the combined entry as an additional duty.

This is model-prepared selection for human review of the saved source version, not a statement that every legal consequence is an operator duty or that the current law has been independently re-retrieved. Existing cross-reference gaps, including repealed § 7 and actual permission/dispensation terms, remain explicit. No new automatic classifier was introduced. No commit, push or release was performed.
