# Requirement Workstream Presentation v2

This version makes the capability boundary between the current no-API system and an optional API-connected extension explicit.

## Canva design

- Design ID: `DAHT5tlR70w`
- Title: `Requirement Workstream - System1 + System2 Redesign v2 - API Capability Boundary`

## Capability model

### Without API: current core

- Manual intake and structured candidate inbox
- Scheduled official retrieval
- Payload validation and hash/version comparison
- Rules-based governance and Random QA
- Safe workbook synchronization and reporting

### API connected: optional extension

- Active regulatory and source discovery through search providers
- Semantic deduplication and document matching
- Change summaries and draft source assessments
- Explainable triage and natural-language operator interaction

### Boundaries that do not change

- Human acceptance remains mandatory.
- APIs do not become legal authority.
- API failure falls back to the deterministic core.
- API output cannot directly promote files or perform unsafe workbook writes.
- Original-format retention, paywall rules, backups and audit history remain enforced.

## QA evidence

- `rendered/`: local 1920 x 1080 renders.
- `canva_post_import/`: thumbnails retrieved from Canva after import.
