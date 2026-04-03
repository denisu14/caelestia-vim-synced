#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $(basename "$0") [options]"
    echo "Install caelestia-vim-colors (colorscheme sync for Neovim/Vim)"
    echo
    echo "Options passed to caelestia-colorgen.py for initial generation:"
    echo "  -t, --transparent  Transparent editor background"
    echo "  --with-vim         Also generate the Vim colorscheme"
    echo "  --vim-only         Only generate the Vim colorscheme (skip Neovim)"
    echo "  --no-signal        Do not send SIGUSR1 to running Neovim instances"
    echo
    echo "  -h, --help         Show this help message"
    exit 0
}

case "${1:-}" in -h|--help) usage ;; esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
SYSTEMD="$HOME/.config/systemd/user"
NVIM_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
VIM_DIR="$HOME/.vim"
SCHEME="$HOME/.local/state/caelestia/scheme.json"

echo "Installing caelestia-vim-colors"

mkdir -p "$BIN"
install -m755 "$SCRIPT_DIR/caelestia-colorgen.py"   "$BIN/caelestia-colorgen.py"
install -m755 "$SCRIPT_DIR/caelestia-colorwatch.sh"  "$BIN/caelestia-colorwatch.sh"
echo "  scripts -> $BIN"

mkdir -p "$SYSTEMD"
cp "$SCRIPT_DIR/caelestia-colorwatch.service" "$SYSTEMD/"
systemctl --user daemon-reload 2>/dev/null || true
echo "  service -> $SYSTEMD"

# Config snippets
mkdir -p "$NVIM_DIR/lua"
cp "$SCRIPT_DIR/caelestia-sync.lua" "$NVIM_DIR/lua/caelestia-sync.lua"
echo "  neovim config -> $NVIM_DIR/lua/caelestia-sync.lua"

mkdir -p "$VIM_DIR"
cp "$SCRIPT_DIR/caelestia-sync.vim" "$VIM_DIR/caelestia-sync.vim"
echo "  vim config -> $VIM_DIR/caelestia-sync.vim"

# First run
if [[ -f "$SCHEME" ]]; then
    python3 "$BIN/caelestia-colorgen.py" --no-signal "$@" && echo "  initial colorscheme generated"
else
    echo "  scheme.json not found yet - colours will generate on first wallpaper change"
fi

cat << EOF

Done.  Next steps:

  Neovim - add to init.lua:
    require("caelestia-sync")

  Vim (if using --with-vim or --vim-only) - add to .vimrc:
    source ~/.vim/caelestia-sync.vim

  Start the watcher:
    systemctl --user enable --now caelestia-colorwatch.service

  Requires:
    sudo pacman -S inotify-tools
EOF
