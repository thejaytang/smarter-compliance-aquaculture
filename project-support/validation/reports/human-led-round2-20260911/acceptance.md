# Human-led workbench: round-two acceptance

Date: 2026-09-11. Status: **COMPLETE for the approved second-round local scope**. This report implements the [approved plan](../../plans/human-led-workbench-round2.md) within the [human-led material goal](../../design/human-led-workbench-goal.md). It does not redefine business content acceptance or the deferred Requirement schema.

## Implemented behavior

- Runtime status distinguishes source access, material extraction, saved storage and the existing export/legacy workers. Durable sanitized failure/recovery events, last successful checks, uptime and infrastructure backoff supplement the compatible health endpoint. Viewing status does not submit work.
- Material and history lists return compact, paginated metadata. Candidate and conflict details load by material-bound identity. Additive indexes are rebuildable projections; saved material bodies and immutable history remain authoritative.
- Bound originals stream from verified files, including PDF byte ranges. Reader caches include source digest, reader version and requested range. Excel reads stream OOXML without evaluating formulas; empty/hidden sheets and unavailable native styling remain visible limitations.
- Reading mode, block editing, whole-content search, chapter navigation, linked original locations and PDF region selection support human correction. Large tables render bounded windows while retaining the complete saved table.
- The server calculates affected review scopes and preserves only provably unaffected human checks with their provenance. Content edits, withdrawn checks and source invalidation cannot silently carry forward active content confirmation.
- Explicit stopped-service backup includes the five owning stores and the optional existing Jobs store, required originals/Canonical/material resources and a separately verified archive of actual source/dependency declarations. Isolated recovery is an inspection path, with writers and background workers disabled.

## Evidence and gates

All engineering writes use isolated fixtures. The normal workspace is inspected and backed up separately, without synthetic material confirmations or source decisions.

| Gate | Evidence | Current result |
| --- | --- | --- |
| Scale baseline | `workbench/runtime/round2-acceptance/scale-materials.json`: 100 registered materials, initially 20 versions each; one material has 10,000 blocks | Verified |
| Representative originals | Synthetic 300-page PDF, 20,000-row/30-column Excel, 1,000-chapter HTML, native/scan/blank PDF control and public PA001/CS010 copies | Verified through isolated HTTP; final browser cases recorded separately |
| Latency | [Measured performance](performance.json), [final v6 cold and repeated reads](reader-v6-cold-and-repeat.json), [previous reader baseline](reader-baseline.json); 30 samples per repeated metric | Passed; the final Excel cold open plus reader is 3.69s with the complete adopted 600,000-cell material already saved |
| Actual browser | [Browser evidence](browser-evidence.json), [large-table cell comparison](large-table-ui-readback.json), screenshots linked by case | Passed actual large-draft recovery, 10,000-block search, two-tab conflicts, old-client 426 protection, source switching and reload after service restart |
| Interrupted processing and source-input protection | [Fault evidence](fault-evidence.json) | Interrupted candidate resumed with the same identity; changed-input result remained stale; human body and prior attempt artifacts retained |
| Explicit failed-parser retry | [Fault evidence](fault-evidence.json) | Failure remained recorded; idle polling did not retry; explicit Extract created a separate candidate |
| Lost save response | [Fault evidence](fault-evidence.json) | Complete POST sent, client closed before reading response; independent readback and identical retry proved one saved revision and preserved body |
| Restart preservation | [Fault evidence](fault-evidence.json) | Tested restart retained material, revision, candidate, receipt and conflict tables; another restart is included in the continuous run |
| Full backup/source recovery | `workbench/runtime/round2-recovery-six-stores/evidence.json` | 311 archived source files, 51 resource files and six stores verified; six saved materials/history/confirmation and bound PDF reads passed without the original data/package directories |
| Continuous real-time operation | [Operation groups](soak.jsonl), [timed result](soak-result.json) | Passed: 3,600.007 real seconds, 60 groups, zero failures; two controlled service restarts during the run |
| Large-response memory | [Controlled diagnosis](memory-diagnosis.md), [actual HTTP allocation samples](parent-memory-diagnosis.json) | Dynamic JSON allocation reproduces bounded RSS growth/reclamation; no response-sized Python object accumulation observed, and reused threads do not improve it |
| Normal preservation and loaded version | [Normal maintenance/load](normal-load.json), [preservation comparison](normal-preservation.json), [normal browser](normal-browser-evidence.json) | Passed: backup verified twice, final code loaded at the normal origin, six components have actual successful checks, normal browser inspected; 73 originals, 75 Canonical artifacts and existing business tables preserved |

## Interpretation of the tests

Final full regressions: System2 989 passed / one skipped / one existing dependency deprecation warning; Workbench Python 55 passed; frontend JavaScript 76 passed, including duplicated-tab ownership and repeated fallback recovery. System1's unchanged source passed its existing 108 tests earlier in this round. The final Workbench rerun after the WAL fix is recorded in `workbench/runtime/round2-acceptance/workbench-post-wal-tests.txt`; the earlier 54-test full log is retained separately. Test counts are supporting evidence, not substitutes for browser, preservation or timed-operation gates.

The skipped legacy integration test is `tests.integration.test_real_pdf_preflight::test_supplied_pdf_is_fully_preflighted`: its user-supplied `_PS3_副本.pdf` is absent from the project root. It is not reported as a pass. Current-scope public, native/scan/blank and 300-page reader cases have their own evidence. The warning concerns the existing Starlette/httpx test dependency; no dependency installation was performed to suppress it.

| Measured operation | Result on this machine | Gate |
| --- | ---: | ---: |
| Material summaries, 30 samples | p95 0.60s | <=1s |
| Historical summaries, 30 samples | p95 0.26s | <=1s |
| Save 10,000 blocks, 30 samples | p95 0.91s | <=5s |
| Cold open plus 300-page PDF reader, final v6 | 0.89s | <=5s |
| Cold open plus 20,000-row/30-column Excel reader, final v6 | 3.69s | <=5s |
| Cold open plus 1,000-chapter HTML reader, final v6 | 1.04s | <=5s |
| Repeated PDF / Excel / HTML reader, 30 samples each | p95 0.30 / 0.30 / 0.28s | <=1s |

The earlier Excel reader-only baseline was 14.64s. The final Excel reader-only cold check is 2.91s; its table above additionally includes 0.78s opening the already-saved full material. The final cache check explicitly removed only matching derived cache entries into retained evidence before measuring. These are selected fixture measurements, not universal bounds for every file of the same page or row count.

Acceptance found and corrected genuine edge cases: immediate Extract during material switching, oversized browser-local drafts, stale previous-original display during reader loading, copied-tab journal identity collisions and repeated fallback recovery, automatic reactivation of old confirmation after source restoration, explicit withdrawal of an association check during confirmation, missing backoff for a failed source-export status probe, omission of the Leader database from the backup reservation set, and SQLite backup verification creating WAL sidecars. The final backup fix explicitly closes connections and uses immutable reads only for completed standalone snapshots; a source with committed rows still in WAL is backed up and restored without losing those rows. Repeated verification leaves the package unchanged. The first failed and intermediate normal packages are retained; the designated final package passed two independent verifications with six stores, 8,388 business/resource files and 311 source files. Regression tests and actual browser cases retain the failure/retest distinctions.

The timed run alternates two isolated materials every minute and exercises save, idempotent replay, stale concurrent rejection, current readback, history, bound reader and material identity. It ran from approximately 19:50:50 to 20:50:50 UTC using real elapsed time. It includes two controlled restarts with table-hash preservation checks. This was a phased integration run: a temporary allocation tracer was enabled for memory diagnosis between restarts, then removed; final UI/backoff corrections were validated separately and loaded during the run. It is not a claim that one immutable final build ran unchanged for the entire hour. The isolated fixture enables the material worker and disables source/export/legacy background workers; those workers are checked after normal loading. Worker interruption/retry and source restoration have separate explicit fault cases. Synthetic scale measures responsiveness and state protection, not document-extraction accuracy.

Browser evidence comes from actual isolated Chrome interactions. HTTP response checks do not substitute for rendering or interaction checks. Initial CUA unavailability on the locked Mac is retained in the evidence record; subsequent Playwright-driven Chrome supplied the browser checks.

The final normal service uses the standard launcher at http://127.0.0.1:62742/. The isolated test service was explicitly stopped after its checks; its stores and evidence remain available. Normal preservation permits new maintenance/browser sessions and additive rebuildable indexes; all pre-existing business table hashes and every original/Canonical hash are unchanged. No normal material workspace or content confirmation was created. During the normal System1 navigation check, existing code submitted an identical saved draft without a form edit; final readback verified all ten draft rows remained byte-identical to the baseline. This is recorded as an observed idempotent navigation write, not described as a completely write-free browser session.

The recovery exercise reused the existing component environments and loaded recovered source. It is not a fresh-machine installation test. The package preserves source and dependency declarations but excludes installed environments, downloaded models and browser-local unsaved drafts. A restored inspection workspace is not automatically a replacement operational deployment.

## Deliberate limits

- Single local user with multiple tabs. Remote/team deployment is outside this round.
- Content review completion is distinct from structured Requirements. The final nested structure, forms and semantic processor remain **Not connected**, and Process stays disabled.
- PDF scanning does not trigger OCR. HTML reading disables scripts and external assets. Excel reading does not reproduce native styling/charts or calculate formulas. Original files remain available.
- A bounded hour of operation and passing regressions do not establish multi-day stability, parser fidelity or completed business review.
- No publication, external transmission, Git commit/push, new schedule, model activation, credit reset or removal of protected history was performed.
