# HTML section-numbering development diagnostic

PA001-001 is an exposed, copied public development source, not an independent holdout. The denominator is all 42 original heading `paragrafValue` spans, with terminal punctuation excluded from the separate numbering field. The source DOM independently supplies these labels; no output-only sampling is used.

Parser /4 recorded 0/42 complete labels; /5 records 42/42. All 412 blocks preserve their exact IDs, original text, source references, order, parent/dependency fields, tables and other fields; 84 numbering fields change: 42 section headings and 42 matching contents-list entries. The measured denominator is the 42 source headings, not all changed fields. Source bytes remain unchanged. The new result is a separate candidate and has not been adopted into existing personal or master content.

Ten synthetic numbering cases cover separated/attached suffixes, punctuation without whitespace, nonbreaking spaces, bare labels, ordinary title words, larger numbers, unsupported hyphenated IDs, decimal numbering and unnumbered titles. An initial malformed HTML test fixture failed signature validation and is retained in `tests-before.txt`; it is not evidence of the numbering defect. With the corrected complete HTML fixture, six of ten cases fail before the fix (`tests-before-valid-fixture.txt`). The final three parser/reader modules pass all 49 tests (`tests-after.txt`). Broader integration regression is pending.

This is a bounded numbering improvement. It is not full HTML fidelity, independent quality acceptance, Requirement recognition or business Gold. PDF extraction logic is unchanged; its /4 reserved-window FAIL remains applicable evidence, with /5 fixed-window regression still required before a new frozen candidate.
