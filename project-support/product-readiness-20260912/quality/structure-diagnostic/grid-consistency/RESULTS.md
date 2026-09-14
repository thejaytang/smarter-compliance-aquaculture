# Grid consistency diagnostic

**A native-line crossing ratio distinguishes the six known wrong fine header grids from eight real table regions in these DEV windows.** This is a calibrated development diagnostic, not independent quality acceptance. No product edit or parser rerun occurred: the existing frozen page PNGs were processed with the same grid functions, and all 15 reconstructed grids, merged-cell specifications and cell texts exactly matched their retained candidates.

## Definition and observed ranges

For each accepted table, use original nonempty `text_lines`, not newly split words. A captured line has its center in an actual merged-cell rectangle. Count it once if its bbox extends more than **1 point** beyond an internal edge of that owning merged cell. Edges inside a merged cell do not count. The denominator is all captured native lines in that table. A zero denominator is unmeasured.

| Region | Shape | Crossing lines / captured lines at 1 pt |
| --- | --- | --- |
| Farm p28 Criterion band | 1×14 | 2/4 (50%) |
| Farm p28 Indicators band | 1×8 | 1/1 (100%) |
| Farm p29 Criterion band | 3×18 | 4/4 (100%) |
| Farm p29 Indicators band | 1×8 | 1/1 (100%) |
| Interpretation p19 header | 1×16 | 2/2 (100%) |
| Interpretation p20 header | 1×16 | 2/2 (100%) |
| Audit pp1,2,3 real tables | 32×4; 23×4; 26×4 | 6/123; 2/97; 8/107 (2.06–7.48%) |
| Salmon/Cod p18 main table | 5×2 | 0/20 |
| Salmon/Cod p18 metadata table | 2×4 | 1/9 (11.11%) |
| Multicolumn synthetic table | 3×2 | 0/6 |
| Cross-page synthetic tables | 3×3 each | 0/8 each |
| Borderless/figure synthetic false 1×1 table | 1×1 | 0/2, **missed** |

The observed separating threshold range for a `>= threshold` rejection is **(11.11%, 50%]**. A provisional **25%** criterion lies within that interval. At that value it would reject the six known wrong fine grids and retain all eight real table regions here. This is not a reported precision/recall score: the rule was developed using these exposed DEV cases, and legitimate regions still contain cell/merge defects.

All four predeclared geometry tolerances (0, 0.5, 1, 2 pt) retain the wide separation. Absolute crossing distance is unsuitable: Audit has legitimate-region conflicts up to 179.33 pt, larger than the false header-grid maximum 91.92 pt. Rejecting a table for **any** crossing would discard all three Audit tables and the Salmon metadata table. Audit crossing evidence includes merged headings/footnotes and at least one native line joining text from two genuine columns; preserving the table does not certify those rows.

## Partial outside capture and fallback

No table has a center-captured line extending outside its overall bbox by more than 1 pt. At zero tolerance, two Audit pages have one tiny outside line each; the maximum is 0.228 pt. These samples therefore do not validate behavior on materially clipped tables. Full per-line overflow distances, owner-cell boxes and all four tolerance counts remain in `results.json`.

Each diagnostic record preserves the exact native line payloads that current table suppression hides. A rejected grid should be retained as rejected evidence and replaced by those positioned lines, with an unresolved range and source comparison available. This counterfactual fallback has not yet been loaded into product code. Native fallback still includes occluded text where the PDF contains it; this guard neither validates visibility nor creates headings.

The false 1×1 figure-as-table remains a known failure because it has no internal boundary. Borderless table detection and isolated bad rows inside largely valid tables remain separate gaps. A crossing ratio is a consistency check for an already proposed grid, not a universal table detector.

## Next bounded experiment

Freeze **1 pt and >=25%** before testing an isolated `/4` parser copy on these same DEV windows. Reject only the inconsistent candidate grid, preserve original line IDs/text/bboxes and explicit rejected-grid evidence, expose an unresolved table range, and verify all eight real table regions remain unchanged. Do not tune the rule on reserved documents or claim independent acceptance from these DEV outcomes.

Evidence: [frozen definitions/input hashes](freeze.json), [all grids, ranges and exact native fallback](results.json), [summary/proposed criterion](summary.json), [reproducible diagnostic](diagnose.py). Input/code/Gold hashes were unchanged at measurement completion. Source-rendered real-table checks used Audit pp1–3 and Salmon/Cod p18; the three synthetic true-table regions are supported by their existing cell Gold.
