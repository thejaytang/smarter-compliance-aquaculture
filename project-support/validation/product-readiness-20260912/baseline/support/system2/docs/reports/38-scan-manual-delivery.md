# Offline scanned-body manual delivery

Date: 2026-09-10. Decision: **CONTINUE**. This is a functional mechanism exercise on an existing synthetic scan, not a real-source accuracy study or an independent reference judgment. The [current-stage contract](../../../docs/design/requirement-workstream-stage-delivery.md) permits this scope while broader real scans remain future evidence.

## Input and actual processing

The unchanged existing `gold/pdfs/scanned-critical.pdf` was copied into a new, explicitly labelled isolated System1 database fixture as PA901. SHA256: `1d2fdae4d0289238e3b6a3f9fb424a096e33deb10df9383e68bbf7f0c43b28b1`. Neither Gold nor production sources were modified. The fixture's source title, provenance, notes and output identify its synthetic development purpose. Initial fixture ratings were completed before processing; these are test setup, not a real source-governance judgment.

The shared browser on isolated port 64001 explicitly started the unmodified local PDF route. It completed one scanned page, producing three text units and two coverage units. All four printed lines were present, including `0.01 mg`, `not exceed 0.02 mg` and the date `2027-12-31`. The two body lines were wrongly typed as a heading. This natural structural error is separate from the subsequent seeded omission. No provider or external model was enabled.

## Actual workbench loop

A pre-error database copy and full machine readback were retained. The date unit was then deliberately removed from the disposable review result to exercise a wholly unmapped source region; the original PDF and Canonical remained unchanged. This is an injected test failure, not a natural omission rate.

1. The original-page checker found the absent date with `source_region_unmapped`, critical severity, null confidence, a page-1 bounding box and no corresponding output item. Four original lines were checked. The first comparison phase took 0.489 seconds; this excludes save time.
2. The actual browser located the original, prepared a supplement, and saved the exact date text with its original page/box and an explicit development-exercise note. The effective result gained the located content unit; the prior check became stale.
3. The reviewer changed the body from heading to paragraph and attached the date as related original context through the normal structured-repair controls. Original source facts were retained.
4. The new page comparison had zero reported differences. Six unverified scopes remained visible, including unknown extraction lineage, order and table/footnote checks. The same local OCR family is not independent quality evidence. The full one-page image was manually compared; its absent tables, footnotes, illustrations and cross-page continuation were recorded in the human scope decision.
5. A saved older draft was rejected after version changes. Its note was retained and it remained Pending. Explicit comparison with the current original was required before the current page confirmation saved at revision 22. The failed submission was not counted as a review.
6. All five A units were human-confirmed. B retained the title and date as context, one complete unnumbered body parent as Requirement, and both generated coverage checklists as context only. Machine confidence remained unknown. The date is attached to the published parent with its exact source location.
7. The source reached `complete` at revision 32, one published Requirement, zero actionable or blocked tasks. Review history displayed 13 applied decisions and excluded draft events. The browser showed saved event 33 and synchronized Excel event 33.

There were 13 applied manual decisions: one supplement, one content-type repair, one relationship, five A checks and five B checks. The exercise from observing the machine result at 16:10:28 UTC to the completed database readback at 16:21:49 UTC lasted 11 minutes 21 seconds, including developer tool orchestration, diagnostics and deliberate failure injection. It is not a human labor benchmark. Initial machine text coverage was 4/4 printed lines in this tiny fixture; all five A units and all five B judgments used human confirmation, so machine acceptance share was 0%. No broad automatic-quality claim follows.

## Delivery and evidence

The published parent retains its PDF hash/version, immutable Canonical identity, body, paragraph type, source position and related date content. No original number is invented. The generated workbook contains the complete body, date, source hash and synthetic label; OfficeCLI validation passed. Frozen output SHA256: `cc99228014d774ab43645812618ab5e58b1204f575c64df640b4cf6f118f82bb`. Native visual acceptance of this copy remains unperformed.

Local evidence: `workbench/runtime/stage-functional-20260910/`, including one-time fixture initialization, machine-before-omission database/readback, explicit seeded-error record, final workflow/feed, Excel readback and frozen output. The live isolated databases and immutable parsing artifacts belong to `workbench/runtime/stage-functional-pilot/`. No synthetic decisions were copied to normal operation.

## Remaining functional audit

Reuse reports 16 and 22–37 for existing HTML/XLSX, source preservation, database authority, repair propagation, retry/recovery, temporary B subdivision and weekly mechanisms. The current code audit confirms that whole erroneous extracted table rows have no explicit retirement control, although duplicate row-item retirement and cell/grid repair exist. The real cross-page example in report 31 retains such an extra row. Verify and provide a usable source-preserving manual path before claiming that representative table task complete. Do not resume repeated automatic layout tuning as a substitute for this missing operation.
