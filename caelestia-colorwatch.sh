#!/usr/bin/env bash
# caelestia-colorwatch - Watch scheme.json for changes and regenerate
# Neovim colorschemes.  All arguments are forwarded to caelestia-colorgen.
#
# Requires: inotify-tools   (sudo pacman -S inotify-tools)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GEN="$SCRIPT_DIR/caelestia-colorgen.py"
GEN_ARGS=("$@")

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/caelestia"

if ! command -v inotifywait &>/dev/null; then
    echo "error: inotifywait not found - install inotify-tools" >&2
    exit 1
fi
if [[ ! -f "$GEN" ]]; then
    echo "error: caelestia-colorgen.py not found at $GEN" >&2
    exit 1
fi

mkdir -p "$STATE_DIR"

# Initial generation
[[ -f "$STATE_DIR/scheme.json" ]] && python3 "$GEN" "${GEN_ARGS[@]}" || true

echo "[caelestia-colorwatch] watching $STATE_DIR/scheme.json"

while true; do
    # Watch the directory - editors often write-then-rename.
    inotifywait -q -e close_write,moved_to,create "$STATE_DIR" 2>/dev/null |
    while read -r _ _ filename; do
        [[ "$filename" == "scheme.json" ]] || continue
        sleep 0.1
        python3 "$GEN" "${GEN_ARGS[@]}" || true
    done

    sleep 2
    mkdir -p "$STATE_DIR"
done
