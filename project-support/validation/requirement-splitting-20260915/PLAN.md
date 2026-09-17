# Manual requirement splitting

Authorized 2026-09-15 in the current task. Implement the user's fixed unit template inside the existing material Requirements pane. This supersedes the earlier deferred-manual-schema boundary, not the disconnected automatic extraction or Site Model boundary.

- Bring a whole saved text block into an independent, source-bound personal splitting session.
- Work outside-in: split outer statements and establish their relationships, then extract fields and recursively group their linked units.
- Scalar k means exactly k direct children; [min,max] is an inclusive range. Nested groups count once. Field content is terminal; never automatically subdivide it or rewrite passive/negative wording.
- IDs link requirements under extracted headings, not chapter objects. Persist units, source bindings, sessions and step history in Workbench SQLite; server-bound actors and revision checks protect saves.
- Each explicit splitting step saves independently. Retain original content, historical versions and separate material review/archive state. Automatic extraction remains unavailable.

Validation: isolated store and HTTP checks for arithmetic, source fidelity, references, replay, stale edits, actor isolation, undo and reopen; frontend integration and actual browser outside-in flow. No business reviews, external services, Git operations or automation. Native Windows acceptance is separate.

## Checkpoint

The manual flow has passed an actual isolated browser run through complete passage splitting, including an exception and a nested min–max condition group. Full frontend regression passes 245 tests; full Workbench backend regression passes 217 tests. A source-only optional-module test now excludes unrelated vendored binaries from its temporary import fixture. The design detector's single warning concerns a pre-existing PDF region image that is populated at runtime, outside this change. [Results](RESULTS.md) record normal Workbench activation and final boundaries.

Independent scope: current collaboration ZIPs do not include the new personal requirement tables. The editor and user guide explicitly disclose local-only storage. Automatic recognition, machine learning, downstream compliance, and native Windows acceptance are not claimed.
