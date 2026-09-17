# Complete cross-page parent and classification history

Date: 2026-09-10. Decision: **CONTINUE** to the consolidated functional-delivery audit. This checkpoint follows the user's [current-stage contract](../../../docs/design/requirement-workstream-stage-delivery.md). It verifies a usable manual alternative to automatic cross-page row joining; it does not establish independent extraction accuracy.

## Actual local workflow

A labelled two-page PDF contains one advisory item: `9.1 Daily check`, followed by `Operators should record water temperature at the inlet and outlet before feeding.` The sentence crosses the page boundary inside a two-column table. The original second-page first-column cell is empty. No external source or provider was contacted.

The actual browser started the ordinary local parser on isolated PA902. It produced 12 source units and three coverage units. Both physical grids and all printed passages were retained. A natural OCR artifact, `oo`, appeared in the empty cell. The reviewer compared both rendered originals and used the table-cell repair to clear it. Automatic OCR tuning was not expanded.

Through the normal workbench controls, the reviewer then:

1. Used page coverage → **Add missing content** to save the complete item with original number `9.1`, title, exact combined sentence and page-1 box.
2. Attached each physical row as **Context**. Both source pages, cell locations and current versions remain dependencies of the complete parent.
3. Confirmed the parent, both physical tables/rows and the relevant page/source coverage. Unknown machine scores remained unknown.
4. Classified physical tables and fragments as context, without another Requirement count. The local rule's `should` suggestion was visible.
5. Saved a deliberately erroneous negative classification, explicitly labelled as a synthetic correction exercise. Opened the current result from Review history, verified the saved negative, and corrected it to Requirement.

At revision **38**, exactly one parent is available: `manual:a9647f2b-83ec-493d-badd-2582b4178740`. There are **18 applied decisions**, including the injected negative and correction, and no draft disguised as history. The source correctly remains **partial**, with eight other A checks and three coverage B judgments unfinished. This checkpoint does not claim complete PA902 processing. Checkpoint 38 already supplies a separate fully completed scan/manual source.

The one-time source setup and regression fixture initialization are engineering evidence, not daily review steps. Every repair and judgment described above was performed in the browser. The 16 minutes 41 seconds from explicit queueing to the final fragment judgment includes tool operation, diagnosis and implementation pauses; it is not a reviewer productivity benchmark. Machine extraction preceded manual review; automatic acceptance was zero for this uncalibrated example.

## Defects exposed and corrected

- Linked source context previously appeared only inside a collapsed repair form. It now appears beside the extracted result, with page labels and **Open linked source unit** buttons.
- History previously retained before/after text but omitted the actual B classification values. New B decisions now persist classification before/after, timestamp and source-version identity in System2. History shows them and opens the current result in its actual A/B stage. A saved human classification is displayed explicitly and preselects its existing value; changing it still requires submission. Older records are unchanged and missing fields are labelled, not reconstructed from guesses. The normal database has **zero** pre-existing B classification history rows, so the omission affects earlier isolated test history rather than normal business classifications. This exercise's correction preserves the preceding negative in its new `classification_before` field.
- The Excel parent initially lacked readable linked context and listed only its own page. The current export includes linked passage text in Context / applicability, both linked pages in Source position, current related-unit versions/boxes in Structure / dependencies, and the document's Canonical binding while identifying the manual origin. Parent/subitem counting is unchanged. Renderer **19** also reserves height for context and title text; the example's row height is 132 points. Native visual inspection of this latest copy remains unverified.
- **Clear cell text** explicitly supports an original empty cell. The browser automation's empty `fill` did not clear an existing value; the explicit button was exercised and the empty overlay was read back. Source cells and the original PDF remain unchanged.

A first UI helper import returned 404 because the server serves an explicit asset list. The helper was moved into the already served repair module; final browser loading on both the isolated and normal entry passed. The first regression fixture omitted a required context reason and was corrected. These failures were not successful submissions or source acceptance.

## Evidence and reliability

Evidence root: `workbench/runtime/cross-page-functional-20260910/`. The isolated service root is `workbench/runtime/cross-page-functional-pilot/workbench/`, port 64002, instance `vNsQJU81nJB_K6sQrtyRIuyDJdA68G9k` at verification. Normal entry remains port 62742.

| Artifact / check | Verified result |
| --- | --- |
| Original PA902 PDF | SHA256 `adbad987188eb0fff1893c61209dfb08ea70aa327115fee493b4f169dea03bf7`; both rendered pages inspected; explicitly synthetic |
| Canonical | SHA256 `ae932f339ccf1a1f2bcc4d3508f2f9fe1de3a9395ece1ea34633f7a7bcea695e`; unchanged |
| Original unit retention | All 15 machine-installed original unit records unchanged |
| Final database/feed | `parent-delivered-readback.json` and `parent-delivered-feed.json`; one complete parent, both context pages, partial source |
| Latest Excel | `complete-parent-final.xlsx`, SHA256 `c85f15077273b14cf64d3532553b1b25266babbbe2ae8657ec7db48a812cc0a7`; synchronized event **39** |
| Excel readback | `final-excel-readback.json`: `PA902!B16` exact complete sentence, G16 both contexts, H16 linked pages, Z16 Canonical/manual origin, AA16 current relation versions/boxes, AJ16 count 1 |
| Office structure | `office-final-validation.txt`: validation passed; latest native visual acceptance not claimed |
| Normal preservation | `normal-preservation.json`: every table in all five stores matches the stopped checkpoint-37 recovery copy; all 73 managed originals unchanged |
| Normal runtime | Actual overview and 50-item CS001 review page loaded; S1 saved/exported revision 1 and S2 saved/exported event 71 remain coherent |

The regression `test_manual_complete_parent.py` verifies the manual parent, negative-to-positive correction, replay, both-page output and source retention. A subsequent physical-cell edit suspends that parent's A/B acceptance and current delivery, preserving its previous text and history. This later-edit check is a deliberate injected regression, not an observed natural source change. The actual browser proof covers saved relationships, classification correction and coherent delivery; prior real-source dependency/recovery loops are reused.

Full System2 regression passed **739**, with one pre-existing missing-fixture skip and one existing Starlette warning. The last context-height-only adjustment passed the 11 directly affected parent/workbook checks. Workbench Python passed **28** and frontend checks **17**. Logs are under each component's `runtime/manual-parent-*`. Tests establish these contracts, not independent quality.

## Remaining boundary

Automatic physical-row continuation and arbitrary column remapping remain future improvements. The verified manual complete-parent alternative preserves physical source evidence and requires the reviewer to classify fragments as context and recheck the parent after dependent changes. It is not a permanent B subdivision rule. Complex-table, scan, original-verifier, weekly and migration evidence is reused from earlier checkpoints. Continue with the final functional matrix, guide corrections and current-state handoff; do not expand automatic-quality tuning or clear business Pending.
