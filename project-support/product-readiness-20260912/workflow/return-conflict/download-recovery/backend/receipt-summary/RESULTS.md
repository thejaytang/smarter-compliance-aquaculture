# 1. Retain the entered adoption-receipt summary

**PASS: 9/9 focused actual HTTP tests, stable before/after code binding.** New receipt collections now store the supplied summary using the existing 4000-character convention. When the field is absent, the old default `Explicit per-item adoption receipts` remains. Explicit empty input remains empty. The change affects only new freezes; matching request replay returns the exact retained ZIP, and an altered request using the old ID is rejected by the existing binding.

The focused tests inspect actual exported ZIP metadata for exact multilingual text and newlines, exercise default/empty/over-limit input, compare download/replay bytes, and recreate a pre-fix frozen artifact whose entered summary was lost. That historical artifact is not rewritten. Database and saved-file snapshots plus the receipt's retained material history remain unchanged during replay/download. The historical missing-summary limitation is preserved rather than silently repaired.

Only `workbench/src/local_workbench/collaboration_collection.py` and `workbench/tests/test_collection_download_http.py` changed. `server.py` was fingerprinted and remains unchanged. No business service/store was operated, and no service was restarted or current runtime-loading claim made.

- [Pre-change exact backup and hashes](pre-change/manifest.json)
- [Command and before hashes](focused-01/invocation.json)
- [Full output](focused-01/unittest.log)
- [Result and after hashes](focused-01/result.json)

Collection source SHA256: `1e7aeb8c70fdbf028d9c5bc8326f99f55358773610ebfe631b42e8b1507b48b2`.

This is focused regression evidence only. The prior full Workbench run remains bound to its prior code; actual future receipt export and visible summary confirmation are separate root-owned UI checks.
