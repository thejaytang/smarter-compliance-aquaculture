# Workbench architecture migration

Status: implemented locally; final verification is recorded in [RESULTS.md](../validation/architecture-20260917/RESULTS.md). User request: 2026-09-17 architecture attachment. This is a storage and ownership refactor, not a UI or semantic redesign.

## Checkpoints

1. Stop the known local service and preserve source code plus consistent SQLite backups. Inventory business tables, original hashes and existing authors/times.
2. Introduce a workspace layout, four owning business stores, cross-store validation, and explicit repeatable migration. Preserve all saved JSON and historical identities.
3. Move product code under frontend/backend; preserve Python import compatibility without duplicate implementations. Consolidate launch/setup in deployment.py.
4. Extend existing logical Collaboration merge with coordinated database snapshots, authoritative history exports and a verified manifest. Add a separate read-only downstream delivery.
5. Run local regression, fault/replay and cross-workspace journeys; activate only after preservation checks. Remove development/sensitive paths from the Git index without deleting local files. Update product guides.

## Storage mapping

| Existing owner | New owner |
| --- | --- |
| System1 governance and assessments | workspace/databases/system1.sqlite |
| System2 main and personal workflow databases | workspace/databases/system2.sqlite; preserved branch namespaces |
| Workbench requirement_* sessions, steps, requests, units and structure projections | workspace/databases/system3_requirements.sqlite |
| Workbench interpretations, frozen origins/citations, catalog and candidate records | workspace/databases/system3_scd.sqlite |
| Workbench logins, execution queues, local policies/settings | runtime/state and runtime/settings |
| Original and retained processing evidence | workspace/sources, with inventoried paths |
| Collaboration exchange graph and receipts | System2-owned shared exchange journal; packages under workspace/packages |

Each saved JSON/history remains authoritative; relational structure/origin tables remain derived indexes. Cross-file references are validated explicitly. Attached SQLite transactions use rollback journals for atomic Requirement/SCD changes; the export coordinator reserves all owning databases before backup. No active WAL database is copied as a regular file.

## Acceptance

Preserve source IDs, original bytes, authors/timestamps and nested JSON; retain SCD v3 binding after Requirement v4; support explicit save/reopen/conflict/replay; round-trip new and legacy logical packages; keep credentials and operational logs out of business packages. Native Windows checks require an available Windows host and must not be inferred from earlier CI. No new cloud CI or business-data upload is authorized by this plan.

## Physical directory closeout

The follow-up applies the requested layout to the complete local `05` directory, not only the Git product index. Root duplicates and unused setup wrappers are archived; development evidence is grouped under design/decisions/plans/validation; caches move into runtime. See the [location mapping](../decisions/layout-20260917.md). Component environments and dependency declarations remain with their owners.
