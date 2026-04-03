#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    -h|--help)
        echo "Usage: $(basename "$0")"
        echo "Uninstall caelestia-vim-colors (colorscheme sync for Neovim/Vim)"
        exit 0
        ;;
esac

BIN="$HOME/.local/bin"
SYSTEMD="$HOME/.config/systemd/user"
SVC="caelestia-colorwatch.service"

echo "Uninstalling caelestia-vim-colors"

# Stop service
if systemctl --user is-active  --quiet "$SVC" 2>/dev/null; then
    systemctl --user stop    "$SVC"; fi
if systemctl --user is-enabled --quiet "$SVC" 2>/dev/null; then
    systemctl --user disable "$SVC"; fi
rm -f "$SYSTEMD/$SVC"
systemctl --user daemon-reload 2>/dev/null || true
echo "  service removed"

# Scripts
rm -f "$BIN/caelestia-colorgen.py" "$BIN/caelestia-colorwatch.sh"
echo "  scripts removed"

# Generated colorschemes
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/nvim/colors/caelestia.lua"
rm -f "$HOME/.vim/colors/caelestia.vim"
echo "  generated colorschemes removed"

# Config snippets (only if they look like ours)
for f in "${XDG_CONFIG_HOME:-$HOME/.config}/nvim/lua/caelestia-sync.lua" \
         "$HOME/.vim/caelestia-sync.vim"; do
    if [[ -f "$f" ]] && grep -q "caelestia" "$f" 2>/dev/null; then
        rm -f "$f"
        echo "  removed $f"
    fi
done

echo ""
echo "Done.  Remove require(\"caelestia-sync\") / source lines from your config manually."
