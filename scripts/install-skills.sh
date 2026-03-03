#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Deprecated entrypoint: use scripts/skills.sh directly for all commands." >&2
  echo "Running equivalent install for this repo: add <repo> -s '*' -a codex claude-code -g -y" >&2
  exec "${SCRIPT_DIR}/skills.sh" add "${REPO_ROOT}" -s '*' -a codex claude-code -g -y
fi

echo "Deprecated entrypoint: use scripts/skills.sh directly for all commands." >&2
exec "${SCRIPT_DIR}/skills.sh" "$@"
