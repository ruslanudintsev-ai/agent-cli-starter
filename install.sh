#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/main"

if ! command -v curl >/dev/null 2>&1; then
  printf '%s\n' 'Error: curl is required.' >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Error: Python 3.10+ is required.' >&2
  exit 1
fi

TEMP_INSTALLER="$(mktemp "${TMPDIR:-/tmp}/agent-cli-installer.XXXXXXXX.py")"
trap 'rm -f "$TEMP_INSTALLER"' EXIT
curl --fail --silent --show-error --location --retry 2 \
  "$REPO_RAW/setup_starter_kit.py" --output "$TEMP_INSTALLER"

python3 "$TEMP_INSTALLER" --target "$PWD" "$@"

ENTRY=""
if [[ -f manage.py ]] && grep -q '^# AGENT_CLI_STARTER_ENTRYPOINT$' manage.py; then
  ENTRY="manage.py"
elif [[ -f agent_cli.py ]] && grep -q '^# AGENT_CLI_STARTER_ENTRYPOINT$' agent_cli.py; then
  ENTRY="agent_cli.py"
else
  printf '%s\n' 'Error: starter entrypoint could not be located.' >&2
  exit 1
fi

python3 "$ENTRY" sys-info --json
printf 'Agent CLI ready: python %s <command> --json\n' "$ENTRY"
