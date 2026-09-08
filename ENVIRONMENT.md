# Runtime Environment

This is the shared environment guide for the Requirement Workstream. Paths and commands below start from the directory containing this file unless a different working directory is stated. This is the GitHub repository root; in the original authoring workspace it is named `05_Working area of requirements side/`. Use [README.md](README.md) for the project entry and [PROJECT_STATE.md](PROJECT_STATE.md) for dated verification results.

## Environment ownership

Keep one isolated environment per executable component. The workbench calls System1 through its own interpreter; System2 does the same for governed source intake. There is no shared root `.venv`.

| Component | Environment | Python requirement | Dependency source of truth |
| --- | --- | --- | --- |
| System1 | `system1/Code/.venv/` | 3.11+ | [Pinned requirements](system1/Code/deployment/requirements.txt) and [setup script](system1/Code/deployment/setup_macos.command) |
| System2 | `system2/.venv/` | >=3.11,<3.14 | [pyproject.toml](system2/pyproject.toml) declares dependencies/extras; [uv.lock](system2/uv.lock) locks their resolution |
| Workbench | `workbench/.venv/` | 3.11+ | [pyproject.toml](workbench/pyproject.toml); standard-library runtime, no third-party runtime packages |
| System3 | None yet | Not selected | [Design-only state](system3/PROJECT_STATE.md); create an independent environment when implementation begins |

Python 3.12 is the common setup target. Use the explicit component interpreter rather than an ambient `python` or another activated environment. Dependency declarations remain in their owning components; this guide does not replace them. System1 pins its direct dependencies but does not currently provide a complete transitive lockfile. Workbench source execution does not require a package build or a separate dependency lockfile.

## New-machine setup

The commands in this section create or synchronize environments and may download dependencies. They are setup actions, not daily launch steps. On a new computer, recreate environments instead of copying `.venv` directories. Retain the component directories, configuration, source data and persistent runtime records together.

### System1 and the workbench on macOS

Prerequisite: a working Python 3.12 installation available as `python3` on `PATH`. A browser is required for daily operation. Microsoft Excel is used for workbook inspection and native acceptance, not as the daily review interface.

```sh
python3 --version
mkdir -p system1/Code/runtime/backups system1/Code/runtime/logs
./system1/Code/deployment/setup_macos.command
python3 -m venv workbench/.venv --without-pip
```

The empty runtime directories support a fresh clone's write-location checks; live runtime records are not committed. The System1 setup script creates its environment, installs its pinned requirements and creates missing local configuration from examples. It leaves existing configuration in place and does not register a schedule. Read its Doctor result and rerun the check below if any issue is reported. The script waits for a keypress before closing.

After setup, the normal daily entry is:

```sh
./Open\ Workbench.command
```

The launcher starts the local workbench and may process already-submitted requests and due weekly QA while it runs. It is not an environment-only diagnostic. Close Excel before applying workbook changes through the workbench.

System1 also provides [Windows setup](system1/Code/deployment/setup_windows.cmd). This does not establish Windows support for the complete workbench: the current launcher and adapters use macOS/POSIX paths, including `.venv/bin/python`. Validate and adapt those entries before deploying the whole workspace on Windows.

### System2 development and local parsing

Prerequisites: `uv` and Python 3.12. Run this block from the workstream root; the subshell keeps the surrounding working directory unchanged:

```sh
(
  cd system2
  UV_CACHE_DIR="$PWD/.cache/uv" uv sync --locked --python 3.12 \
    --no-editable --extra dev --extra docling --extra table-fallbacks
)
```

`--locked` refuses a dependency change that requires updating `uv.lock`. `--no-editable` installs an ordinary package rather than relying on an editable-install `.pth` file. Continue using `PYTHONPATH=src` when running source code so a stale installed wheel cannot override current files.

This profile includes test tools, positioned native extraction and table fallbacks. HTML/XLSX use the base dependencies. The separate `paddle` extra enables additional OCR/layout/model integrations; it is not required for the current HTML/XLSX workflow or included in the profile above. If a task explicitly needs it, add `--extra paddle` to the same synchronization command, retaining the other extras. Python packages and cached model files are separate requirements; a cache directory alone does not prove a backend can run. Do not change parser profiles as a substitute for accuracy validation.

For the current explicit local PDF route, inspect [pdf-intake-positioned.yaml](system2/config/pdf-intake-positioned.yaml). Parser commands and bounded sample selection belong to the [System2 guide](system2/USER_GUIDE.md); full PDF runs are not setup checks.

## Tools outside the Python environments

| Tool | Used for | Requirement |
| --- | --- | --- |
| `uv` | System2 locked dependency setup | Needed when rebuilding/synchronizing System2; not required to double-click an already-installed workbench |
| Node.js | Workbench frontend state tests | Development only; not required by the workbench Python service |
| Poppler `pdftotext` | Independent native PDF text evidence | Must be on the parsing process's `PATH` when that evidence path is required |
| Tesseract | Local OCR for the selected PDF route | Requires the executable and language data matching the run configuration |

Executable checks:

```sh
uv --version
node --version
pdftotext -v
tesseract --version
tesseract --list-langs
```

An installed Python OCR wrapper does not install the Tesseract executable or prove that Norwegian language data is available. Missing secondary evidence must remain visible in verification results. Native-tool and model requirements depend on the selected parser configuration; environment readiness is separate from source-fidelity acceptance.

## Configuration, environment variables and persistent data

| Setting or location | Purpose |
| --- | --- |
| `PYTHONPATH=src` | Select current source code when running from the owning component's code directory |
| `UV_CACHE_DIR="$PWD/.cache/uv"` from `system2/` | Keep System2 package downloads in its local cache |
| `system1/Code/config/config.json` | Relative workbook/Data/runtime paths and operational settings |
| `system1/Code/config/schedule.json` | Schedule intent; setup does not enable or register an operating-system schedule |
| `system2/config/*.yaml` | Parser, routing, verification and external-model settings selected per run |
| `system2/.cache/` | Rebuildable package/model caches; first use of a missing model may need a download |
| `workbench/runtime/` | Persistent operators, drafts, requests, receipts and staged uploads, plus local service metadata |

System2's [model-runtime setup](system2/src/pdf_extraction/ocr.py) supplies project-local defaults for `PADDLE_PDX_CACHE_HOME`, `XDG_CACHE_HOME`, `MPLCONFIGDIR` and `HF_HOME`. Run from `system2/` so these defaults remain inside the component. Existing process environment overrides take precedence.

`ENVIRONMENT.md` is documentation. A `.env` file is a different mechanism for process configuration or secrets; the current launch/setup paths do not require a shared root `.env`. Do not put real credentials into this guide or version control. Keep `.venv`, rebuildable caches and local runtime files out of commits; preserve persistent business and review data during environment repair. Workbench SQLite and System1 history are not disposable environment caches.

The workbench listens on `127.0.0.1` and manages its local port through runtime metadata. Do not hard-code a machine-specific address into shared configuration. See the [workbench guide](workbench/USER_GUIDE.md) for service behavior.

## Verify an existing installation

These checks inspect the environment and imports without starting the review service or parsing source files:

```sh
(
  cd system1/Code
  PYTHONPATH=src .venv/bin/python -m system1 doctor
)
(
  cd system2
  PYTHONPATH=src .venv/bin/python -c \
    'import sys, pdf_extraction; print(sys.version); print(pdf_extraction.__file__)'
  UV_CACHE_DIR="$PWD/.cache/uv" uv sync --locked --dry-run --offline \
    --no-python-downloads --no-editable --extra dev --extra docling --extra table-fallbacks
)
(
  cd workbench
  PYTHONPATH=src .venv/bin/python -c \
    'import sys, sqlite3, local_workbench; print(sys.version); print(local_workbench.__file__)'
)
```

The import paths should point into the intended component's `src/`. The dry run previews synchronization without installing or removing packages or rewriting the lockfile; it is not a fresh-machine installation test. If an offline check cannot resolve cached information, report that limitation instead of removing `--locked` or silently changing dependencies.

After environment or code changes, use the component's existing checks: [System1 tests](system1/Code/ENGINEERING.md#testing), [System2 tests](system2/USER_GUIDE.md#tests) and [workbench checks](workbench/USER_GUIDE.md#file-ownership). Documentation changes require link/path/command checks, not a full parser run. Update this guide when setup procedures or environment ownership change, update the owning dependency declaration/lockfile for dependency changes, and record verified state in the appropriate `PROJECT_STATE.md`.
