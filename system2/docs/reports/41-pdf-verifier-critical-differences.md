# PDF verifier critical-difference checkpoint

Date: 2026-09-10. Decision: **CONTINUE** within the new [PDF reliability goal](../goals/pdf-verification-reliability-20260910.txt). This checkpoint establishes a bounded engineering improvement, not independently accepted PDF accuracy. The earlier [functional phase](../../../project-support/reports/requirement-workstream-functional-delivery-20260910.md) remains completed under its own scope.

## Inventory and reference limits

The owning governance database and metadata of its ten saved PDFs were read without changing selection or inspecting reserved acceptance content. Only CS004 is currently INCLUDE; six are EXCLUDE and three Pending. The ten files contain 504 pages by metadata, but this is not a processed or accepted sample. CS004 is the existing 134-page native-text development source. Other saved PDFs were not promoted to eligible inputs. Earlier inventory found no representative scanned body in CS004; real scan/mixed-source acceptance remains unavailable in the currently eligible PDF scope.

All 13 historical Requirement Gold samples remain exposed: six active regression and seven active diagnostic. The sample-history SHA256 remains `4f66a2322146f95dae6ace03cd75fb42b26441f02e449aae1bde2deede57b987`. No independent reference owner or new qualifying held-out/calibration material is established. With one eligible, development-exposed PDF, a source-family-separated acceptance claim is unsupported. The user was asked to arrange a small independent human review; unaffected engineering continues while that input is pending.

An initial pypdf metadata read failed on an AES-encoded file because its optional cryptography dependency is absent. Installed Poppler `pdfinfo` supplied all ten page counts successfully. No dependency was installed, PDF decrypted/replaced, full document parsed, new source acquired or selection changed.

## Failure, diagnosis and bounded change

The old comparator split ordered numeric strings into word-token counts and compared only original-to-output. Thus `1.5` and `5.1` had the same counted tokens; `1,500` and `1.500` also matched. Added `not`, an extra word, a negative sign and changed within-line word order could retain every counted original token and produce no finding.

The unchanged real CS004 page 19 was rendered and inspected. Its source SHA256 is `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. Ten frozen controls use positioned original-line observations from the prior development evidence. Two retain text unchanged; eight mutate only isolated output records. They are constructed diagnostic controls, not independent human transcriptions or a real-world error-rate sample.

| Output challenge | Before | After |
| --- | --- | --- |
| Numeric separator change | Missed | Located critical difference |
| Numeric component reorder | Missed | Located critical difference |
| Inserted negation | Missed | Located critical difference |
| Extra ordinary word | Missed | Located major difference |
| Within-line word order | Missed | Located order difference |
| Inserted negative sign | Missed | Located critical difference |
| Removed negation | Detected | Detected |
| Entire original line omitted | Detected | Detected |
| Two unchanged controls | No findings | No findings |

Method `original-page-comparison/2` preserves numeric separators, order and signs, compares output back to spatial original evidence, and checks equal-token single-line ordering. Source/output locations and evidence stay attached. Both comparison directions are coalesced into one issue when they refer to the same located record; reverse evidence remains in the report. Comparisons do not write source facts or assign an accuracy score.

The first implementation raised natural candidate count from eight to ten by duplicating two existing tokenization issues. The second change grouped those duplicate directions, restoring eight candidates without dropping their evidence. These unlabelled natural candidates cannot establish verifier precision or false-alarm rate. No naturally occurring critical error was independently confirmed in this checkpoint.

## Verification and practical boundaries

- Frozen diagnostic result: **8/8 seeded differences detected, 0/2 unchanged controls flagged**; baseline detected 2/8. These fractions describe only the fixed challenge set and are not independent accuracy estimates.
- Frozen real effective-output input: eight candidate findings before and after, with two reverse comparisons coalesced. A fresh standalone call against the unchanged full original, limited to page 19, also returns eight findings and five unverified-scope entries. Acceptance remains `not_assessed` and confidence null.
- The source checker records its new method. Prior method reports become stale on reconciliation, preserving old reports/history and requiring a new comparison. Existing source/result/version protections remain intact.
- Focused source-verification and routing checks passed. Full System2 regression passed **750 tests**, with one existing missing-fixture skip and one existing dependency warning. The source-check frontend passes syntax validation. Tests exercise correction, affected B gating, history, Excel readback, replay and staleness in isolated synthetic stores. This checkpoint did not repeat the actual real-PDF browser repair loop; that remains a later gate for the new findings.
- The first targeted test run exposed a fixture issue: its synthetic original contained only a body, while its output included the internal identifier `clause`. The new reverse check correctly rejected that extra text. The local fixture now omits the unprinted internal label; no real source or Gold answer changed.
- Validation preservation comparison matched all **18 tables in two normal owning stores**, all **73 managed source files**, and all **51 Gold files**. Normal business records were never submitted or cleared. The other normal stores were outside this checkpoint's comparison scope. No external API, material transmission, schedule, commit, publication or full large-PDF run occurred.

Single-line ordering is not page reading-order validation. Table grids/spans, row ownership, controlling notes, cross-page relations and illustration role remain unverified. Broad or ambiguous boxes can still conceal ownership/coverage errors. Multi-page output text without page partitioning explicitly remains unverified for reverse comparison. Shared evidence engines remain disclosed; no confidence calibration or automatic release threshold changed. Human workload measurement still requires an actual reviewer, separate from development time.

## Reproduction and retained evidence

Run from System2 using its existing environment:

```sh
PYTHONPATH=src .venv/bin/python scripts/evaluate_pdf_verifier_challenges.py \
  --cases outputs/runs/pdf-verifier-reliability-20260910/cp41/challenge-cases.json \
  --original ../system1/Data/C_Certification_Scheme/CS004-001_ASC_Salmon_and_Cod_Standard.pdf \
  --output outputs/runs/pdf-verifier-reliability-20260910/cp41/challenge-replay.json
```

The evaluator refuses an existing output path and a mismatched source fingerprint. It reports null independent precision/recall and does not perform acceptance writes. The [standalone checker contract](../contracts/original-verification.md) supplies the raw-original acquisition entry.

Evidence directory: `system2/outputs/runs/pdf-verifier-reliability-20260910/cp41/`. It retains inventory, original rendering, baseline source modules, frozen records and original observations, challenge cases, before/first-fix/final results, fresh standalone output, and before/after preservation reports. The baseline comparator SHA256 is `6d9f4f3bab85790a2e062d757c35aff3d7f7d2ba280b7a9c76a9123dafd95264`; the frozen real-page input is `c3fca2a61612d195a8a1c88e85cdac36369c74d412da234253432f4b0197f96c`. Full regression output is `system2/runtime/pdf-verifier-cp41-regression.txt`. Original PDF, Gold, Canonical and prior outputs remain retained. Restoring comparator code would restore the demonstrated blind spots; it is not a recommendation to restore business databases.

## Next bounded checkpoint

Challenge whether broad output boxes can reuse one occurrence of text to explain several original lines or hide table ownership errors. Design source-side accounting and explicit structural scope before expanding sample volume. Separately prepare the existing workbench's independent-reference workflow once reviewer availability is known; reserve fresh material without opening acceptance labels during development. Real scans and source-family-separated acceptance require suitable governed or separately authorized test material. Missing inputs remain explicit, and the overall PDF goal stays active and incomplete.
