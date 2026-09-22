# ABC reading view validation · 2026-09-22

## Result

The fourth pane shows three modules only: program-combined extraction followed by a Set expression for Scope/A, Condition/B and Demand/C. Linked concepts that occur in the expression are quoted inline; saved wording, nested AND/OR/NOT and unknown definitions are preserved. Unmatched labels remain in the existing editor rather than being added as another concept list or guessed synonyms. The footer shows B ⊆ A and B ⊆ C.

Set disclosures open the existing editor and its review notes. Global Edit, Evidence, More, separate concept summaries, general review-question output and data-integration panels were removed from the reading view. Save and AI Gen remain; each module retains its explicit approval. Final confirmation is shown only when saved approvals and existing semantic gates permit it, and is hidden after new edits. No backend, schema, dependency or business-data change.

## Checks

- 387 frontend tests passed (`frontend-tests.log`). Checks cover escaped concept labels, exact matches versus word fragments, existing quotes, nested negation/disjunction, selection, retained source text, separate candidate adoption, save behavior and conditional final confirmation.
- The actual Chrome view of PE002 / R4 was inspected. All three extraction blocks and Sets are visible in the reading flow, with 0 visible form controls. Demand concepts are quoted inline; the program-combined Norwegian wording remains distinct. Opening and closing the Demand editor retains `R4 · Saved · Review pending`. No live approval, save or model generation was performed.
- At the existing 1144-pixel browser width, the existing keyboard horizontal scroll exposes the fourth pane fully. Set text wraps inside the column and Save remains accessible.
- An isolated browser fixture used the production frontend modules and a local in-memory API stub. Three approvals followed by Save retained three approvals and `reviewed: false`. Editing B invalidated B only, updated its displayed expression and enabled Save; A/C stayed approved and final confirmation was hidden. One AI Gen action produced three separate candidates; approving A replaced A only. This is frontend interaction verification, not a new backend persistence or real-model acceptance test.
- All six files present under the business database directory stayed byte-identical (`business-preservation.json`), including the four canonical stores. The permanent Example remains unchanged and pending human review.
- Changed product files passed `git diff --check`. The original law HTML was not edited. No commit, push, PR or publication.

Before-edit copies are retained here to distinguish this change from existing local work. The synthetic server and tab were stopped after testing; the live R4 tab remains open for review.
