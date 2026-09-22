# Fourth-pane concept cards

Implemented locally on 2026-09-21; no commit, push or release.

- Three Scope/A, Condition/B and Demand/C cards edit their rule trees directly. Shared object/assessment context is above them; supporting information, original mapped wording and previous explanations are disclosed inside each card. The summary is B ⊆ C; data integration and complete JSON remain collapsed.
- Local concepts have stable IDs, types, proposed/confirmed meaning, exact source quotations and leaf references. Meanings are independent of Site Model bindings. Source changes invalidate interpretation/mapping confirmation, reset concept confirmation when context is refreshed, and identify rules affected through concept-only citations.
- One generation action requests a structured draft. Each candidate card is compared and accepted/dismissed independently. Existing edits remain until explicit adoption; generated concepts are always proposed. Real provider execution was not invoked.
- Old `/1` and `/2` records and deterministic historical projections remain readable/importable. The optional `/2` concepts extension supplies rule-derived current definitions while retaining all six historical explanation/evidence fields. No database migration or old-record rewrite.

## Validation

- 335 Workbench tests passed in the owning environment. After final dependency-impact changes, 42 affected backend tests and the 15-test continuity suite (including the new concept-only citation test) passed. Logs retained here.
- 351 frontend component tests plus 26 `test_*.mjs` checks passed; final 22 affected frontend checks passed.
- A synthetic isolated live UI verified shared concept identity/name propagation, confirmation, new Event creation, source quotation attachment, explicit draft save, separate interpretation confirmation, subsequent rule edits clearing review, and page reload readback. The synthetic record has five revisions; prior explanation remains intact.
- Two isolated running services verified full four-database package export/import, receiver re-export, restart and exact design/fields/logic/history readback. See `exchange-result.json`. Both isolated services were stopped.
- The live workspace passed stopped integrity verification and restarted at `http://127.0.0.1:62742/`. Changed product/test files pass whitespace checks. The byte-exact original example HTML retains pre-existing upstream whitespace.
- Direct browser inspection confirmed the real Example's three cards, concept types, source quotations, nine open concept questions and disabled confirmation while those questions remain. No new browser console or external-provider claims are inferred from these checks.

## Permanent Example

A coordinated local four-database recovery package was captured before live changes (`backup-receipt.json`). R9 (`e0660b90-6d65-5c8d-a91d-04145628fe5f`) gained nine model-prepared proposed concepts in interpretation revision 3: facility, salmonids, seawater setting, slaughter cage at a slaughterhouse, temperature, measurement, depth, weekly frequency and atFacility. All quotes were checked against saved context. No human confirmation was asserted.

All 35 saved interpretation fields and exact Requirement revision bindings remain unchanged; the other 34 check designs remain unchanged. The full-law Material remains revision 3. Original HTML SHA-256 remains `9334a78a021971411e5c8826a2bb16aab1db707d778f6249c9a36b0afc90a4a1`. Readback and preservation results are retained here. The older full-law review artifacts describe their earlier interpretation snapshot; `r9-after.json` is the current R9 extension evidence.

Real model-provider calls, actual Site Model execution and native Windows execution were not run. The AI service and Site Model remain unconnected. Local concept confirmation does not certify legal interpretation or prove compliance.
