# PDF Review Transaction Contract v1

Entry points: `GET /jobs/{job_id}/review-context` and `POST /jobs/{job_id}/reviews/guarded`.
Currently supports block/span/cell text decisions and page labels, not structural split/merge, omitted-content insertion, page-completeness decisions or HTML writes.

## Request and decision scope

Requests contain UUID `request_id`, `expected_revision`, `expected_canonical_sha256`,
`expected_source_sha256` and a named `decision`. Clients obtain results and versions from the same context response.
Version mismatch or busy locks return 409. Replaying an identical request ID/payload returns its original applied revision; reusing an ID with different content is rejected.
This is not an authentication contract. Future shared-workbench integration must bind operators on the server, not trust client-provided names.

`accept/modify` confirms only targeted text; it does not close structural, page-completeness or semantic-ownership issues.
`reject/unreadable` records human action while retaining source-fidelity work; it must not promote the result to accepted.
Repeated tokens, missing locations or overlapping spans must not be resolved by guessing the first match; block-level confirmation remains necessary.
Body changes require existing Requirements to be reverified. With no complete block-to-field dependency graph, conservatively mark all existing document Requirements instead of guessing a local recomputation scope.

## Writes and recovery

1. Acquire the nonblocking `.review.lock` in the current Canonical directory.
2. Preserve old Canonical in `review-revisions/<unique-id>/`; generate new Canonical, derivatives, complete audit projection, verification explanation and receipt.
3. Validate the model/references, recompare current Canonical bytes, then atomically replace Canonical via a temporary file. This is the commit point.
4. Current Canonical references the new revision's derivatives. Retain old exports and revisions.

Pre-commit failure leaves current Canonical unchanged. Retain orphan revisions for diagnosis; retries create a new directory.
Only revisions reachable through the current Canonical receipt chain are committed. An orphan receipt is not success.
Receipts bind request, predecessor and new Canonical payload hashes; replay verifies historical hashes.
Independent machine reports retain their original versions. `review-verification.json` describes this human action and current blockers, not a rerun of machine verification.

Consumers must follow Canonical `artifacts` references rather than treating old same-named root exports as current.
The `/quality` endpoint follows current references. Original source-batch indexes describe the original parse; human revisions use receipts and must not claim the original parse hash.

## Compatibility boundaries

Legacy Python `apply_review_decision/correct_page_label` and HTTP interfaces remain compatible but lack the full transaction version guarantees. They cannot serve future production workbench writes.
The bundled standalone review page uses guarded endpoints. It is not the shared workspace workbench or a secure multi-user deployment.
Validation covers in-process failures, replay, stale versions and cooperative locks. It does not establish power-loss recovery or concurrency safety against writers ignoring locks.
