#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CLI_VERSION="${SKILLS_CLI_VERSION:-latest}"

usage() {
  cat <<USAGE
Wrapper for \'npx skills\' with preflight checks and better error hints.

Usage:
  scripts/skills.sh <same arguments as npx skills>

Examples:
  scripts/skills.sh --help
  scripts/skills.sh list -g
  scripts/skills.sh check
  scripts/skills.sh add "${REPO_ROOT}" -s '*' -a codex claude-code -g -y
  scripts/skills.sh add "${REPO_ROOT}" --list

Notes:
  - This wrapper forwards all args directly to: npx --yes skills@${CLI_VERSION}
  - Set SKILLS_CLI_VERSION to pin a version, e.g. SKILLS_CLI_VERSION=0.5.1
USAGE
}

err() {
  echo "ERROR: $*" >&2
  exit 1
}

expand_home_path() {
  local p="$1"
  if [[ "$p" == "~" ]]; then
    echo "$HOME"
  elif [[ "$p" == ~/* ]]; then
    echo "$HOME/${p#~/}"
  else
    echo "$p"
  fi
}

is_local_source_hint() {
  local src="$1"
  [[ "$src" == "." || "$src" == ".." || "$src" == /* || "$src" == ./* || "$src" == ../* || "$src" == ~* || -e "$src" ]]
}

print_node_install_help() {
  local os
  os="$(uname -s)"
  echo "npx was not found. Node.js is required to run 'npx skills'." >&2

  if [[ "$os" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      echo "Install with Homebrew: brew install node" >&2
    else
      echo "Install Node LTS from https://nodejs.org/ or via nvm/fnm." >&2
    fi
  elif [[ "$os" == "Linux" ]]; then
    echo "Install Node LTS via your package manager or nvm/fnm." >&2
  else
    echo "Install Node LTS from https://nodejs.org/." >&2
  fi
}

maybe_prompt_install_node_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    return 1
  fi
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  if [[ ! -t 0 || ! -t 1 ]]; then
    return 1
  fi

  echo "npx not found." >&2
  read -r -p "Install Node via Homebrew now? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES)
      brew install node
      ;;
    *)
      return 1
      ;;
  esac

  command -v npx >/dev/null 2>&1
}

ensure_npx() {
  if command -v npx >/dev/null 2>&1; then
    return
  fi

  if maybe_prompt_install_node_macos; then
    return
  fi

  print_node_install_help
  exit 127
}

diagnose_failure() {
  local output="$1"

  if [[ "$output" == *"EAI_AGAIN"* || "$output" == *"ENOTFOUND"* || "$output" == *"ECONNRESET"* || "$output" == *"ETIMEDOUT"* ]]; then
    echo "Hint: network/DNS issue while fetching npm packages or remote sources." >&2
    echo "- Check internet/proxy settings and retry." >&2
    return
  fi

  if [[ "$output" == *"EACCES"* || "$output" == *"permission denied"* || "$output" == *"Permission denied"* ]]; then
    echo "Hint: permission issue detected." >&2
    echo "- Retry with project scope where supported by the command." >&2
    echo "- Or fix Node/npm directory permissions." >&2
    return
  fi

  if [[ "$output" == *"401"* || "$output" == *"403"* || "$output" == *"Unauthorized"* || "$output" == *"authentication"* ]]; then
    echo "Hint: authentication/authorization issue for source or package registry." >&2
    return
  fi

  if [[ "$output" == *"Missing required argument: source"* ]]; then
    echo "Hint: use 'add <source>' or 'add <source> --list'." >&2
    echo "Example: scripts/skills.sh add '${REPO_ROOT}' -s '*' -a codex claude-code -g -y" >&2
    return
  fi

  if [[ "$output" == *"Found 0 skill"* || "$output" == *"No skills found"* ]]; then
    echo "Hint: source was reachable but no SKILL.md matched filters." >&2
    echo "- Validate source path and --skill filters." >&2
    return
  fi

  if [[ "$output" == *"Unknown command"* || "$output" == *"Unknown option"* ]]; then
    echo "Hint: run scripts/skills.sh --help to see supported CLI options." >&2
    return
  fi

  echo "Hint: rerun with a simpler command first (e.g. scripts/skills.sh list) to isolate the issue." >&2
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  echo
  if command -v npx >/dev/null 2>&1; then
    set +e
    npx --yes "skills@${CLI_VERSION}" --help
    exit_code=$?
    set -e
    exit $exit_code
  fi
  echo "npx is not installed, so upstream help is unavailable." >&2
  print_node_install_help
  exit 0
fi

ensure_npx

ARGS=("$@")

# Lightweight preflight for `add <source>` only.
if [[ "${ARGS[0]}" == "add" || "${ARGS[0]}" == "a" ]]; then
  if [[ ${#ARGS[@]} -lt 2 || "${ARGS[1]}" == -* ]]; then
    err "Missing source for 'add'. Example: scripts/skills.sh add '${REPO_ROOT}' -s '*' -a codex claude-code -g -y"
  fi

  src="$(expand_home_path "${ARGS[1]}")"
  ARGS[1]="$src"

  if is_local_source_hint "$src"; then
    [[ -e "$src" ]] || err "Local source path not found: $src"

    # Warn early if no skill files exist under local source.
    skill_count="$(find "$src" -type f -name SKILL.md 2>/dev/null | wc -l | tr -d '[:space:]')"
    if [[ "$skill_count" == "0" ]]; then
      echo "WARN: no SKILL.md found under local source: $src" >&2
    fi
  fi
fi

CMD=(npx --yes "skills@${CLI_VERSION}" "${ARGS[@]}")

run_output=""
run_status=0
interactive_mode="false"

if [[ -t 0 && -t 1 && -t 2 && "${SKILLS_CAPTURE_OUTPUT:-0}" != "1" ]]; then
  interactive_mode="true"
fi

if [[ "$interactive_mode" == "true" ]]; then
  set +e
  "${CMD[@]}"
  run_status=$?
  set -e
else
  set +e
  run_output="$("${CMD[@]}" 2>&1)"
  run_status=$?
  set -e
  echo "$run_output"
fi

if [[ $run_status -ne 0 ]]; then
  echo >&2
  echo "Command failed (exit=$run_status)." >&2
  if [[ "$interactive_mode" == "true" ]]; then
    echo "Hint: rerun with SKILLS_CAPTURE_OUTPUT=1 to enable diagnostic parsing." >&2
  else
    diagnose_failure "$run_output"
  fi
  exit $run_status
fi
