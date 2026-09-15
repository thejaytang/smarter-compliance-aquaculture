# Document context and cross-document validation

## Delivered behavior

- Candidate and document-information sections collapse independently. Review-impact notices are dismissible across the page top, without changing review state.
- Before extraction, document information is absent. A ready/partial extraction or existing extracted content enables it. Opening an original alone does not create editable content.
- Metadata edits use the existing Markdown redline/editor/save path, stored as a source-bound block with role `document_information`. The body and Requirement intake exclude this role. Source-derived baseline and historical saved versions are retained.
- HTML information supports explicit metadata, meaningful headings, Official Journal title paragraphs and saved HTML titles. PDF/spreadsheet information can be entered manually after extraction; automatic identity extraction for those formats remains unimplemented.

## Cross-document findings and correction

Initial corpus run: 70/72 passed. Two Mattilsynet files (PA027, PA043) lost heading text in the reader because removing hydration comments also removed their following text. The reader now preserves comment tails. PA010 uses Official Journal title paragraphs; PA026 has its title only in the HTML head. Explicit fallbacks now retain both. Final `material-reader/12` corpus run: 72/72 passed, all 62 HTML titles present, all 10 PDFs rendered first and last pages. Every original hash remained unchanged. [Per-file results](corpus-results.json), [reproduction script](check_corpus.py).

This checks saved-source reading, metadata values/anchors and PDF rendering. It does not certify every paragraph of automatic extraction or scanned-page OCR accuracy. Excel reader/merge/formula/hidden-sheet behavior is covered by isolated fixtures, not a current System1 Data spreadsheet (none exists there).

## Automated checks

- Frontend suite: 238 passed after document-context visibility/editing guards.
- Reader/body/Markdown suite: 64 passed; final navigation subset after title fallback: 8 passed.
- Final Markdown/navigation subset: 30 passed.
- Workbench Requirement persistence/API suite: 9 passed, including backend rejection of document-information intake.
- Isolated MaterialStore save/reopen test verifies metadata role, original baseline, source references, body preservation and unconfirmed review state.

## Actual browser checks

- Normal PA001, personal revision 0: document information count 0 before extraction.
- Isolated TS001 HTML fixture: information absent before Auto-extract; present after requested candidate completes. The fixture's workers were disabled; one explicit isolated material tick executed that requested extraction.
- Edited title and added Test reference DOC-QA-001 in the actual Markdown editor. One removed and one added difference region appeared; metadata count inside continuous body was 0.
- Save succeeded at isolated personal revision 4. Reload retained revised title, test reference, original baseline, one red deletion and one green addition. Metadata options in Requirement intake: 0.
- Earlier disclosure/status-refresh check retained collapse state and dismissed notification, with normal PA004 personal revision 8 unchanged.

## Activation and preservation

Normal service activation used five consistent database backups. All five stores had zero changed logical tables across restart; automation remained disabled. [Activation evidence](activation.json). Business material bodies and review confirmations were not saved, adopted or modified by these tests. UI interactions and writes beyond read-only navigation occurred only in the retained engineering fixture.

Reproduce corpus check from project root with `PYTHONPATH=system2/src system2/.venv/bin/python project-support/document-context-20260915/check_corpus.py`. This creates only isolated reader caches and the report. Native Windows interaction and full extraction-quality acceptance remain separate.
