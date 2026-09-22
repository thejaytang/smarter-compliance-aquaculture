# Product and full-development separation

2026-09-22. Preparation is in progress; no branch was committed or pushed in this milestone.

The user explicitly chose the same public repository for full development content. The requested product `main` will carry only the application and the permanent PE002 Example. This is a current-tree boundary, not removal of previously published history or privacy for the public development branch.

Remote main `47ee24a15149c8e1050166b4f7dcbb2a2a6afa51` was fetched and checked out separately at `/private/tmp/smarter-compliance-main-20260922`. Its bilingual GitHub presentation is preserved. The active development checkout was not switched or cleaned.

The owning live export API produced the coordinated full snapshot recorded in `full-export-receipt.json`. `scope_example.py` derives only PE002 source/review, its material and its source-bound Requirement/interpretation histories. Rebuilt snapshot graph fingerprints preserve the retained ancestry while excluding unrelated Requirement sessions; source/material values and authored annotation histories remain unchanged.

`build_example_seed.py` created a separate empty System1 store from the existing workbook fixture's structure after clearing its fictional source rows in a new copy. Owning migration and Collaboration import populated the isolated workspace with PE002 only; a coordinated export then produced `example-seed-20260922.zip`. No production database was edited to remove records.

`verify_example_seed.py` passed fresh restoration, exact block/annotation readback, restart and refusal to overwrite existing work. The seed contains one source/original, 85 body blocks, 21 active Requirements and 21 active interpretations, with removed-entry history retained. `example-package-audit.json` confirms the logical inventory contains only those four PE002 record keys and the empty template retains no fictional sources. Live human approvals were not advanced.

The audited Example seed and logical package are now copied into `workbench/resources/examples/`, with exact checksums. The complete coordinated export is retained as `workbench/initial-data/workspace-20260922.zip`, with checksum and manifest, alongside the unchanged 2026-09-17 archive. Full-seed restoration passed with 76 originals and 157 bindings; it refused to overwrite existing work. See `full-seed-verification.json`.

Current branch rules and guides now enforce Example-only `main` and explicit full-data exceptions on development. Five boundary tests pass; unaudited archives, runtime data and unapproved workflows remain rejected. Original `example.html` is now marked `-text` in Git attributes to preserve bytes on all platforms.

The isolated main preparation index contains the audited Example resources/guides and excludes the old complete seed and old PE001 package, whose local files remain intact. The staged product boundary and all three Example hashes pass; the incoming bilingual presentation assets remain intact. See `main-preparation-audit.json`. This is a preparation index only: final UI/product code transfer, complete validation, milestone commits/push and remote readback remain pending. No branch was switched in the live development checkout.

The prepared main index also passed all 38 local Markdown guide links against tracked files/directories, without relying on excluded files left on disk; see `main-guide-links.json`. Final product transfer must rerun this check if guides change.

Backend/product-contract changes were subsequently copied through an explicit twelve-path list. A fresh candidate in a Unicode-named directory was materialized from the preparation index only, so excluded local files left in the preparation checkout could not satisfy imports or restoration. The candidate contains no initial-data directory, development tests/records or old PE001 package. Its own backend restored the Example seed successfully, checked the sole PE002 original and all 170 saved bindings, and refused a repeated restore without changing any business database. See `main-index-seed-verification.json`. The current staged product boundary passes. This verifies the prepared backend and seed; final UI transfer and release acceptance are still pending.
