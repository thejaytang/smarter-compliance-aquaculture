# Saved example publication

User authorised publishing the current example work to main on 2026-09-18. Published commit `b221b162b767c6f93a46ea9886cff472b52a695e`, preserving incoming main commits `7c5be3d` and `bf8920a`. Remote main readback matched; developing-win and developing-only-jay were not pushed.

## Saved scope

Captured a coordinated snapshot through the running Workbench export API at 08:54:14 UTC. Derived a scoped, supported logical Collaboration ZIP containing PE001 source/review, the current example material, and its shared Requirement bundle. Original graph IDs/ancestry and evidence were retained, with a new package ID. No unrelated source heads, materials, raw databases or runtime settings were published. Both PE001-003 and PE001-004 original HTML files are retained for source ancestry.

The package contains material revision 12, 27 blocks, three Requirement sessions with seven saved history versions, and zero saved S/C/D interpretations. Two entries remain in progress. Browser-only edits are not captured; the inspected in-app tab showed Saved but was older than the API snapshot. The full local snapshot used for preparation stays local.

## Verification

Restored the immutable original seed into an isolated temporary receiver; imported the scoped ZIP through FullSnapshot preview/apply as Ana Jokic. All 27 blocks, three Requirement UUIDs, units, roots, Group structure, source segments, text and source identities matched. Repeated apply, restart readback, and reopening PE001 by source ID passed. All 88 source records remained. Eighteen material-collaboration tests passed against the published code, including a new superseded-evidence roundtrip and invalid-status rejection regression. Product boundary and naming, exact-file staging and whitespace checks passed. Native Windows was not executed.

Two actual blockers were fixed on main: import validation omitted the legitimate superseded candidate status, and incoming commit bf8920a had removed the Snapshot import still used by MaterialService._pin. No history was stripped to bypass validation. The live Mac development checkout and runtime were not switched to main.

Users must pull main and import workbench/resources/examples/example-work-20260918.zip through Collaboration preview and explicit apply. Git pull alone does not replace local work. The original initial-data archive is unchanged.
