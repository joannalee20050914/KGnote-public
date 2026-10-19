#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$project_root/scripts/codex_control.py" --repo "$project_root" verify
