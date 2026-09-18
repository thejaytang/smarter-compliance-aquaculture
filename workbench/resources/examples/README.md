# Workbench training example

Open [example.html](example.html) in a browser. It contains three English excerpts: sea lice, operational journal records, and § 5 on internal control. These are working translations for training, not official English legal texts. The sea-lice text includes the previously supplied temperature measurement, counting branches, broodstock exemption and Annex 1 reference. The operational journal excerpt is unchanged. All eight duties and the documentation requirements from the supplied § 5 are included.

## Use in an existing Workbench

Pulling application updates downloads this file; it does not replace local sources, databases or annotations. The initial-data archive is unchanged. Do not restore that archive over an existing workspace.

1. Save any browser edits. In **Sources**, open **example (PE001)** in the source register and choose **Request review**. Enter that you are updating the training example, then choose **Create pending review**.
2. Open its pending source-review task and choose **Supply authorised original**. Select `workbench/resources/examples/example.html` (on Windows, `workbench\resources\examples\example.html`).
3. Check the file, confirm its identity and permission, explain that this is the three-excerpt training update, and choose **Confirm and apply**.
4. Return to **Materials** and open **example** from the list to use the current source version. Older saved work remains bound to its previous source version; it is not silently transferred.

Use the named reviewer authorised to apply source updates on your installation. Colleagues can also exchange the updated source through the existing Collaboration review process. Do not copy SQLite files between installations.

This file matches local demonstration snapshot PE001-004 from 2026-09-18. SHA-256: `307a53d4645e6c5569b1b66fd169f770236fc90ae2630567718eaff8fe0d0475`. A receiving installation allocates its own next source-version identifier.

The repository fixes this HTML file to LF line endings on Windows and macOS so that Git checkout preserves the documented checksum, including when `core.autocrlf` is enabled. This rule does not rewrite existing registered originals or saved material versions.
