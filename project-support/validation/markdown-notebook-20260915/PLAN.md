# Markdown notebook content editing

Authorized 2026-09-15. Replace the dense Extracted content block forms with vertically stacked Markdown cells, following the user's Jupyter Notebook clarification. Keep source block boundaries and ordering with lightweight separators. Render by default, edit one cell's Markdown at a time, and provide only essential formatting, cell and source actions. Deletions use red background plus strikethrough, additions use green background. A Markdown baseline persists independently of Save so saving cannot erase redlines.

Use locally bundled markdown-it for parsing/rendering and jsdiff for text differences. Native textarea editing provides plain Markdown and keyboard selection; Shift+Enter renders a cell. No hosted editor or external model is needed. Preserve material IDs, source refs, personal drafts, history, concurrent-write guards, review declarations and the Requirements intake. Store Markdown and its baseline within the owning material block, which already travels through material history and collaboration snapshots. Keep complex original table merges in the recorded original; warn when converting their edit representation to a simple Markdown table.

Validate format/security, persistence/history, no accidental confirmation, and a real isolated browser edit/save/reopen/requirement-intake flow. Activate the normal Workbench only after preserving current stores and checking pending work. Native Windows acceptance remains separate.

Completed: [Results](RESULTS.md) record passing tests, isolated browser behavior, actual-source body selection and normal service activation.
