"""Recreate declared component environments; never start services or restore data."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def commands(root, python, windows=False, reviewer=False):
    """Return component-owned setup commands with explicit interpreter paths."""
    interpreter = Path("Scripts/python.exe" if windows else "bin/python")
    components = [] if reviewer else [(root / "system1/Code", "system1")]
    components.append((root / "workbench", "workbench"))
    result = []
    for directory, name in components:
        env_python = directory / ".venv" / interpreter
        result.append((directory, [python, "-m", "venv", str(directory / ".venv"), "--without-pip"]))
        declaration = directory / ("deployment/requirements.lock" if name == "system1" else "pyproject.toml")
        if name == "system1" or windows:
            args = ["uv", "pip", "install", "--python", str(env_python), "-r", str(declaration)]
            if name == "system1":
                args.append("--require-hashes")
            result.append((directory, args))
    result.append((root / "system2", ["uv", "sync", "--locked", "--python", python, "--no-editable"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", action="store_true", help="Set up Workbench and System2 only.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without creating or changing environments.")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Run with Python 3.12 (python3.12 on macOS; py -3.12 on Windows).")
    if not shutil.which("uv"):
        parser.error("uv is required on PATH; see ENVIRONMENT.md.")
    for directory, command in commands(ROOT, sys.executable, os.name == "nt", args.reviewer):
        print(directory.relative_to(ROOT), ":", subprocess.list2cmdline(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=directory, check=True, env={**os.environ,
                "UV_CACHE_DIR": str(directory / ".cache/uv"), "PYTHONUTF8": "1"})
    if not args.dry_run:
        from initialize_local import initialize
        initialize(ROOT)
    print("Environment plan checked." if args.dry_run else "Environments ready. Import saved work separately; no service was started.")


if __name__ == "__main__":
    main()
