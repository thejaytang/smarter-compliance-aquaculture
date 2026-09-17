# Storage, Versioning and Exchange

## 1. Ownership

| SQLite file in `workspace/databases/` | Authority |
| --- | --- |
| `system1.sqlite` | Governed sources, original versions/artifacts, source operations/history, machine assessments/holds, saved source-review exchange objects |
| `system2.sqlite` | Canonical/material processing records, material revisions/review history, saved collaboration material/catalog objects |
| `system3_requirements.sqlite` | Requirement sessions, immutable steps, units, source-bound Group JSON, links and relational projections, requirement exchange receipts |
| `system3_scd.sqlite` | Saved `requirement-interpretation/1` records/history, origins/citations, candidate runs, check-design projections and Site Model catalog |

`runtime/state/workbench.sqlite` is a local coordination journal for actors, requests, sessions, resumable operations and editable local policy. It is not a fifth business database and is never exported. Private settings live under `runtime/settings`; original attachments and processing artifacts under `workspace/sources`.

System2's main material tables have their original names. Retained personal branches use `branch_<stable-reviewer-id>__<table>` in the same System2 file. Local `.storage.json` descriptors resolve branch paths to that owner; they are operational pointers, not business identity. No extra workflow SQLite file is created for a branch. Replaceable source-check/Excel markers and locks resolve to `runtime/state/system2/<branch>/`; retained pre-migration marker files are excluded from business packages.

## 2. Authority and bindings

Immutable `requirement_steps.body` and `interpretation_history.body` preserve exact JSON, authors and time. Current rows point to saved heads. Relational source/structure/citation tables are derived indexes, validated against saved authority. Interface `R1`/`G1` labels never replace stable IDs.

A Requirement session records material ID/revision, source identity/hash/version, block IDs, text, exact spans/source segments and source references. Units retain stable IDs and Group trees, relationships, quantities and links. An interpretation records its unit ID, session ID/revision and frozen context/source citations. Version 3 remains version 3 after Requirement version 4 is saved; reads flag it stale. Saving a new interpretation is explicit.

SQLite foreign keys protect relationships inside each file. Application commits additionally validate S/C/D origins against saved Requirement steps. Owning adapters validate material/source bindings on writes; full inspection validates the complete saved chain and original hashes. The public interfaces keep expected revisions, request IDs and append-only receipts. Attached-database writes use on-disk journals, full synchronization and deterministic database order; routed material connections prohibit WAL to preserve the multi-file rollback mechanism.

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

`workbench-layout/1` is explicit and requires a stopped service. It makes SQLite-consistent old-store backups, copies tables without rewriting authoritative JSON, retains historical source files, validates and promotes staged stores. The layout marker appears only after verification. Prepared hashes and refusal to overwrite different destinations support interruption/retry.

Data migration does not create new human edits or collapse separate Requirement/SCD versions. Original paths in historical evidence remain historical; local operational descriptors are rebased separately. Recovery evidence stays under `runtime/backups/architecture-v1`. Ordinary launch and application updates never invoke seed restoration or data clearing.
