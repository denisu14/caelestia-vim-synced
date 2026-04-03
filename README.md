# caelestia-vim-synced

Dynamic Vim and Neovim colorscheme that syncs with
[Caelestia](https://github.com/caelestia-dots/shell)'s Material 3 palette.

When Caelestia generates a colour scheme from your wallpaper, this tool reads
the palette and writes a native colorscheme file for Vim and Neovim.  Running
Neovim instances hot-reload via `SIGUSR1` - no restart needed.

```
wallpaper change
  -> caelestia CLI writes ~/.local/state/caelestia/scheme.json
    -> inotifywait detects the change
      -> caelestia-colorgen reads the palette
        -> writes ~/.config/nvim/colors/caelestia.lua
          -> SIGUSR1 -> Neovim reloads live
```

## What it covers

Only built-in highlight groups - no third-party plugin dependencies.

- **Editor UI** - Normal, CursorLine, LineNr, Visual, Search, Pmenu, StatusLine,
  TabLine, WinBar, Diff, Spell.
- **Standard syntax** - every `:help group-name` group (Comment, String,
  Function, Keyword, Type, etc.).
- **Diagnostics** - Error / Warn / Info / Hint with undercurl and virtual text.
- **Treesitter** - all `@` capture groups (built-in since Neovim 0.9).
- **LSP semantic tokens** - `@lsp.type.*` groups (built-in since Neovim 0.9).
- **Terminal colours** - `g:terminal_color_0`-`15`.

If you use third-party plugins that define their own highlight groups
(Telescope, nvim-cmp, etc.), you can add overrides in a `ColorScheme` autocmd -
see [Customisation](#customisation) below.

## Requirements

- Python 3
- `inotify-tools` for the watcher (`sudo pacman -S inotify-tools`)
- Neovim >= 0.10 for hot-reload (older Neovim and Vim work, just reload manually)
- An active [Caelestia](https://github.com/caelestia-dots/shell) installation

## Install

```sh
git clone https://github.com/YOUR/caelestia-vim-colors.git
cd caelestia-vim-colors
chmod +x install.sh
./install.sh            # pass --transparent if you want transparent backgrounds
```

The install script copies everything into place.  Then wire up your editor:

**Neovim** - add to `init.lua`:

```lua
require("caelestia-sync")
```

**Vim** - add to `.vimrc`:

```vim
source ~/.vim/caelestia-sync.vim
```

**Start the watcher**

```sh
systemctl --user enable --now caelestia-colorwatch.service
```

Or with Hyprland's `exec-once`:

```
exec-once = ~/.local/bin/caelestia-colorwatch.sh --transparent
```

## Usage

```
caelestia-colorgen.py [OPTIONS]

Options:
  -t, --transparent   Make editor backgrounds transparent
  --with-vim          Also generate the Vim colorscheme
  --vim-only          Only generate the Vim colorscheme (skip Neovim)
  --no-signal         Do not send SIGUSR1 to running Neovim instances
  -h, --help          Show help

caelestia-colorwatch.sh [OPTIONS]

  Watches scheme.json and runs caelestia-colorgen.py on every change.
  All options are forwarded to the generator.
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAELESTIA_SCHEME_PATH` | `~/.local/state/caelestia/scheme.json` | Scheme file to read |
| `CAELESTIA_NVIM_COLORS_DIR` | `~/.config/nvim/colors` | Where to write `caelestia.lua` |
| `CAELESTIA_VIM_COLORS_DIR` | `~/.vim/colors` | Where to write `caelestia.vim` |
| `CAELESTIA_TRANSPARENT` | _(unset)_ | Set to `1` / `true` for transparent mode |

## Colour mapping

| Material 3 role | Editor use |
|-----------------|------------|
| primary | Functions, keywords, UI accents |
| secondary | Types, modules, preprocessor, includes |
| tertiary | Constants, numbers, booleans |
| tertiaryFixedDim | Strings |
| secondaryFixedDim | Macros |
| surface | Editor background |
| onSurface | Default foreground |
| surfaceContainer* | Popups, floats, cursorline |
| error | Errors, exceptions, diagnostics |
| outline | Line numbers, inactive UI |
| outlineVariant | Borders, separators |

## Transparency

Pass `--transparent` (or set `CAELESTIA_TRANSPARENT=1`) to make these groups
use `NONE` backgrounds, letting your terminal's opacity and blur show through:

Normal, SignColumn, FoldColumn, StatusLine, StatusLineNC, TabLineFill,
WinBar, WinBarNC, EndOfBuffer.

Floating windows, popups, and completion menus keep solid backgrounds.

## Customisation

Add overrides in a `ColorScheme` autocmd so they reapply on every reload:

**Neovim** (`init.lua`):

```lua
vim.api.nvim_create_autocmd("ColorScheme", {
    pattern = "caelestia",
    callback = function()
        vim.api.nvim_set_hl(0, "Comment", { fg = "#888888", italic = false })
        -- add any plugin highlight overrides here
    end,
})
```

**Vim** (`.vimrc`):

```vim
augroup caelestia_overrides
    autocmd!
    autocmd ColorScheme caelestia highlight Comment guifg=#888888 gui=NONE
augroup END
```

## Uninstall

```sh
./uninstall.sh
```

Then remove the `require("caelestia-sync")` or `source` line from your config.

## License

GPLv3
