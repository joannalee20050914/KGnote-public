#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_python="${KGNOTE_TEST_PYTHON:-$project_root/.venv/bin/python}"

if [ ! -x "$test_python" ]; then
  echo "Missing test Python: $test_python" >&2
  echo "Run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt" >&2
  exit 2
fi

cd "$project_root"
"$test_python" docs/requirements/requirements_guard.py check --repo "$project_root"
PYTHONPATH="$project_root/docs/requirements${PYTHONPATH:+:$PYTHONPATH}" \
  "$test_python" -m unittest discover -s docs/requirements -p 'test_requirements_guard.py' -v
PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$test_python" -m unittest discover -s tests -p 'test_*.py' -v
