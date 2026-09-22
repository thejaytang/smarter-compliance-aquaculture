# Full-law Workbench example

[example.html](example.html) is a complete Norwegian HTML copy of **Forskrift om bekjempelse av lakselus i akvakulturanlegg**, FOR-2012-12-05-1140, including §§ 1–16, Annex 1, document metadata and amendment notes. The original document language and bytes are preserved. It is not an anonymised or abridged fixture.

The source already exists as **PA015-001**, “Regulation on control of salmon lice in aquaculture facilities”, from [Lovdata](https://lovdata.no/dokument/SF/forskrift/2012-12-05-1140). The saved consolidation identifies the last amendment as FOR-2023-12-14-2087. SHA-256: `9334a78a021971411e5c8826a2bb16aab1db707d778f6249c9a36b0afc90a4a1`.

## Permanent Example

On 2026-09-21 the user requested a permanent, separate copy in the library. This workspace registers it as **PE002-001**, titled **Example：Forskrift om bekjempelse av lakselus i akvakulturanlegg**, linked to primary source **PA015**. The Example prefix is register metadata; the retained original itself is unchanged. Do not treat this saved library entry or its annotations as disposable test data. PA015 remains unchanged.

The local copy has model-prepared extracted content for the complete legal body, 21 active source-bound Requirement entries and 21 matching fourth-pane interpretations. Purpose, applicability, definitions, authority powers and legal effects remain source context rather than independent Requirements. R1 starts with the coordinated-plan duty in § 4; R4 covers temperature measurement; R5 combines counting with its broodstock and slaughter-out exemptions. The dated spring-2013 transition duty remains explicitly historical. Twenty retained entries keep their original identities and annotations; the combined counting entry has a new identity, while its two predecessors and thirteen context-only entries remain recoverable in Removed entries with all prior interpretation/history records preserved. Original Norwegian wording stays in panes two/three; fourth-pane interpretation is English. Human review remains pending, including the explicit source-reference gaps. No Site Model mapping or compliance execution is claimed. The older PE001 excerpts and history remain retained, with PE001 excluded from active source selection.

## Fresh installation

[example-seed-20260922.zip](example-seed-20260922.zip) initializes the four business stores with **only PE002** and its saved work. Its SHA-256 is `ddae83dde9a29f456fee1de78d270896d7e1304d3637ab961dfd4d4f4df688c2`; [checksum file](example-seed-20260922.zip.sha256).

After installing dependencies, run from the repository root:

```sh
python3.12 deployment.py restore-initial --archive workbench/resources/examples/example-seed-20260922.zip --sha256 ddae83dde9a29f456fee1de78d270896d7e1304d3637ab961dfd4d4f4df688c2
python3.12 deployment.py verify
```

On Windows use `py -3.12` instead of `python3.12`. Initial restoration refuses a workspace with existing business data. It does not enable schedules, configure model credentials or approve the prepared annotations.

## Existing installation

Use [example-work-20260922.zip](example-work-20260922.zip), SHA-256 `2843373219fd04457b59445496ceb01caeac6623b343cedb7515f34e983c7c86`; [checksum file](example-work-20260922.zip.sha256). Open **Collaboration**, import the ZIP, inspect the preview and explicitly apply it. Resolve any local/incoming conflict before applying. Existing unrelated sources and saved work are retained.

The package preserves PE002's source/version identities, material revision 3, all 85 legal-body blocks, 21 active Requirements and 21 matching interpretations. Removed entries and their saved histories remain recoverable. Purpose, applicability and definitions remain context. Prepared interpretations still require individual human approval; no completed compliance finding is included.

The package includes only PE002 source/review records, its material and its source-bound Requirement/interpretation history. Original source bytes, source spans, Group structure, quantities, author/time and saved bindings are preserved. It contains no credentials, runtime configuration or unrelated business records.

After applying, reopen **Materials → Example：Forskrift om bekjempelse av lakselus i akvakulturanlegg**. An application update alone does not import annotations. Uploading `example.html` alone supplies the original document, not its saved work. Do not unpack a package over workspace files or restore the seed over an existing installation.

The earlier 2026-09-18 PE001 excerpt package is retained only on the development branch and in history. It is not the current Example and is not included in the product checkout. Updating the product does not delete local historical PE001 work.
