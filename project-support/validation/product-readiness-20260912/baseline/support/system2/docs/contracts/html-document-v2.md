# HTML Canonical v2 Contract

Current default parser: `html-dom/2.1.0`; schema: `html-document/2`. Applies to governed static HTML snapshots. Eligibility belongs to the [source-intake contract](source-intake.md).

## Body scope

Template recognition must be unique. Lovdata reads title, documentMeta and documentBody; ASC reads title and main; Fiskeridirektoratet, Miljødirektoratet and Mattilsynet read title and main#main. Detection and CSS/XPath roots belong to `HTML_PROFILES` in `contracts/html.py`. Site chrome headers/footers are excluded; navigation, metadata and filters inside the body are retained with roles. Unknown/ambiguous templates, missing roots and empty bodies fail explicitly. Navigation cannot replace body text.

## Sole fact source

`nodes` preserves elements, DOM hierarchy/order, original attributes, heading levels and section context. `atoms` preserves text nodes, including whitespace, in source order. Every atom has an owner and text index; nodes have stable snapshot/DOM-path IDs and CSS locators. Source/configuration hashes and parser version are inherited. Tables, lists and links reference nodes instead of maintaining independently editable text copies.

Tables retain grid coordinates, rowspan/colspan, empty cells and nesting. `is_header` means an original `<th>` only, not an inferred business header. `rowspan=0` covers remaining rows in its row group while the original attribute remains 0. Spans crossing groups and overlapping cells generate explicit issues; do not guess table width. Lists preserve direct items and original labels. Internal links/static footnotes retain targets; duplicate/missing targets remain ambiguous/missing. External targets are not downloaded.

Within the body, exclude only script/style/comment content, recording location, reason and digest. Trim comment-digest boundary whitespace to reconcile DOM engines' empty-comment representations; do not trim body text this way. Preserve visibility, filter and data attributes. Retain all static display branches without executing JavaScript or deciding final visibility. Preserve image references without claiming image-text transcription.

All machine items have `confidence=null` and `review_policy=review_required`; `requirement_status=not_extracted`. These are not Requirement semantic-extraction results.

## Independent verification and artifacts

Parsing uses BeautifulSoup. Independent lxml verification reconstructs boundaries, DOM, text, attributes, order, table grids, lists and links without importing parser traversal/table logic. A standard-library HTMLParser separately checks raw text flow and root counts, avoiding shared-libxml blind spots; only CRLF/CR line endings are normalised. Mutation tests cover omissions, reordering, rewriting, incorrect relationships, confidence/review policies at every level and complete issue inventories. Hidden issues or inflated confidence must not pass.

`canonical.json` is the fact source. `verification.json` records checks, the Canonical model digest and physical-file SHA-256. The shared result binds schema, Canonical and verification references/hashes. Verification failure returns failed; success remains review_required. Passed means machine checks succeeded for the specified body scope in the local snapshot, not acceptance of dynamic pages, images or legal semantics.

## Compatibility

Default `template=auto` uses v2; `config/html-auto.json` may be supplied explicitly. The `lovdata-document-v1` template in `config/html-template.json` retains legacy `html-structure/1` behavior without migrating historical artifacts. Consumers inspect result schema version before choosing a model.
