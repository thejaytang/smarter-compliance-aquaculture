# 1. Authorized operation and result

On 2026-10-09 the user requested merging the locally retained complete snapshot into the existing Example-only workspace. The normal browser Collaboration flow was used, with the selected browser actor Ana Jokic and package sender Weijie Tang. Existing author identities and history were preserved.

- Input: `workbench/initial-data/workspace-20260922.zip`, captured 2026-09-21 23:02:45 UTC.
- SHA-256: `cd5d033e4cfa10ae91838589b773720d9388918122cb43058d1fa61f9bb05bc0`.
- Package: `8ca47f11-7bd3-4539-b7ea-4dbee796cd6c`.
- Synchronization receipt: `2c99f94c-1c29-4d1d-89b6-d48f0da46c20`, status `applied`, 189/189 records.
- Browser confirmed `Synchronization complete. Saved work and history are retained.`

The preview had 183 new, three unchanged and three conflicting records. Two PE001 material conflicts compared empty local historical placeholders with saved incoming content (22 and 27 blocks). The Requirement conflict included eight additional PE001 sessions and five additional interpretations. All 36 common sessions and interpretations were compared: differences were delivery-origin metadata, local revision rebasing and corresponding references/history, not human wording or structures. Imported versions were selected explicitly in the preview; local prior revisions remain retained.

# 2. Interrupted import and recovery

The original sandbox-launched server could not access validation staging. The package passed the owning full validator outside the sandbox; the service was stopped normally and restarted outside it.

The first apply stopped after 31 records at PA012. System1 publication and original verification used ordinary Windows paths. The fix uses the existing shared `FilePath` boundary, compact same-directory immutable temporary names, and long-path-aware original availability/download checks. A native isolated regression reproduced the original failure and then passed with exact original bytes and idempotent replay.

The resumed import stopped after 82 records because PE001's operation payload had been truncated to Excel's 32,767-character cell limit by the in-memory compatibility adapter. The retained incoming request reconstructs 44,388 characters; the stored 32,767 characters matched that exact prefix. SQLite-backed adapter reads and new operation writes now preserve the full string. A regression covers a larger JSON payload, replay, bridge reads and subsequent owning-store save.

With the service stopped, [the narrowly scoped recovery script](repair_sync_payload_20261009.py) backed up System1 using its owning backup method and restored the full payload using the owning version-guarded save. It verified the request/package/record identities and exact prefix before writing. No original, operation or historical row was deleted. The earlier truncated value remains in audit history.

- Repaired operation: `SYNC-7bf55632-249e-5039-9bc3-a03452b19ee9`.
- Recovery revision: 84.
- Backup: `workbench/runtime/backups/collaboration-20261009/system1-before-payload-repair.sqlite` and its immutable template companion.

The same synchronization receipt resumed from its recorded progress and finished normally.

# 3. Verification

| Check | Result |
| --- | --- |
| Source register | 89 sources, confirmed in database and browser |
| Received originals | 76/76 SHA-256 checks matched the immutable package manifest |
| Material documents | 3 saved documents; browser queue shows 39 eligible materials |
| Requirement sessions / interpretations | 44 / 41 |
| Pre-existing material history | All 5 row hashes retained; now 12 rows |
| Pre-existing Requirement steps | All 93 row hashes retained; now 153 rows |
| Pre-existing interpretation history | All 77 row hashes retained; now 164 rows |
| Received source/material/Requirement/SCD history | 288 / 26 / 70 / 87 immutable events |
| Current source-operation JSON | All payloads parse successfully |
| PA012 original through browser HTTP | HTTP 200, 140708 bytes; SHA-256 `15cc7d1de65ea3277121031dd0c7e4d7b44ea7950fdfbd38df7d402255860e68` |
| System1 targeted tests | 31 passed: `test_source_snapshot`, `test_governance_store`, including inherited collaboration checks |

The 39-item Materials queue is not the full 89-source register: current eligibility and saved source decisions continue to apply. No parsing, AI processing, source retrieval, review completion or archive action was requested or initiated by this merge.

The full repository suites, stopped-workspace `deployment.py verify`, and a post-merge full export were not run. Source snapshot validation, durable apply receipts, received-original hashes, prior-history hashes and native browser checks establish this merge's verified scope. No commit or publication was performed.
