# Smarter Compliance Workbench

This is the `main` product branch. It contains the application and the permanent PE002 Example. Complete business snapshots and development materials belong to the separate public `developing` branch.

A local, human-led workspace for governing sources and preparing traceable Requirements and check designs. It runs on your own computer and opens in a browser.

Use `main` for shared product installations and updates on Windows and macOS. Jay's `developing` branch also includes development documents and tests. The Windows fixes are part of `main`; a separate operating-system branch is not required.

This directory is the application root. The product checkout contains the four root guides, the two launchers, `deployment.py` and `workbench/`. Development checkouts additionally contain `PROJECT_STATE.md` and `project-support/`; they are not needed to run the product.

## 1. Start here

- [User guide](USER_GUIDE.md): daily review, manual saves, Collaboration and fixed deliveries.
- [Environment guide](ENVIRONMENT.md): first installation, migration, updates and recovery.
- [Agent instructions](AGENTS.md): the single guide for local VS Code Copilot and other coding assistants.
- [Storage and exchange contract](workbench/contracts/storage-and-exchange.md): four databases, version bindings and package format.
- [Review contract](workbench/contracts/review-workflow.md): the existing four-pane workflow and source semantics.

Double-click **Open Workbench (Windows).cmd** on Windows or **Open Workbench (macOS).command** on macOS after setup. Both call `deployment.py`. The [permanent Example](workbench/resources/examples/README.md) includes the full Norwegian law and its saved annotations. Import its seed explicitly on a fresh installation; an ordinary launch or application update never imports it again. Existing installations can import its scoped Collaboration package.

## 2. What is stored where

| Location | Responsibility | Included in application Git updates |
| --- | --- | --- |
| `workbench/frontend/` | Pages, components and bundled browser assets | Yes |
| `workbench/backend/` | Application, System1, System2, System3 and shared code | Yes |
| `workbench/contracts/`, `workbench/config/`, `workbench/deployment/` | Product contracts, sanitized templates and deployment helpers | Yes |
| `workbench/resources/examples/` | Permanent PE002 law, Example-only seed and saved annotation package | Yes |
| `workbench/initial-data/` | Complete dated business snapshots and checksums | Development branch only |
| `workbench/workspace/` | Business databases, originals, exported human history and packages | README only |
| `workbench/runtime/` | Private settings, execution state, recovery backups, diagnostic logs and cache | README only |
| `project-support/`, `workbench/tests/`, `PROJECT_STATE.md` | Development plans, tests and evidence | This development branch only |

System3 uses the Workbench process and has two independently versioned business stores. It is not a separate service. The four panes remain Original document, Extracted content, Requirements, and Interpretation & Check Design.

Collaboration exchanges saved work through a preview and explicit decisions. A downstream delivery is a fixed, independently readable snapshot. Neither executes a Site Model query or establishes actual compliance.

## 3. Development and product branches

Keep full business snapshots and development evidence on `developing`. `main` carries only the product and permanent PE002 Example. Publish selected application changes to `main`; do not merge this branch wholesale into `main`. Both branches and previously published Git history are public. Active workspaces remain local and use validated snapshots for handoff. Environments, credentials and caches are rebuilt or configured locally.
