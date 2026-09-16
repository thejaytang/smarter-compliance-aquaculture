# Installed example material, 2026-09-16

## Result

The normal Workbench at `http://127.0.0.1:62742/` now contains **example**, source `PE001`, snapshot `PE001-001`, material `fb2ab88857c490664724dbad418d2943`. It is pinned first in Material review for the requesting reviewer. The pin is a persistent, actor-specific list preference applied before pagination, while search and task filters still apply.

The saved personal material contains three cases: the supervisor's complex anchoring-line example, the fictional fish-removal illustration, and the user-supplied translated sea-lice illustration. Three completed splitting sessions contain 8, 15 and 14 units. Four primary Requirements have saved six-field interpretations, source references, unresolved questions and derived checking logic. Multi-paragraph sources retain individual original HTML anchors. Nested conditions, nested exceptions and the fish action quantity range [2,3] remain explicit.

These are saved demonstrations, not reviewed legal interpretations or compliance findings. Shared material adoption and material review were not completed. The local authored original has demonstration provenance; its missing official URL remains an unresolved governance item. Training-artifact quality ratings do not assert legal authority, legal currency or translation authenticity. Annex contents and unstated inspection deadlines are not invented.

## Implementation and verification

- Added actor-specific material pinning and a guarded endpoint, with pagination, persistence, filtering and actor-isolation tests.
- Fixed source intake accepting the existing Workbench `peer_sync` field without changing authorization checks.
- Batched splitting previews read a single request-local source snapshot. Final save independently rechecks the current source; a changed source rejects the save without appending history.
- Regression: 267 Workbench backend tests, 286 frontend tests and 30 System1 source-workflow tests passed.
- Normal activation used consistent database recovery snapshots (8 stores initially, 9 after the example personal workspace existed). Existing business rows survived both activations; asset checks and foreign-key checks passed.
- Owning APIs registered the source and explicitly saved content, splitting and interpretations. No business rows were inserted directly.
- Normal browser verification showed example as the first Material review row, all three completed splitting sessions and the saved anchoring-line interpretation at revision 1 with all six fields and Checking Logic.
- The existing user tab and its unsaved PA004 content were not reloaded. AI remains Not connected; automation remains disabled.

## Assets and boundaries

[Bundled example assets](../../workbench/examples/README.md) describe the demonstration. The installed local databases, original-source registration, generated business workbooks, request receipts and recovery snapshots are not included in this code change. Cloning the repository alone does not install the local material record.

This supersedes the example-pending statement in the earlier bulk-edit checkpoint. Whole-document AI Auto-extract, remaining cross-pane acceptance and native Windows desktop verification remain separate work. No real model call or Site Model assessment was performed.

## Subsequent third-pane interaction revision

Each local relationship child now has an explicit **Decompose** action, including a previously completed Condition. It opens that child's own source text and recursive controls. The three relation extraction actions are directly visible. The third-pane Split at cursor and Interpret requirement buttons are removed; selecting a saved Requirement loads the fourth pane. Locate text is placed at the right of each top coloured source header, including collapsed entries, and resolves that entry rather than whichever child happened to be selected.

All 290 frontend tests pass, including child-owned extraction, completed-child reopening, saved-selection interpretation and header-location ownership. Normal browser verification on example exercised the two parallel sea-lice Condition groups, entered C3, and displayed its existing C4/C5 children and all three direct relation actions. Leave prompted before discarding the unsaved preview; saved step 1 remained intact. The first entry's header locator selected its original linked passage. Frontend assets loaded on normal 62742 without another backend restart. Native Windows interaction remains unverified.
