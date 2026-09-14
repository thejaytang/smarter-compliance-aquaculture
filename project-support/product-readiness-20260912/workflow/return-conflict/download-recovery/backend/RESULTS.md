# 1. Durable collection-download HTTP recovery

**PASS in isolated HTTP tests: 7 new tests and 4 related route/reviewer tests.** Product/browser delivery to Downloads remains a separate root-agent check; these tests establish authenticated retrieval of retained package bytes, not completion of a browser download.

## 1.1 Contract

- `GET /api/collaboration/collection-download?id=<UUID>` returns only an existing `sent_collection` package owned by the currently selected authenticated reviewer. Read-only restored-inspection mode remains rejected. Invalid/unknown/multiple identifiers fail.
- Existing `POST /api/collaboration/collection-export` and `POST /api/collaboration/collection-download` retain behavior and ZIP payloads, adding canonical `Content-Location: /api/collaboration/collection-download?id=<UUID>`. UUID validation prevents arbitrary/header-injected locations. Export filenames remain unchanged; saved downloads retain `review-<UUID>.zip` for GET/POST parity.
- The GET enforces the existing exact local Host, rejects explicit foreign Origin/Referer and cross-site/same-site Fetch Metadata, and uses the existing port-scoped session identity with a read-only lookup. Unknown/no session is refused without creating even an anonymous session row. Authenticated direct address-bar/no-referrer navigation remains supported; POST Origin/CSRF checks are unchanged.
- `/package-download.js` is in the static whitelist. The actual HTTP startup import graph verifies its delivery as JavaScript with exact source bytes.

## 1.2 Evidence

[focused-01](focused-01/result.json) ran seven actual local HTTP tests with real isolated Store/Collaboration databases. Checks include owner/other actor/no session/unknown cookie, exact bytes/name/headers, repeated GET and compatible POST, actual receipt export plus idempotent replay, malformed/unknown/duplicate/extra ids, incorrect Host/cross-origin/referrer/fetch-site metadata, inspection mode and POST CSRF. Database dumps and every saved package hash were unchanged by downloads and rejected requests. A retained material revision/adoption record was included in that snapshot.

[related-http-01](related-http-01/result.json) passed the actual app import graph and three existing reviewer-mode HTTP tests. Both runs retain exact argument vectors, source/asset fingerprints, logs and stable before/after bindings. All test databases and HTTP servers were disposable; no normal business service/store was operated.

## 1.3 Changed files and recovery

Only `workbench/src/local_workbench/server.py`, new `workbench/tests/test_collection_download_http.py`, and the focused graph assertion in `workbench/tests/test_frontend_module_routes.py` were changed by this backend task. Root owns the corresponding UI helper and copy. [final-code.json](final-code.json) records final hashes. Exact pre-change server/graph-test bytes and hashes are retained in [pre-change/manifest.json](pre-change/manifest.json); the new test did not exist before this task.

Server SHA256: `fabaf8713318fa6c7619a60b025bdb35ac56911d7fdf2502d4c90772a3c7b599`.

The changes were not loaded into any existing service by this task. A root-owned isolated restart and real browser check are still required to verify the visible recovery link and actual file delivery.
