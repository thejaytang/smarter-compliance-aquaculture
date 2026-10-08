# Workbench GitHub synchronization, 8 October 2026

The existing application source on `main` and `developing` matches the published Appendix F application. This update adds an installable complete business seed from the stopped 6 October snapshot to `developing`, and direct Windows clone/install instructions to both branches. No application behavior, schema or live workspace is changed.

The original Appendix F ZIP is valid but contains member paths up to 269 characters. The company-computer extraction error was not captured; long paths are an observed risk, not a confirmed diagnosis. The new instructions clone the repository into a short local folder and restore the compressed seed through the existing guarded, long-path-aware importer.

Fresh macOS dependency installation and PE002 restore/start succeeded. Full restoration retained 89 source records, 76 originals, 157 bindings, 85 Example blocks, 21 Requirements and 21 interpretations. Every table row in the four packaged business databases matches the original handoff. Existing-workspace restoration was rejected. The actual browser opened Sources, Materials and the saved Example with its original and four panes. Fifteen existing deployment, initial-data and platform tests passed. Windows dependency resolution succeeded for all three components.

Native company Windows installation and interaction remain unrun. This is not a claim of Windows acceptance or end-to-end model processing. See `verification.json` for scoped checks and limitations.

GitHub publication is verified at `main` commit `80ba7e2` and `developing` delivery commit `cbed1ae`. An anonymous download of the complete seed matches its SHA-256 and passes ZIP integrity; seven remote guide/manifest files match the prepared bytes. Eight of nine acceptance groups passed; native company Windows acceptance remains unrun. See `publication.json`.
