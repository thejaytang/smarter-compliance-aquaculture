#!/bin/zsh
set -eu
script_dir="${0:A:h}"
if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Python 3.12 is required. See ENVIRONMENT.md."
  exit 2
fi
exec python3.12 "$script_dir/rebuild_environments.py" "$@"
