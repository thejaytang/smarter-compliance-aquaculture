# Storage, Versioning and Exchange

## 1. Ownership

| SQLite file in `workspace/databases/` | Authority |
| --- | --- |
| `system1.sqlite` | Governed sources, original versions/artifacts, source operations/history, machine assessments/holds, saved source-review exchange objects |
| `system2.sqlite` | Canonical/material processing records, material revisions/review history, saved collaboration material/catalog objects |
| `system3_requirements.sqlite` | Requirement sessions, immutable steps, units, source-bound Group JSON, links and relational projections, requirement exchange receipts |
| `system3_scd.sqlite` | Saved `requirement-interpretation/1` records/history, origins/citations, candidate runs, check-design projections and Site Model catalog |

`runtime/state/workbench.sqlite` is a local coordination journal for actors, requests, sessions, resumable operations and editable local policy. It is not a fifth business database and is never exported. Private settings live under `runtime/settings`; original attachments and processing artifacts under `workspace/sources`.

SQLite `file:` URI reads resolve through the same owning aliases as filesystem-path reads. URI decoding uses native path conversion so Windows drive roots, escaped characters and Unicode names retain their identity; read-only query parameters and personal-branch table prefixes are preserved.

Windows extended-length syntax is confined to native file/SQLite access. Portable identities, descriptor paths and exported names keep ordinary spelling. Atomic copies preserve original names and hashes and retain refusal to overwrite different content. Package history JSONL uses explicit UTF-8/LF bytes on every platform. Snapshot preparation uses unique short OS temporary directories with bounded ownership and long-path-safe cleanup.

Application operations remain serialized and reentrant. Waiting interactive operations precede background legacy/export checks unless the oldest waiter has aged for ten seconds; a running operation is never interrupted. This is a scheduling preference, not a ten-second execution deadline. Idle legacy checks wait ten seconds, active processing retains its three-second interval, and source Excel checks wait five seconds. Materials and Collaboration display projections may reuse the shell's existing three-second source snapshot; save/adoption checks continue to resolve owning evidence and expected revisions.

System2's main material tables have their original names. Retained personal branches use `branch_<stable-reviewer-id>__<table>` in the same System2 file. Local `.storage.json` descriptors resolve branch paths to that owner; they are operational pointers, not business identity. No extra workflow SQLite file is created for a branch. Replaceable source-check/Excel markers and locks resolve to `runtime/state/system2/<branch>/`; retained pre-migration marker files are excluded from business packages.

## 2. Authority and bindings

Immutable `requirement_steps.body` and `interpretation_history.body` preserve exact JSON, authors and time. Current rows point to saved heads. Relational source/structure/citation tables are derived indexes, validated against saved authority. Interface `R1`/`G1` labels never replace stable IDs.

Interpretation reads reuse each owning material read only within the same coordinated request. A successful interpretation save returns its committed document in the HTTP response, avoiding a second browser fetch. The durable request receipt is unchanged. A retry after a lost response reuses that receipt and reads the current saved document without appending another revision. Conflicts return no replacement document; drafts and explicit conflict decisions remain with the client. No context snapshot is reused across independent requests.

A Requirement session records material ID/revision, source identity/hash/version, block IDs, text, exact spans/source segments and source references. Units retain stable IDs and Group trees, relationships, quantities and links. An interpretation records its unit ID, session ID/revision and frozen context/source citations. Version 3 remains version 3 after Requirement version 4 is saved; reads flag it stale. Saving a new interpretation is explicit.

SQLite foreign keys protect relationships inside each file. Application commits additionally validate S/C/D origins against saved Requirement steps. Owning adapters validate material/source bindings on writes; full inspection validates the complete saved chain and original hashes. The public interfaces keep expected revisions, request IDs and append-only receipts. Attached-database writes use on-disk journals, full synchronization and deterministic database order; routed material connections prohibit WAL to preserve the multi-file rollback mechanism.

New fourth-pane saves use `requirement-check-design/2` inside the existing interpretation record. It retains the three rule groups and adds `object_type`, `identity_field`, `assessment_context` and `based_on`. A group may carry explicit boolean `not`; an unmapped leaf carries `id`, `expression` and `interpretation_field`. These leaves retain relation/time meaning without claiming query support. `based_on` freezes the six interpreted values, source-context fingerprint, catalog revision and exact rule design confirmed by the reviewer. A mismatch prevents a ready handoff.

The optional `/2` `concepts` extension stores `{id,label,kind,status,references}`; `kind` is concept/relation/property/event/action, `status` is proposed/confirmed, and references contain exact saved-context IDs/quotations. Leaf `concept_ids` reference this registry. Validators bound sizes, enforce stable unique IDs, reject dangling references and verify quoted source text on save, generation and import. Concepts and source manifests are also available in the saved source trail. A confirmed local meaning is not an ontology or database binding.

For concept-enabled designs, the single rule tree deterministically supplies the current main-card definitions and review values. The original six fields remain stored as contextual explanations/evidence, so opening or saving does not erase earlier prose. Designs without the extension retain their historical deterministic projections, including during import. Editing new rule trees invalidates review and mapping confirmation; changing source context resets concept meaning confirmation. AI candidates preserve current manual work until accepted per card and always start with proposed concepts. No relational schema migration is needed.

Generated `logic.version=2` includes `requirement-set-handoff/1`: A/B/C definitions, citations, shared object/context metadata, B's input domain A, intended B ⊆ C composition, supported QueryBuilder projections and explicit gaps. `executable` is always false. Unsupported predicates or group negation block the entire affected projection. The consumer must validate allowed models, joins, correlated evidence and time semantics. Old `/1` designs retain their original deterministic logic in history and import validation; an explicit new save upgrades a draft. No database migration or historical rewrite is needed.

## 3. Consistent packages

`workbench-business-package/1` has purpose `collaboration` or `delivery`. Export serializes application mutations and reserves all four database writers before SQLite backup and attachment copying. It creates a frozen application view to derive the same logical merge payload. No independent live database copies are treated as a coordinated snapshot.

Required ZIP contents:

- `manifest.json`: format/purpose, package UUID, actor/time, complete file bytes/SHA-256 inventory, database user_version/schema hashes/table counts, exact saved bindings and original identities.
- `databases/`: the four SQLite snapshots.
- `sources/`: managed originals and required retained attachments.
- `logs/`: one JSONL human-history projection per owning database.
- `logical-workspace.zip`: validated, source-bound logical merge representation for Workbench.
- `README.txt`: independent reading instructions and the non-executed check-design boundary.

There are no runtime settings, API secrets, sessions, caches or diagnostic logs. Missing/changed referenced originals stop export. Local `workspace/logs/<package-id>/` holds the matching history projection; the database history remains authoritative. Packages have bounded expanded/compressed size and portable, collision-checked paths.

## 4. Import and history

Imported SQLite is untrusted, read-only evidence: schema/integrity/foreign-key checks, source hashes, cross-database bindings and authoritative-history comparison run before merge. Logical heads must match saved database content or previously retained sync branches. Domain validation is still required; a valid checksum is not semantic approval.

Preview compares with local saved work. Explicit conflict decisions and confirmation are mandatory. Expected-revision guards reject changed local inputs. Each owning write has a deterministic request ID; `applying` progress persists between writes so interruption/replay can continue without duplicate changes. Current records are never replaced by the received databases.

Original incoming history is appended as immutable `received_history` evidence in the owning store, deduplicated by canonical event hash. Source and attachment indexes retain content-addressed files. Locally continued versions retain original provenance and the new editor. Retained incoming versions can be read even when local revision numbers are rebased by conflict handling.

Legacy logical full snapshots remain supported through their existing validators. Unsupported formats fail explicitly. A `delivery` package is rejected by Collaboration import; it is a fixed downstream artifact.

## 5. Independent downstream reading

Open each SQLite snapshot read-only. Start from an S/C/D history JSON body, use `session_id` and `session_revision` to find its exact `requirement_steps` record, then follow `material_id`, `material_revision` and source segments to System2 `material_revisions`. Its source ID/hash/snapshot points to System1 `source_versions` and the manifest's original path. Imported evidence may be in `received_history`, `received_sources` and `received_assets`; it preserves original identity even after local rebasing.

The manifest gives schema version/hash and table inventory, and SQLite `sqlite_master` gives the complete readable schema. Human logs carry actor, time, object type/ID, action, before/after version and operation identity with source evidence. Optional unknown legacy event fields remain unknown, never replaced with migration time.

## 6. Migration and recovery

Component process reuse does not cache business authority or bypass write coordination. Every request opens its owning stores and retains the existing source checks, expected versions, durable request identities and immutable history. A transport failure after a possible commit is an uncertain receipt, not permission to repeat a new write. The application closes component processes after draining background writers during shutdown. Read-only material scheduling hints use the existing candidate status in the correct storage alias/branch; missing or unreadable stores are errors, not an empty queue.

Material candidate computation may run outside the application operation lock, under the existing worker file lock, because it reads hash-checked immutable originals and creates only isolated attempt artifacts. Preparing the captured candidate binding and finalizing its result use the owning service under write coordination. Finalization checks the exact candidate/source/scope/input revision; concurrent human revisions are preserved and make the candidate stale. This does not authorize new extraction, auto-adoption or confirmation.

New attempt artifacts use `material-artifacts/<attempt-id>/` beneath their owning material workspace to avoid nesting three long identifiers on Windows. `attempt-binding.json` retains the exact material, candidate, source, scope and input revision. Successful candidate metadata records the relative artifact directory and attempt ID. Each attempt remains separate; older directory layouts and failed-attempt evidence are retained unchanged.

Initial business-seed import separates temporary preparation (`runtime/staging/seed/`, resolved by `Workspace`) from durable recovery receipts (`runtime/backups/initial-import/`). A retry requires the same verified package and compares retained legacy prepared files without deleting them. Promotion is restricted to the package inventory. Windows destination preflight includes promotion temporary names; it rejects unsupported path lengths before package-file writes. Existing completed workspaces remain ineligible for seed restoration.

`workbench-layout/1` is explicit and requires a stopped service. It makes SQLite-consistent old-store backups, copies tables without rewriting authoritative JSON, retains historical source files, validates and promotes staged stores. The layout marker appears only after verification. Prepared hashes and refusal to overwrite different destinations support interruption/retry.

Data migration does not create new human edits or collapse separate Requirement/SCD versions. Original paths in historical evidence remain historical; local operational descriptors are rebased separately. Recovery evidence stays under `runtime/backups/architecture-v1`. Ordinary launch and application updates never invoke seed restoration or data clearing.

## Processing completion records

`material_progress_confirmation` objects are append-only System2 collaboration records (`id`, `material_id`, `stage`, `signature`, `complete`, `actor`, `at`). They track processing progress separately from material body revisions and per-card approvals. `material_progress_receipt` and existing request bindings make completion decisions replay-safe. The progress version guards concurrent reopen/confirm choices. Full peer snapshots carry confirmation records as validated immutable history; imported history only applies when the current owning content signatures match. Archive checks the current owning material, all active Requirement entries, and all top-level interpretations under the operation lock. Legacy archived records remain historical evidence and are not retroactively marked as having these new confirmations.
