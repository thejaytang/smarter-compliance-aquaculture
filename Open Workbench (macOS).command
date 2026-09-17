#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x ./workbench/.venv/bin/python ]; then
    exec ./workbench/.venv/bin/python ./deployment.py "$@"
fi
exec python3 ./deployment.py "$@"
