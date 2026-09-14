# Original-side comparison and repair checkpoint

Date: 2026-09-10. Decision: **ADJUST**. The explicit Requirement Workstream goal resumes authorized reversible implementation after the earlier pause. This report establishes a bounded engineering loop, not completion of the first multi-format acceptance checkpoint or the overall goal.

## Scope and gap diagnosis

The earlier completeness gate masks parser-provided regions and can exempt a full-page image. A missing body line within a broad table/scan box can therefore be untested. The added [standalone comparison contract](../contracts/original-verification.md) starts from the original page instead, reports unmapped text and residual raster regions, and preserves all unresolved scope. Existing PDF/HTML/XLSX processing and previous repairs remain available. System1 authority has not migrated and System3 semantics were not implemented.

Poppler native text and Tesseract raster observations are separate acquisitions from the current effective-output projection. They are not independently validated ground truth, and can share engines with extraction. The report discloses shared/unknown lineage and leaves confidence null. No externally hosted model was activated.

## Evidence populations

| Population | Scope | Result and limitation |
| --- | --- | --- |
| Real development material with natural errors | CS004 original pages 19, 20 and 123, already exposed in earlier development | Original-side comparison produced 8, 7 and 7 baseline candidates respectively. These are candidates, not verified error counts. A previously corrected page-19 table spelling removes one candidate in the latest pilot. |
| Real original with a seeded omission | Complete footnote 5 on CS004 page 19, in an isolated copy only | The preserved original unit was marked superseded to simulate total absence from effective output. All original text/positions were retained. The checker found the omitted note body, ending and marker. |
| Synthetic acquisition controls | Existing born-digital multicolumn and scanned-critical fixture PDFs | Local native/OCR acquisition works; the shared Tesseract engine is disclosed. These are synthetic documents, not real held-out scans. |
| Synthetic transaction controls | Deterministic isolated workflow fixture with known source observations | Detect, invalidate prior delivery, correct, reject stale resolution, recheck, accept A, classify B, publish corrected text and export; replay and stale-write checks also passed. This establishes transaction behavior, not real-source classification quality. |

The real original is `system1/Data/C_Certification_Scheme/CS004-001_ASC_Salmon_and_Cod_Standard.pdf`, SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. Document ID: `ecd506cd90695697577fcca2065a0a49`. No gold annotations, manifests or held-out reference answers were changed. Development, calibration and final held-out labels are not yet an accepted real-source reference set.

## Actual browser and Excel loop

The pilot copies the latest `workbench/runtime/pdf-hierarchy-pilot` runtime to `workbench/runtime/original-verifier-pilot`, using SQLite backup and retargeting only the copy's owned paths. It retains all 38 documents and prior pilot history. Its registry is isolated; registered originals remain read-only. System1 random QA is disabled in the pilot configuration. No new scheduler was activated.

1. Original page 19 check saved at revision 115. Seeded omission recorded at revision 116 with original unit `pdf:812fc34243da26a3c32b2fda` preserved, plus a pre-fault database backup.
2. The check at revision 117 found 10 candidates, including the three planted missing-note signals. The normal completeness panel prepared the positioned missing-content form.
3. The browser restored the full original text, including its note number and final word: `5 Farm sites can choose whether to use redox or sulphide. Farms do not have to demonstrate that they meet both.` The operator note explicitly identifies Codex's isolated engineering test, not a production human acceptance.
4. Draft revision 118 did not accept content. Applied repair request `fef948f8-55db-4470-a624-62c58b73ea80` saved revision 119. The old comparison became stale. Rechecking at revision 120 removed the three missing-note signals, leaving 7 unresolved candidates.
5. The background worker generated Excel event 143 without a synchronous export call. OfficeCLI located the text in CS004 B618/B619. Native Microsoft Excel displayed the complete new note at row 618 with `Not delivered`, and the retained old row 619 with `Superseded`. Both remained pending; the source banner showed zero available Requirements.
6. The final instrumented check saved revision 121, event 144, with exact comparison-input evidence and tool versions. Its report ID is `764f9a89d2b64df3dd36a6dd5b7cefae53d98910d8be8e63efe7cbec1d26f99e`. Findings remain 7 and unverified-scope entries 6. Real A/B source acceptance was not performed.

The desktop 1440 × 1000 browser check showed original left/result right and a correctly positioned highlight over the page-19 header. Unclassified visual regions offer inspection rather than a misleading missing-text correction. Narrow views stack comparison content; ergonomic acceptance by the intended human reviewers is still required.

## Failures and measured bounds

- Installed Poppler 26.04.0 crashed on `pdftotext -bbox-layout` for this real source's metadata. A bounded TSV acquisition succeeds and retains word positions; neither the original nor the tool installation was changed.
- Real page-19 header wording is correct visually, while native acquisition splits `Aquacul ture Stewards hip C ouncil`. Footer labels are spread across multiple extracted records. These remain explicit tokenization/fragmentation conflicts, not silent corrections or accuracy claims.
- Dark table backgrounds and edge decoration produce residual-ink candidates. Their role requires inspection; they are not confirmed body-text omissions. Grid, merged cells, footnote/cross-page ownership, reading order, insertions and token order remain unverified.
- The system Python could not perform the pilot SQLite backup. The owning project Python/SQLite 3.50.4 passed `quick_check` and made the backup. Use the declared project environment for recovery.
- Device: Mac16,12, Apple M4, 16 GiB memory. Seven selected-unit HTTP reads measured 0.470–0.729 seconds under the active isolated workload. This is a small observed sample, not a validated p95 bound.
- The instrumented original-page request took **8.1101 seconds end to end**; its **2.758-second** precommit comparison time excludes final state application and reconciliation. Ordinary human-decision latency and human review time were not measured here. Current conservative source hydration needs targeted profiling.
- Seeded Excel-lock failure: database event 144 was immediately visible as saved while Excel remained at 143/pending. The worker then reported `failed`, preserving the earlier snapshot and saved state. After removing the artificial lock, the **100-second recovery test timed out** while the worker was still refreshing. A later independent read confirmed automatic recovery to event 144 and matching saved/exported versions. The failed timing assertion is retained; eventual consistency does not pass that timing target. The target document's proposed 60-second ordinary convergence budget is not established.

## Validation and preservation

System2 full regression: 688 passed, one pre-existing missing-fixture skip; the existing Starlette deprecation warning remains. The seven added original-verification tests also passed after the evidence-bundle assertion. Workbench Python: 22 passed, including pending/current/failed/unknown version checks and mismatched cached-download rejection. Existing frontend: 17 passed; updated modules pass syntax checks. Updated entry, state, guide, contract and plan links were also checked: 243 local references resolved before the final System1 state cross-links. These checks establish their engineering invariants, not source accuracy.

The normal service was reloaded on retained port 62742 after database and registry backups. Before/after table digests match for every System2 and Workbench table: 38 documents, 15,120 review units, 0 System2 human-review rows and 0 deliveries. Source registry bytes and CS004 original hash are unchanged. Both new UI modules are served. A fresh normal browser loaded System2 original-page inspection, displayed `Check this original page`, and showed saved event 71 / Excel event 71 synchronized, without invoking the check or selecting an actor. Creating that browser session is not a source or review decision. The enlarged isolated original retained the exact page-header highlight. No production check, source review, new parsing batch, provider, weekly schedule or deployment outside this local workstation was initiated.

## Evidence locations and recovery

Local-only files are retained under `system2/tmp/original-verifier-pilot/`: baseline page JSON, `seeded-omission.json`, `before-seeded-omission.sqlite`, `after-repair-page19.json`, `after-repair-records.json`, `repair-history.json`, `standalone-page19.json`, `verified-sync-snapshot.xlsx`, `runtime-check.json` (including the timed-out recovery observation), and `eventual-recovery.json`.

The native-checked event-143 workbook SHA256 is `80ed563f0c8e2de0b0f1e4d66dd7580ea2cfa34805b2d1f333589933c29c38a7`. Automatically recovered event-144 workbook SHA256 is `c1269ff05ce86a4288bf25fe7b5cb3284f8c4c67b81ab8fab2934193f7d9b0fd`; its corrected content was unchanged by the added machine check. Its exact source evidence is in the pilot workflow's `source-verification/0940bc122d851b312d968b693083a441cb7de20414f4b8d11ac157b18aba1192.json`.

Normal-service backups and complete table/hash comparison: `workbench/runtime/original-verifier-release-backup/{before.json,after.json,source-before.json,system2.sqlite,workbench.sqlite,Requirement_Source_Registry.xlsx}`. These are retained restoration artifacts, not an instruction to overwrite live data. Restore only at a stopped-write checkpoint and preserve later human changes. Source originals require no restoration because they were not modified.

## Remaining acceptance and next decision

Continue according to [the active execution plan](../../../docs/plans/requirement-workstream-implementation.md). First isolate export and state-application latency, then complete the real scan and complex/cross-page verification loop with independent reference labels. The reference owner was requested from the user and remains unresolved. Do not label the scan fixture, this browser engineering run, existing table repairs or regression success as independent held-out acceptance.

System1 database migration, B's configurable provisional split/count policy, calibrated dimension scores, independent precision/recall and verifier error rates, the new weekly A/B sampling rules, safe local reparse, human effort and optional same-sample API uplift remain outstanding. The overall goal is active and incomplete.
