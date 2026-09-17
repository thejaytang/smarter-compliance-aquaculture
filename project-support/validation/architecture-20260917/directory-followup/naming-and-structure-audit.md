# Naming and structure audit

2026-09-17. Read-only application/code audit requested with Ponytail. No product files were renamed or edited in this audit, and no service restart, database mutation, commit or push was performed. This report and the current state summary are local development evidence.

## Scope and method

- Inspected the names of all 704 files currently in the application Git index, including bundled assets. Of these, 406 are outside vendor/minified-file locations; 306 are Python files.
- Read active entry guides, dependency declarations, product policy, package/import boundaries and files implicated by the findings. Parsed maintained Python and compared maintained code contents; this is not a full semantic or security audit of every implementation.
- Scanned 101,111 local file names, including retained history. Excluded 76 environment/generated-directory roots such as Git internals, virtual environments, node_modules, runtime cache/backups and bytecode. Dependencies and generated paths are not subject to a custom naming policy.
- Inspected 279 local files under current tests/design/decisions/plans. Existing diagram titles with spaces are human-facing deliverables and intentional exceptions.
- Product Windows-reserved-name and case-folded full-path checks found no conflicts. One retained local historical name (`project-support/validation/legacy-layout/system2/:memory:.ses`) is invalid on Windows. Another 218 local historical paths exceed 240 relative characters; this is a portability review threshold, not proof that every Windows application will reject them. None is in the current product index. No native Windows execution was performed.
- Existing product boundary check passed. It checks inclusion policy, not naming quality, import architecture or obsolete references. No application test suite was rerun for this read-only audit.

## Findings

### 1. An apparent old implementation copy is still a product file

`workbench/backend/system2/src/pdf_extraction/derived 2.py` is the sole Python filename that fails the current lower-case underscore convention. It contains a 9,999-byte implementation, not an identical copy of `derived.py`. No active source/test references to this filename were found. `derived.py` is now a 156-byte deprecated facade forwarding to `delivery/writer.py`; current orchestration and review code use the delivery package.

Recommendation: confirm the retained implementation has no unique required behavior, archive it as development history and remove it from the product index. Do not rename it into a second live module or delete it solely because its name looks temporary.

### 2. Configuration and generated guidance still refer to pre-migration locations

- `.gitattributes:2-5,12-13` still lists old System1/System2, PDF.js and saved-package paths. `git check-attr` reports `text` and `eol` unspecified for the current `workbench/frontend/assets/vendor/pdfjs/build/pdf.mjs`. The generic Python and launcher newline rules do work. The old vendor-specific protection no longer covers the current location; this audit did not establish changed bytes or broken rendering.
- `workbench/backend/system2/pyproject.toml:54-55` configures `tests` and `../workbench/src` relative to the System2 component. Both locations are absent. Current tests are under `workbench/tests/system2`. Explicit invocations can pass while these default discovery paths remain obsolete.
- `workbench/backend/system1/Code/src/system1/workbook_presentation.py:40` still tells users to consult `system1/PROJECT_STATE.md`, which is absent and excluded from the product. Root product guides must be used instead.

Recommendation: repair these references before another product distribution; retain old paths only in explicit legacy migration/recovery branches and historical evidence.

### 3. Physical module separation does not yet establish ordinary Python package boundaries

`workbench/backend/application/local_workbench/__init__.py:6-7` extends its package path into sibling `shared` and `system3` folders and mutates `sys.path`. `shared/workspace.py:10-16` and the System1/System2 SQLite bridge modules search ancestor directories for shared code. The bridges depend on the full Workbench checkout even though System2 also declares a separately buildable wheel.

This supports the current local launcher and does not by itself prove a runtime failure. It does make import ownership, standalone component expectations and developer tooling less explicit. Identical `sqlite_support.py` bridge files exist in shared and System2; the actual storage implementation is centralized in `workspace_storage.py`, so this is not duplicated database logic.

Recommendation: define and test the supported launch/import contract, then use explicit package imports and one declared shared dependency mechanism. Keep separate component environments where required. Do not add independent services or a generic plugin framework for this cleanup.

### 4. The shared folder mixes reusable mechanisms and application orchestration

`shared` contains 37 files. In addition to identity/storage/platform helpers, it contains source task orchestration (`source_workflow.py`), intake, material scheduling, collaboration and recovery. Some cross-system collaboration belongs here, but a source-specific workflow is not a general-purpose helper. The application folder currently has only five files; its server handles many routes and coordinators.

Recommendation: retain genuinely cross-system infrastructure under shared; keep domain rules with their owning system and application-level scheduling/adapters with application. Move only demonstrated responsibilities, not all files with a source/material prefix. No directory proliferation is needed merely to meet an ideal template.

### 5. System1 retains a redundant capitalized Code layer

System1 uses `backend/system1/Code/src`, while System2 uses `backend/system2/src`. `Code` is the only uppercase directory in maintained product paths. It is a consistency/maintenance issue, not a Windows filename error.

Recommendation: when performing the next focused path migration, flatten `Code` into `system1` rather than rename it to the equally redundant `code`. Update adapter paths, dependency locations and environment rebuild steps together. Never rename a live virtual environment and assume its embedded paths have changed.

### 6. Large files are review candidates, not automatic split targets

The largest maintained files include System2 `canonical.py` (3,271 lines), the application `server.py` (1,076) and `shared/collaboration.py` (971). Size alone does not justify a rewrite. Split only where independently maintained responsibilities or repeated changes demonstrate a useful boundary; the server's routing and coordinator wiring is the most direct candidate. This is lower priority than stale paths and ambiguous ownership.

## Naming convention recommended for adoption

| Category | Convention | Examples/exceptions |
| --- | --- | --- |
| Ordinary product directories | Lowercase descriptive names; hyphens for multiple words | `project-support`, `frontend`, `contracts` |
| Python modules/import packages | Lowercase, underscores where needed | `workspace_storage.py`, `pdf_extraction` |
| Frontend source and styles | Existing lowercase hyphen convention | `requirement-source.js`, `four-pane.css` |
| Current project documents | Keep established root entry names; other documents use lowercase hyphens | `README.md`, `AGENTS.md`, `storage-and-exchange.md` |
| Config/contract resources | Lowercase descriptive names, existing extension conventions | `config.example.json`, `default.yaml` |
| Tests | Preserve current runner convention | `test_workspace.py`, existing `test_*.mjs` |
| Local records/reports | One readable topic/date convention | Existing `topic-20260917` folders; avoid new mixed `final`, `new`, `copy`, `2` variants |
| User launchers | Explicit, human-readable platform labels | `Open Workbench (Windows).cmd`, `Open Workbench (macOS).command` |
| Original materials, database IDs, archives and vendor files | Preserve source/vendor identities and recorded names | Do not impose code naming rules on evidence or third-party distributions |

Do not rename APIs, database tables, persistent IDs or old manifests as a cosmetic filename cleanup. Keep `runtime` and `workspace` separate. Do not flatten the four business databases or combine incompatible environments for visual symmetry.

## Conclusion and priority

The top-level product/development/data boundaries are suitable for the stated local collaboration workflow. The entire implementation is not yet uniformly organized: active old-copy and stale-path findings remain, and Python import ownership is transitional. Prioritize (1) the old implementation copy and stale references, (2) explicit imports and responsibility boundaries, then (3) redundant Code nesting when a validated path migration is warranted. Do not perform a repository-wide naming rewrite.

## Primary guidance checked

- [PEP 8: module/package naming and consistency](https://peps.python.org/pep-0008/#package-and-module-names). Python naming guidance; backward compatibility and local consistency matter more than cosmetic uniformity.
- [Python Packaging: src versus flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/). Explains import-path behavior and tradeoffs; it does not mandate one directory tree for every project.
- [Microsoft: naming files and paths](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file). Platform naming constraints, distinct from aesthetic naming preferences.
- [Git attributes](https://git-scm.com/docs/gitattributes). Attributes apply by path pattern; old patterns do not protect relocated vendor paths.
