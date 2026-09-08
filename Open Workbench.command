#!/bin/zsh
set -eu
project_dir="${0:A:h}"
workbench_dir="${project_dir}/workbench"
if [[ ! -x "${workbench_dir}/.venv/bin/python" ]]; then
  echo "The local workbench environment is missing. Follow the setup instructions in README.md."
  read -k 1 "?Press any key to close..."
  exit 2
fi
cd "${workbench_dir}"
export PYTHONPATH="${workbench_dir}/src"
exec "${workbench_dir}/.venv/bin/python" -m local_workbench
