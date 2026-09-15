# Requirement annotations and check design

## Workflow

The material workspace has four independently scrolling panes: Original document, Extracted content, Requirements, and Interpretation & check design. Collapse a pane from its header; the same rail restores it. Drag separators or use arrow keys (Shift for larger steps). Narrow screens retain horizontal scrolling.

1. Save material text, then split a passage in Requirements. Assign exact source selections to fields and relationships.
2. **Finish & collapse** saves the unit and displays its completed field ranges in **Requirement annotations**. Other completed units remain visible. **Resume unit editing** removes that unit's completed marks; finishing restores its current ranges. Unmarked text is not a claim of complete parsing.
3. The Read selector switches between **Current text**, **Changes**, and **Requirement annotations**. Changes retains red strikethrough deletions and green additions. Reading modes do not save or review anything. Markdown editing retains the existing source/baseline behavior.
4. Activate an annotated fragment by mouse, Enter or Space to locate its splitting field. Overlaps list all referenced field/unit identities. **Locate text** returns to the source passage.
5. Choose **Interpret requirement**. Fill the two fields in each Scope, Condition and Demand group. Record explicit source quotations, proposed interpretations and unresolved questions separately.
6. **Checking Logic** updates from these six fields. It identifies A, filters applicable B within A, and describes checking B against Demand/evidence. C, when displayed, means objects with sufficient evidence of meeting Demand in the same assessment context. `B ⊆ C` is a design criterion, not a computed result. Unknowns, original exception ownership and source combinations remain visible. No operators are guessed from prose; fixed `k` and inclusive `[min,max]` semantics remain unchanged.
7. **Save interpretation** preserves a separate version. **Mark interpretation reviewed** is a later explicit action, blocked while fields or gaps remain unresolved. Neither action confirms or archives material content.

Unsaved interpretation drafts are retained by reviewer, material, requirement and browser tab. Switching Requirement keeps each draft. Leaving the material is blocked until all drafts or uncertain writes are resolved. The browser journal supports reload recovery; the server remains the durable authority after Save. On conflict, refresh/review context or explicitly reload the newer saved interpretation. History restores append a new revision and validate citations against current context.

## One shared API in Settings

Open the reviewer/Settings menu and choose **AI service**. Supply the complete OpenAI-compatible Chat Completions URL, model and API key, then save. There is no default service or model. A blank key keeps the saved key; Remove saved key explicitly clears it. The setting is shared by this installation, not duplicated in each pane. Optional `WORKBENCH_AI_API_KEY` is a server environment fallback. The Settings form supersedes the earlier environment-only configuration proposal.

The key is saved only in `workbench/runtime/ai-provider.json`, created with private file permissions on POSIX; it is never returned by the settings API, placed in browser storage, logged, or included in collaboration/recovery packages. Protect the runtime directory using the operating system's normal account permissions. Windows-native permissions and execution remain unverified for this change.

Saving configuration does not test the connection or call a model. Before configuration, generation shows **Not connected**. Configured means settings are present, not proven provider availability. This adapter powers interpretation suggestions; it does not enable the unavailable automatic Requirement extractor or Site Model engine. Legacy provider example files are retained as inactive compatibility/design artifacts, not additional Settings forms.

Generation is explicit. A confirmation displays the destination, model and complete material/version list. The context includes the selected requirement, connected splitting, full saved material blocks, saved/original document information when available, and explicitly selected accessible local related materials. Customer-confidential sources are blocked based on their governed source metadata. Nothing is researched online. If complete context exceeds the configured UTF-8 byte limit, generation fails before transmission; nothing is silently truncated.

All six candidates or a single field may be generated. Candidates include quotations, basis and gaps. They never replace formal edits automatically. **Use suggestion** previews replacement of existing content; adoption remains editable. A regenerated candidate does not change earlier formal edits. The server validates shape and exact quotations; this does not establish semantic correctness. Provider redirects are rejected and provider errors are sanitized. Timeouts, invalid citations, interrupted requests and stale context retain saved work.

## Data and interfaces

- `requirement-interpretation/1`: actor, material and Requirement ID, splitting revision, context fingerprint and manifest, six fields, citations, gaps, reviewed status, deterministic derived logic.
- SQLite tables: `requirement_interpretations`, `interpretation_history`, `interpretation_requests`, `interpretation_runs`. Added alongside existing Requirement tables in the existing Workbench database. No System3 service or environment is added.
- `GET /api/requirement-annotations?material_id=…`: current reviewer's read-only completed-span projection, plus stale sessions. Source offsets use Unicode code points. Markdown token projection checks canonical source equality and refuses uncertain mapping. Nested spans keep the inner field background and outer borders; ambiguous equal/crossing ranges are neutral overlaps.
- `GET /api/interpretations?unit_id=…`, `GET /api/interpretations/run?id=…`.
- `POST /api/interpretations/context`, `/save`, `/generate`. Save includes request UUID, expected revision and context fingerprint. The server regenerates logic, appends history, enforces reviewer ownership and rechecks splitting revision. Review/restore use the same guarded save route.
- `GET/POST /api/settings/ai`: sanitized shared configuration read / version-checked save. Secrets are write-only to the browser.

The ordinary consistent database recovery path includes splitting, interpretations, candidates and their histories. **Collaboration ZIPs still exclude splitting and interpretation data.** The UI explicitly labels this boundary. API credentials are excluded from both export paths.

## Global field palette

`four-pane.css` owns shared semantic tokens: Subject pink-purple; Modal Verb blue; Main Verb green; Object orange; conditions purple; exceptions red; subrequirement teal. Pane 2 marks and pane 3 fields use these tokens, with visible labels and focus descriptions. Scope, Condition and Demand use neutral group styling rather than implying a grammatical one-to-one mapping.

Validation evidence and known limits: [current report](../../project-support/four-pane-20260916/RESULTS.md).

## Versioned provenance and relational joins

Each saved interpretation revision now has an append-only projection in the same SQLite database:

`interpretation_history → interpretation_origins → interpretation_fields → interpretation_citations`

`interpretation_origins → interpretation_rule_nodes → interpretation_fields`

Origins also reference the exact `(session_id, revision)` in `requirement_steps`. The parent is immutable splitting history; deleting or combining an active unit cannot erase its saved evidence. Origin rows retain reviewer, Requirement ID, material and splitting versions, source descriptor/hash, block ID, chapter, code-point range and source text. The System1 original descriptor and System2 material remain their owning authorities; no duplicate writable legal text is introduced.

The Workbench SQLite connection enables foreign keys. A save atomically appends history and its relational projection, then commits the idempotence receipt. Fields, citations and rule nodes cannot exist without the owning saved revision. Legacy histories are indexed on first read from the exact saved splitting step. Citations whose original block metadata was not historically stored are labelled `legacy-unlocated`; they are never joined to today's paragraph merely because wording matches.

`GET /api/interpretations/trace?unit_id=…&revision=…` returns the requesting reviewer's saved trail, including retired units. Source edits make current interpretations require review but never rewrite the old trail. A quotation receives code-point `start` and `end` only if explicitly valid or uniquely present in its cited block. Repeated quotations retain an unresolved position until supplied explicitly. Block identity remains known. History restoration appends a new interpretation revision with currently validated references.

Generation runs are indexed by reviewer and Requirement ID. Opening one interpretation reads at most ten associated runs instead of scanning/deserializing the reviewer's complete request history.

## Optional QueryBuilder handoff

The six human explanations remain the primary editing workflow. **Site Model mapping · optional** provides explicit nested AND/OR comparisons without deriving them from prose. Each leaf has a stable ID, `field`, `operator`, typed `value` and an `interpretation_field` link. This link joins through the saved revision to that field's citations and the Requirement origin. Group nodes retain their parent and section (Scope, Condition or Demand).

The `requirement-check-design/1` contract contains three nullable groups. `null` means **unmapped**, not true and not an empty set. The server validates structure, types, identifier syntax, bounds, unique IDs and supported operators. Negation uses a supported negative comparison; unsupported group negation, quantifiers and event joins must remain unresolved rather than being approximated. Existing source quantity and exception structures remain separate and intact.

A sanitized `querybuilder` projection in the interpretation response uses the documented `condition` / `rules` / `field` / `operator` / `value` shape. An on-demand preview supports handoff. This references the [SQLAlchemy QueryBuilder contract](https://sqlalchemy-querybuilder.readthedocs.io/en/latest/) and [jQuery QueryBuilder rules](https://querybuilder.js.org/), without adding either library to the local runtime. SQLAlchemy QueryBuilder itself does not validate rule syntax. The downstream service must additionally resolve its allowlisted model fields, joins, types, event context and evidence sufficiency. These independent filters do not execute a Site Model query, compile quantity semantics, or establish `Satisfied`.

## Reduced daily controls

Completed cards provide **Interpret requirement** without reopening splitting fields. The six values are visible; **Evidence & gaps**, AI candidates, source structure, history and mapping expand only when needed. Entering a manual nonempty value with no recorded gap marks it as a proposed interpretation, never as source proof. Quoted-source status still requires valid references. **Source trail** shows the fixed saved lineage. Save remains distinct from review and is pinned at the bottom of the pane; Ctrl/Cmd+S inside this pane saves its interpretation. Material-level Save retains its own scope.
