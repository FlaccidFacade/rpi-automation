#!/usr/bin/env bash
# select-profile.sh - Interactive profile selector.
#
# Prints the selected profile name to stdout on success.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIGS_DIR="$SCRIPT_DIR/configs"

if [ ! -d "$CONFIGS_DIR" ]; then
    echo "Error: configs directory not found: $CONFIGS_DIR" >&2
    exit 1
fi

mapfile -t PROFILES < <(find "$CONFIGS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

if [ "${#PROFILES[@]}" -eq 0 ]; then
    echo "Error: no profiles found in $CONFIGS_DIR" >&2
    exit 1
fi

echo "Available profiles:" >&2
for i in "${!PROFILES[@]}"; do
    echo "  [$i] ${PROFILES[$i]}" >&2
done

while true; do
    read -r -p "Select profile number: " idx
    if [[ "$idx" =~ ^[0-9]+$ ]] && [ "$idx" -ge 0 ] && [ "$idx" -lt "${#PROFILES[@]}" ]; then
        echo "${PROFILES[$idx]}"
        exit 0
    fi
    echo "Invalid selection. Enter a number between 0 and $((${#PROFILES[@]} - 1))." >&2
done