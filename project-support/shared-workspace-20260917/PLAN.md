# Shared workspace and clean colleague handoff

Authorized on 2026-09-17: remove Materials development work, preserve System1 source decisions, share saved Requirement work across named reviewers, deliver environment rebuild instructions, and merge the verified milestone into main.

1. Share saved Requirement sessions and interpretations. Retain the creating identity as the storage key; record every editor and timestamp in immutable history. Keep source-version and concurrent-write checks.
2. Exchange a shared Requirement graph, including links across authors, and render Group conflicts as readable structure.
3. Stop the local service, create a consistent recovery backup, remove only Materials development state and its exchange artifacts, and verify retained source records.
4. Supply a reproducible Windows rebuild/handoff path, verify local and Windows CI, publish the explicit milestone to main.

No real AI calls. No claim of Windows desktop interaction acceptance from CI alone. Existing unrelated working-tree changes are excluded from the commit.
