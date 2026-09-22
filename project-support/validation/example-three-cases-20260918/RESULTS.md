# Three English example excerpts

Updated locally on 2026-09-18 at the user’s request through the existing upload, source re-review and manual-replacement APIs. Current source: PE001-004, material `f5e03bbd741dc49d6cf1e7541fe58593`.

- Sea lice: exact English text recovered from the user’s initial message in “讨论第二段拆分” (`6aa82545-920c-83eb-9a46-6a7a7b737914`). Both paragraphs retained, including weekly seawater measurement at three metres, both temperature/frequency branches, broodstock exemption and Annex 1.
- Operational journal: existing excerpt and all three chapter links retained byte-for-byte inside the new document.
- Internal control: translated the user-supplied § 5, preserving all eight listed duties, the documentation paragraph and the final second-/third-paragraph reference. Marked as working English translations for training.
- HTML check: three sections and eleven list items (three operational, eight internal-control); source receipt hash matches registered bytes. Previous PE001-003 hash and contents unchanged.
- Real browser: Materials retains example as its first entry; opening it displays the three English sections and final written-documentation sentence in the first pane. The existing simplified reader renders the a–h ordered list as 1–8, although the retained HTML uses `type="a"`. No new extraction, Requirement or SCD annotations were generated.

During replacement, source re-review initially returned HTTP 503 because its configured `runtime/backups/sources` directory was missing. Re-created that directory and retried the same saved request ID successfully. No source history or database was reset and no application code was modified. No Git commit/push or initial-data package update was performed.

## Git publication

On 2026-09-18 the user authorised publishing to main and developing-win, then explicitly cancelled Jay-branch synchronisation. Published identical commit `e15db28299c15fc665e2dfe34cbc298a460a16a6` to both branches with an atomic, non-force push. Remote readback confirmed both exact IDs; developing-only-jay remains `6fe77f9d99ffcf21f3609fa3e6fa48b17aa4512c`, and no developing-jay branch was created.

Published only the training HTML under `workbench/resources/examples/example.html`, its import instructions, guide/rule pointers and the narrow exact-file allowance in the product boundary checker. Product index/naming, disallowed private-path rejection, exact HTML SHA-256, three sections, eleven list items, three chapter links and whitespace checks passed. No initial-data files changed. Existing Windows installations must explicitly replace the example source using the documented source-review workflow; pulling code never replaces local databases or annotations.
