# Four separate example Requirements

Corrected on normal 62742 on 2026-09-16. The user clarified that the four passages must remain four separate Requirements. The prior demonstration incorrectly repeated the lead-in inside R2–R4.

Current material remains PE001-003 (`3069f79e2481e4c18f1e268c8344de9f`). Original HTML/Markdown and saved material text are unchanged. R1 retains its identity and first passage. New R2–R4 each contain only the corresponding list item, with no copied Subject/modal/main verb or shared condition annotations. R1 links these three complete entries using Subrequirement All 3. The [2,2] location group and [5,5] health-result group remain intact. Fourth-pane Logic explicitly explains the shared context from R1. Previous combined entries remain recoverable in Removed entries with their histories.

Readback verified exactly four active sessions, one source segment and one root per entry, exact source text and fragment offsets, the three live links, nested counts and four current saved interpretations. Browser readback confirmed standalone R4 wording and four Rx entries. Test actions did not save annotations.

The correction exposed an interpretation-context bug: historical reference_evidence was traversed after unlinking, so retiring an unlinked entry blocked R1 as a stale reference. Context now traverses only current structural references, including recursive references; cached historical evidence remains intact. A regression exercises linked-revision rejection, unlinking, retirement and successful parent context reconstruction. All 32 interpretation-related backend tests pass. Controlled activation preserved business records across the 12 discovered SQLite stores. The parent interpretation was then explicitly saved against the corrected current context.

No live AI, Site Model query or native Windows interaction was used. Portable example normalization and README document the revised boundaries.
