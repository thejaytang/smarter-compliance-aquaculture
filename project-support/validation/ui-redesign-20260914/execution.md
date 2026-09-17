# UI redesign execution

## Current checkpoint

2026-09-14: local UI delivery complete under the user-approved API-placeholder scope. Code baseline captured with SHA-256 manifest in [baseline/manifest.json](baseline/manifest.json). Implementation occurs in candidate/ to avoid serving partial frontend changes from the normal live service. Component environments are symlinked to their existing owning environments; no new dependencies installed. Baseline is a code recovery point only, not a consistent cross-store business backup.

Live health reads confirmed normal coordinator 62742 and prior isolated coordinator/reviewer 55542/58814. Old fixture work is preserved and not reused for new mutations. A new isolated fixture was created from the existing engineering builder. Before local promotion, protect active drafts and capture an appropriate business recovery point.

User decision: content-level archive is permitted, explicitly labelled Content finalized · Requirements unfinished. No semantic processor/schema is added.

## Rolling work

- Parent: source review/register/history/intake frontend, integration, fixture and state/verification.
- Shell: candidate index/app/style and navigation helper; single-row shell and six routes.
- Materials: candidate material/collaboration UI, permanent three-pane frame, list/detail, archive interaction.
- Intake: candidate governed source intake/discovery API and owning-service validation/tests.

## Acceptance checklist

| Item | State | Evidence / next check |
| --- | --- | --- |
| Recoverable baseline and independent candidate | PASS (code only) | baseline/manifest.json; no engineering business decisions; see bounded historical asset repairs below |
| Six-module navigation and compact shell | PASS (candidate) | Actual six routes and 44px global row; material-browser-evidence.md |
| Source intake and API integration placeholder | PASS (clarified scope) | Manual URL intake verified; duplicate/version owning tests PASS; automatic discovery provider unavailable |
| Source review, register, action history | PASS (candidate) | source-browser-evidence.md; original/scoring/save/apply/history UI verified |
| Material editing, three panes, save/resume | PASS (candidate) | material-browser-evidence.md |
| Content-only archive, re-review and conflicts | PASS (scoped) | TS002 explicit adopt/archive r2/unchanged review; retained conflict/revision tests |
| Weekly mechanics and deduplication | PASS (disabled by default) | weekly-material-inspection-evidence.md; no normal schedule activated |
| Browser widths, zoom, keyboard and density | PASS | 1280/1440/1920 and narrow overflow PASS; true Chrome 200% PASS; zoom-acceptance.md |
| Regression and preservation/recovery | PASS (code rollback and stores); full assets INCOMPLETE | 187 frontend / 182 Workbench / 145 System1; verified activation-checkpoint, six SQLite snapshots; unreadable historical assets block full package |
| Normal local launcher and loaded version | PASS | Root launcher restarted normal 62742, PID 45944; normal-loaded.json binds loaded code; actual Sources and Materials navigation loaded |

Runtime endpoints and changing implementation status belong here until verified promotion. Do not treat code snapshots, test fixtures or this checklist as product acceptance.

## Recovery preparation and observed failures

The normal service at 62742 was exited through its UI after checking no queued/running/waiting requests, no currently opened normal materials and no other available normal browser tabs. Its displayed 87 sources / 38 eligible originals were read only. No business rating/adoption/archive was performed in normal stores. The candidate's TS003 PENDING action and TS002 archive r2 exist only in the independent fixture.

The initial code-only inventory omitted binary PDF vendor assets (fonts, CMaps, wasm and licenses). Candidate assets were restored from the project's existing vendor directory; recovery source inventory now includes all vendor files, with a regression. The full PDF routes/manifest test passes. Source PDF.js now actually renders TS003's selectable page 1 and scanned page 2; the prior native iframe was black and is recorded as a failed visual check.

Backup attempts encountered stalled/early local reads; length checks rejected truncated content instead of issuing a successful receipt. A known 1,068,926-byte JSON file was read completely three times with stable SHA-256 `8e2516eb2d312a4346ab0c94e46fed571141890612244cb94f00aa1b70aff3fa`. The reader now performs sequential complete-file reads, bounds retries and validates byte length, content before/copy/after and database integrity. Tests retain premature-EOF, size-change and timestamp-only cases. The underlying filesystem cause is not claimed established.

An escalated retry was automatically rejected because 20+ GiB runtime totals had not been distinguished from backup scope. The read-only exact size projection in recovery-size.json established 8,390 files and approximately 2.50 GB total including code; old recovery directories are excluded. An actual-inventory free-space guard was added and tested before writing. Re-review accepted the same bounded local backup after this evidence. The backup remains unverified until its manifest reports complete.


## Local activation and recovery boundary

The normal root launcher now serves the promoted `ui-redesign-20260914` version at http://127.0.0.1:62742/. [promotion.json](promotion.json) records the 31 changed/new code and test files with before/after hashes. [normal-loaded.json](normal-loaded.json) records PID 45944 and an empty `parent_source_changes`; startup fingerprint is `85790778253724dabb8ea5922cfa5fe35fe71dcde0ea724181525f84029070b8`. Actual normal browser reload showed four source modules with the existing 35-source review queue, followed by two material modules and the 38-material review list. No normal source selection, content save, adoption or archive was performed. The new material inspection configuration is absent and the dispatcher stays disabled.

Full historical resource backup did not complete. The final attempt failed on `attempt-5/native/crops/p0011_paragraph_0008.png` under the retained `ecd506cd90695697577fcca2065a0a49` artifact. It has no two readable package copies satisfying the exact hash/Canonical checks, so restoration stopped. Do not call the failed attempt a usable recovery package. Earlier unreadable derived images/raw outputs were moved intact into `unreadable-retained/` and replaced only from agreeing hash-bound historical copies with identical Canonical bindings. [restored-historical-crops.json](restored-historical-crops.json) and [restored-crop.json](restored-crop.json) record those bounded repairs. Original PDFs, Canonical, Gold, review decisions and stores were not modified by these repairs. The underlying filesystem cause remains undiagnosed.

The scoped activation checkpoint avoids making a code-only UI update depend on repairing unrelated historical assets. [activation-checkpoint/manifest.json](activation-checkpoint/manifest.json) contains 706 exact code/test/asset entries and six SQLite backup snapshots taken under all owning writer locks with the normal service stopped. All copies/hashes and SQLite integrity checks passed before promotion; [checkpoint-result.txt](checkpoint-result.txt) is the successful receipt. This is a same-workstation code rollback plus database snapshot, NOT a full historical-asset or portable recovery package.

To roll back this activation: exit the normal service, run the workbench environment on [rollback_code.py](rollback_code.py), then reopen the root launcher. It verifies the current promoted hashes and retained baseline before changing code, preserves the newer files in `rolled-back-code/`, and refuses later edits. It never restores databases or changes originals/history. Database snapshots are retained for manual recovery assessment, not automatic replacement of newer business work. The rollback script was actually executed on isolated copies of all 31 promoted files. It refused a simulated later edit without changing files, then restored every prior hash (or removed a newly introduced file from active code while retaining it) and preserved every newer hash. [rollback-validation/result.json](rollback-validation/result.json) records PASS. It was not executed on the normal workspace.

The locked-Mac blocker is resolved. Actual Chrome 200% and restoration to 100% are recorded in zoom-acceptance.md. Independent activation and isolated rollback verification are complete. The user subsequently confirmed API-placeholder delivery: source_workflow.intake_capabilities remains unavailable and provider_extensions retains its Protocol. The normal UI requests adding a search API service. No credentials were requested in chat, and no live search is claimed. Automatic discovery remains unavailable and material weekly dispatch remains disabled; neither is reported as a connected live workflow.


## Final decision

The user explicitly deferred live search to an API service and requested a missing-API prompt. The normal UI now displays that prompt and disables execution. [completion-audit.md](completion-audit.md) maps all 11 acceptance items to inspected evidence; local delivery is complete within that clarified scope. [normal-loaded-final.json](normal-loaded-final.json) binds the final loaded parent/UI and promotion hashes.
