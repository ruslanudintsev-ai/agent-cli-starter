#!/usr/bin/env bash
set -euo pipefail

REPO="ruslanudintsev-ai/agent-cli-starter"
REV="main"
DRY_RUN=0
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  case "${ARGS[i]}" in
    --ref)
      if ((i + 1 >= ${#ARGS[@]})); then
        printf '%s\n' 'Error: --ref requires a full commit SHA.' >&2; exit 2
      fi
      REV="${ARGS[i+1]}"
      ((i+=1))
      ;;
    --ref=*) REV="${ARGS[i]#--ref=}" ;;
    --dry-run) DRY_RUN=1 ;;
  esac
done
if [[ "$REV" != "main" && ! "$REV" =~ ^[a-fA-F0-9]{40}$ ]]; then
  printf '%s\n' 'Error: --ref must be main or a full 40-character Git commit SHA.' >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  printf '%s\n' 'Error: curl is required.' >&2; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Error: Python 3.10+ is required.' >&2; exit 1
fi

TEMP_INSTALLER="$(mktemp "${TMPDIR:-/tmp}/agent-cli-installer.XXXXXXXX.py")"
trap 'rm -f "$TEMP_INSTALLER"' EXIT
curl --fail --silent --show-error --location --retry 2 \
  "https://raw.githubusercontent.com/$REPO/$REV/setup_starter_kit.py" --output "$TEMP_INSTALLER"

# --target is placed last so this one-liner always installs in the current directory.
python3 "$TEMP_INSTALLER" "$@" --target "$PWD"
if ((DRY_RUN)); then
  printf 'Dry run completed; no project files changed.\n'
  exit 0
fi

ENTRY=""
if [[ -f manage.py ]] && grep -q '^# AGENT_CLI_STARTER_ENTRYPOINT$' manage.py; then
  ENTRY="manage.py"
elif [[ -f agent_cli.py ]] && grep -q '^# AGENT_CLI_STARTER_ENTRYPOINT$' agent_cli.py; then
  ENTRY="agent_cli.py"
else
  printf '%s\n' 'Error: starter entrypoint could not be located.' >&2; exit 1
fi

python3 "$ENTRY" sys-info --json
printf 'Agent CLI ready: python %s <command> --json\n' "$ENTRY"
