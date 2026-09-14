# 1. Windows offline reviewer acceptance

Status: **PENDING_ACTUAL_WINDOWS**. The macOS tests and simulated Windows branches establish implementation checks only. They do not establish an actual Windows installation, Office rendering, browser acceptance or full coordinator portability. Environment ownership and setup instructions remain in the root [ENVIRONMENT.md](../../ENVIRONMENT.md).

## 1.1 Portable local entry

The offline Windows entry is `workbench/deployment/Open Reviewer Workbench.cmd`, which selects reviewer mode and a separate `reviewer-workspace` data directory beside the code. `--root` can select another local reviewer directory. It delegates to `workbench/deployment/Open Workbench.cmd`. It uses Workbench's own `.venv\Scripts\python.exe` and passes command-line arguments through. `Open Workbench.command` retains the macOS default and also accepts arguments. An imported isolated reviewer workspace can be opened with `--reviewer --root "C:\review data\reviewer-workbench"`. The selected root contains data, not copied program code; the launcher uses this installation's source and environment. Reviewer mode must find the imported reviewer descriptor and must not open a normal System1 database.

`workbench/deployment/setup_windows.cmd` creates only the Workbench environment and the locked base System2 environment. It never starts a service, imports business decisions, installs into a global Python environment or installs models. Additional coordinator setup and optional parser profiles retain their separate ownership in ENVIRONMENT.md. Recreate environments on Windows; do not copy macOS `.venv` directories.

## 1.2 Repeatable isolated checks

From the repository root, run `workbench\.venv\Scripts\python.exe workbench\scripts\check_platform.py`. Keep its JSON output with the acceptance record. The driver creates temporary files only and checks separate-process exclusion, lock release, safe process liveness and paths with spaces and non-ASCII characters. A passing result still leaves Office and browser checks below pending.

1. Record Windows version, filesystem, browser, Python version and exact source revision or recovery source hashes. Use a new local directory and engineering-only material packages. Do not use a shared/network folder as a live SQLite workspace.
2. Recreate the declared component environments. Confirm the workbench and System2 interpreters resolve inside their own `.venv\Scripts` directories. Keep System1 data unavailable for the reviewer-mode checks.
3. Import the engineering review package using the documented collaboration flow, then start its reviewer workspace. Open the launcher twice: the same directory must reuse one local service, while another reviewer directory must remain separate. A mode mismatch must be refused.
4. Read the supplied PDF, HTML and Excel originals. Verify scrolling, page/sheet navigation, available text selection/copy, displayed format limitations and a large-file viewport. Compare the engineering Excel original in native Microsoft Excel; record actual screenshots and any font/layout differences.
5. Expand the work area, drag both column separators, exit, reload and verify proportion recovery. Check narrow-window pane navigation and visible save/exit controls. These remain pending actual Windows evidence. Make an engineering-only text correction and save partially complete work. Switch materials, reopen the browser and restart the reviewer service. Verify the saved text, original links and history remain intact, without silently marking content review complete.
6. Exercise duplicate import/export, stale base versions, independent reviewer changes and explicit conflict choices using the collaboration guide. Retain both reviewer returns and the coordinator's histories. Verify an unsaved change blocks unsafe replacement or is recoverable through the intended warning flow.
7. In **My submissions**, select at least two saved results, including a partial result and an assigned inspection when supplied. Export one collection ZIP to a local file and verify its hashes using the receiving installation. Reopen that exact frozen package from submission history. Return it manually to the isolated macOS coordinator; verify import, per-item comparison/adoption and receipt return. A locally created file is not evidence that anything was sent. Transfer only when separately authorized.
8. Stop the reviewer service and rerun the isolated platform smoke check. Record pass/fail per step, error text and retained artifact locations. Do not change this document's status to Windows accepted until those actual checks are recorded.

## 1.3 Implementation boundaries

Workbench and System2 use component-local standard-library helpers: POSIX `flock` and Windows `msvcrt.locking` on byte zero. Workbench Windows process liveness queries `OpenProcess` / `GetExitCodeProcess`, never `os.kill(pid, 0)`. Interpreter selection uses `bin/python` on POSIX and `Scripts/python.exe` on Windows. Windows child service launch uses detached process flags; source paths stay attached to the installed code even when the data root is elsewhere.

The legacy System2 Chrome screenshot route retains POSIX process-group handling and is not part of this offline reviewer acceptance. System1's legacy process-lock fallback still calls `os.kill(pid, 0)` if its required `portalocker` is unavailable; do not use that fallback on Windows. The reviewer route does not invoke System1. These checks do not assert full legacy parser, discovery, scheduling or coordinator Windows compatibility.

## 1.4 This round's local fixture set

The coordinator prepared `project-support/reports/offline-collaboration-20260912/windows-reviewer-code.zip` and `windows-workflow-fixtures.zip`. These retained ZIPs predate the launcher relocation; regenerate the code handoff before a new Windows trial. Keep them separate: the first contains code and setup guidance, the second only isolated TS001 HTML, TS002 Excel and TS003 PDF work plus an Ana Jokic material check. The fixture manifest binds the matching isolated macOS coordinator for returned-package comparison. Do not import these engineering fixtures into normal business data. No Windows result or external transfer has yet been recorded.
