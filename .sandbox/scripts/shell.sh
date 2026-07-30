#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=_lib.sh
source scripts/_lib.sh

WORKDIR=""
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --workdir)
            WORKDIR="$2"
            shift 2
            ;;
        --workdir=*)
            WORKDIR="${1#*=}"
            shift
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

WORKDIR_ARGS=()
if [[ -n "$WORKDIR" ]]; then
    WORKDIR_ARGS=(--workdir "$WORKDIR")
fi

exec docker compose exec "${WORKDIR_ARGS[@]}" claude-code zsh "${ARGS[@]}"
