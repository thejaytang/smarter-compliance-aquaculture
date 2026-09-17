# Smarter Compliance Workbench

This is Jay’s `developing-only-jay` branch. It retains the application, business snapshot and development materials. Colleagues should use `main` for product updates. This branch is in the same public repository; its name does not make it private.

A local, human-led workspace for governing sources and preparing traceable Requirements and check designs. It runs on your own computer and opens in a browser.

This directory is the application root. Its visible entries are the five root guides, the two launchers, `deployment.py`, `project-support/` and `workbench/`. Local development is grouped under `project-support/{design,decisions,plans,validation}`. Old entry points and development helpers are retained there as historical evidence rather than active application folders.

## 1. Start here

- [User guide](USER_GUIDE.md): daily review, manual saves, Collaboration and fixed deliveries.
- [Environment guide](ENVIRONMENT.md): first installation, migration, updates and recovery.
- [Agent instructions](AGENTS.md): the single guide for local VS Code Copilot and other coding assistants.
- [Storage and exchange contract](workbench/contracts/storage-and-exchange.md): four databases, version bindings and package format.
- [Review contract](workbench/contracts/review-workflow.md): the existing four-pane workflow and source semantics.

Double-click **Open Workbench (Windows).cmd** on Windows or **Open Workbench (macOS).command** on macOS after setup. Both call `deployment.py`. The [initial business snapshot](workbench/initial-data/README.md) is included for this one-time handoff and imported explicitly once; an ordinary launch or application update never imports that seed again.

## 2. What is stored where

| Location | Responsibility | Included in application Git updates |
| --- | --- | --- |
| `workbench/frontend/` | Pages, components and bundled browser assets | Yes |
| `workbench/backend/` | Application, System1, System2, System3 and shared code | Yes |
| `workbench/contracts/`, `workbench/config/`, `workbench/deployment/` | Product contracts, sanitized templates and deployment helpers | Yes |
| `workbench/initial-data/` | Immutable first-handoff business snapshot and checksum | One-time authorized snapshot |
| `workbench/workspace/` | Business databases, originals, exported human history and packages | README only |
| `workbench/runtime/` | Private settings, execution state, recovery backups, diagnostic logs and cache | README only |
| `project-support/`, `workbench/tests/`, `PROJECT_STATE.md` | Development plans, tests and evidence | This development branch only |

System3 uses the Workbench process and has two independently versioned business stores. It is not a separate service. The four panes remain Original document, Extracted content, Requirements, and Interpretation & Check Design.

Collaboration exchanges saved work through a preview and explicit decisions. A downstream delivery is a fixed, independently readable snapshot. Neither executes a Site Model query or establishes actual compliance.

## 3. Development and product branches

Keep development evidence on `developing-only-jay`. Publish selected application changes to `main`; do not merge this branch wholesale into `main`, because that would also publish the development-only file policy and records. Active workspaces remain local and use validated snapshots for handoff. Environments, credentials and caches are rebuilt or configured locally.
