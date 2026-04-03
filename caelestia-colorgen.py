#!/usr/bin/env python3
"""
caelestia-colorgen - Generate Vim and Neovim colorschemes from Caelestia's
dynamic Material 3 palette.

Reads   ~/.local/state/caelestia/scheme.json
Writes  ~/.config/nvim/colors/caelestia.lua   (Neovim, default)
        ~/.vim/colors/caelestia.vim            (Vim, with --with-vim or --vim-only)

Then sends SIGUSR1 to every running Neovim process so open editors hot-reload.
"""

import argparse
import json
import os
import signal
import sys
from pathlib import Path

# Defaults

SCHEME_PATH = Path(
    os.environ.get(
        "CAELESTIA_SCHEME_PATH",
        os.path.expanduser("~/.local/state/caelestia/scheme.json"),
    )
)

NVIM_COLORS_DIR = Path(
    os.environ.get(
        "CAELESTIA_NVIM_COLORS_DIR",
        os.path.expanduser("~/.config/nvim/colors"),
    )
)

VIM_COLORS_DIR = Path(
    os.environ.get(
        "CAELESTIA_VIM_COLORS_DIR",
        os.path.expanduser("~/.vim/colors"),
    )
)


# Colour helpers

def hex_color(raw: str) -> str:
    """Normalise a colour value to '#rrggbb'."""
    raw = raw.strip().lstrip("#")
    return f"#{raw}"


def blend(a: str, b: str, t: float) -> str:
    """Linearly blend two hex colours.  t=0 = a, t=1 = b."""
    ha, hb = a.lstrip("#"), b.lstrip("#")
    ra, ga, ba_ = int(ha[0:2], 16), int(ha[2:4], 16), int(ha[4:6], 16)
    rb, gb, bb_ = int(hb[0:2], 16), int(hb[2:4], 16), int(hb[4:6], 16)
    r = int(ra + (rb - ra) * t)
    g = int(ga + (gb - ga) * t)
    b_ = int(ba_ + (bb_ - ba_) * t)
    return f"#{r:02x}{g:02x}{b_:02x}"


# Palette extraction

class Palette:
    """Resolve Material 3 colour roles from a Caelestia scheme dict."""

    def __init__(self, scheme: dict):
        self._colours: dict = scheme.get("colours", {})
        self.mode: str = scheme.get("mode", "dark")
        self.name: str = scheme.get("name", "dynamic")
        self.flavour: str = scheme.get("flavour", "")
        self.is_dark: bool = self.mode == "dark"

    def c(self, key: str, fallback: str = "808080") -> str:
        return hex_color(self._colours.get(key, fallback))

    # Key colours

    @property
    def primary(self):            return self.c("primary")
    @property
    def on_primary(self):         return self.c("onPrimary")
    @property
    def primary_container(self):  return self.c("primaryContainer")
    @property
    def on_primary_container(self): return self.c("onPrimaryContainer")

    @property
    def secondary(self):            return self.c("secondary")
    @property
    def on_secondary(self):         return self.c("onSecondary")
    @property
    def secondary_container(self):  return self.c("secondaryContainer")
    @property
    def on_secondary_container(self): return self.c("onSecondaryContainer")

    @property
    def tertiary(self):            return self.c("tertiary")
    @property
    def on_tertiary(self):         return self.c("onTertiary")
    @property
    def tertiary_container(self):  return self.c("tertiaryContainer")
    @property
    def on_tertiary_container(self): return self.c("onTertiaryContainer")

    @property
    def error(self):               return self.c("error")
    @property
    def on_error(self):            return self.c("onError")
    @property
    def error_container(self):     return self.c("errorContainer")
    @property
    def on_error_container(self):  return self.c("onErrorContainer")

    # Surfaces

    @property
    def surface(self):                 return self.c("surface")
    @property
    def on_surface(self):              return self.c("onSurface")
    @property
    def surface_variant(self):         return self.c("surfaceVariant")
    @property
    def on_surface_variant(self):      return self.c("onSurfaceVariant")
    @property
    def surface_container(self):       return self.c("surfaceContainer")
    @property
    def surface_container_high(self):  return self.c("surfaceContainerHigh")
    @property
    def surface_container_highest(self): return self.c("surfaceContainerHighest")
    @property
    def surface_container_low(self):   return self.c("surfaceContainerLow")
    @property
    def surface_container_lowest(self):return self.c("surfaceContainerLowest")

    @property
    def inverse_surface(self):     return self.c("inverseSurface")
    @property
    def inverse_on_surface(self):  return self.c("inverseOnSurface")
    @property
    def inverse_primary(self):     return self.c("inversePrimary")

    # Outlines / misc

    @property
    def outline(self):             return self.c("outline")
    @property
    def outline_variant(self):     return self.c("outlineVariant")
    @property
    def shadow(self):              return self.c("shadow")
    @property
    def scrim(self):               return self.c("scrim")

    # Fixed accent colours (safe for foreground on any surface)

    @property
    def string_fg(self):
        return self.c("tertiaryFixedDim", self._colours.get("tertiary", "ccc992"))

    @property
    def macro_fg(self):
        return self.c("secondaryFixedDim", self._colours.get("secondary", "ccc2dc"))

    # Terminal colours

    def term(self, n: int) -> str:
        return self.c(f"term{n}", "808080")

    # Derived UI colours

    @property
    def visual_bg(self):
        return blend(self.surface_container_high, self.primary, 0.25)

    @property
    def cursorline_bg(self):       return self.surface_container_low

    @property
    def search_bg(self):
        return blend(self.surface, self.primary, 0.35)

    @property
    def diff_add(self):
        return blend(self.surface, self.c("tertiary", "4caf50"), 0.2)

    @property
    def diff_change(self):
        return blend(self.surface, self.c("primary", "2196f3"), 0.2)

    @property
    def diff_delete(self):
        return blend(self.surface, self.c("error", "f44336"), 0.2)

    @property
    def diff_text(self):
        return blend(self.surface, self.c("primary", "2196f3"), 0.35)

    @property
    def diag_warn(self):
        return self.c("tertiary", "fb8c00")

    @property
    def diag_hint(self):           return self.tertiary


# Neovim Lua generator

def generate_lua(p: Palette, transparent: bool) -> str:
    """Return a complete Neovim colorscheme as a Lua string."""

    NONE = "NONE"
    bg_mode = "dark" if p.is_dark else "light"

    # Backgrounds that become NONE in transparent mode
    n_bg    = NONE if transparent else p.surface
    sign_bg = NONE if transparent else p.surface
    fcol_bg = NONE if transparent else p.surface
    tfill   = NONE if transparent else p.surface
    wbar_bg = NONE if transparent else p.surface
    sl_bg   = NONE if transparent else p.surface_container
    slnc_bg = NONE if transparent else p.surface_container_low
    eob_fg  = NONE if transparent else p.surface

    tr_label = "yes" if transparent else "no"

    lines: list[str] = []
    a = lines.append

    a(f'-- Caelestia for Neovim (auto-generated)')
    a(f'-- Scheme: {p.name} | Flavour: {p.flavour} | Mode: {p.mode} | Transparent: {tr_label}')
    a(f'-- https://github.com/caelestia-dots')
    a(f'')
    a(f'vim.opt.termguicolors = true')
    a(f'vim.opt.background = "{bg_mode}"')
    a(f'')
    a(f'vim.cmd("highlight clear")')
    a(f'if vim.fn.exists("syntax_on") then vim.cmd("syntax reset") end')
    a(f'vim.g.colors_name = "caelestia"')
    a(f'')
    a(f'local hi = vim.api.nvim_set_hl')

    def hi(group: str, fg: str | None = None, bg: str | None = None,
           bold: bool = False, italic: bool = False, underline: bool = False,
           undercurl: bool = False, strikethrough: bool = False,
           sp: str | None = None, reverse: bool = False):
        opts: list[str] = []
        if fg:            opts.append(f'fg = "{fg}"')
        if bg:            opts.append(f'bg = "{bg}"')
        if sp:            opts.append(f'sp = "{sp}"')
        if bold:          opts.append("bold = true")
        if italic:        opts.append("italic = true")
        if underline:     opts.append("underline = true")
        if undercurl:     opts.append("undercurl = true")
        if strikethrough: opts.append("strikethrough = true")
        if reverse:       opts.append("reverse = true")
        a(f'hi(0, "{group}", {{ {", ".join(opts)} }})')

    a("")
    a("-- Editor")
    hi("Normal",           fg=p.on_surface,          bg=n_bg)
    hi("NormalFloat",      fg=p.on_surface,          bg=p.surface_container)
    hi("FloatBorder",      fg=p.outline_variant,     bg=p.surface_container)
    hi("FloatTitle",       fg=p.primary,             bg=p.surface_container, bold=True)
    hi("Cursor",           fg=p.surface,             bg=p.on_surface)
    hi("CursorLine",       bg=p.cursorline_bg)
    hi("CursorColumn",     bg=p.cursorline_bg)
    hi("ColorColumn",      bg=p.surface_container_low)
    hi("LineNr",           fg=p.outline)
    hi("CursorLineNr",     fg=p.on_surface, bold=True)
    hi("SignColumn",       fg=p.on_surface_variant,  bg=sign_bg)
    hi("FoldColumn",       fg=p.outline,             bg=fcol_bg)
    hi("Folded",           fg=p.on_surface_variant,  bg=p.surface_container_low)
    hi("VertSplit",        fg=p.outline_variant)
    hi("WinSeparator",     fg=p.outline_variant)

    a("")
    a("-- Selection & Search")
    hi("Visual",           bg=p.visual_bg)
    hi("VisualNOS",        bg=p.visual_bg)
    hi("Search",           fg=p.on_surface, bg=p.search_bg)
    hi("IncSearch",        fg=p.on_primary, bg=p.primary)
    hi("CurSearch",        fg=p.on_primary, bg=p.primary, bold=True)
    hi("Substitute",       fg=p.on_primary, bg=p.primary)

    a("")
    a("-- Popup menu")
    hi("Pmenu",            fg=p.on_surface,            bg=p.surface_container_high)
    hi("PmenuSel",         fg=p.on_primary_container,  bg=p.primary_container)
    hi("PmenuSbar",        bg=p.surface_container)
    hi("PmenuThumb",       bg=p.outline)

    a("")
    a("-- Status / Tab / Winbar")
    hi("StatusLine",       fg=p.on_surface,          bg=sl_bg)
    hi("StatusLineNC",     fg=p.on_surface_variant,  bg=slnc_bg)
    hi("TabLine",          fg=p.on_surface_variant,  bg=p.surface_container)
    hi("TabLineFill",      bg=tfill)
    hi("TabLineSel",       fg=p.on_primary_container, bg=p.primary_container, bold=True)
    hi("WinBar",           fg=p.on_surface,          bg=wbar_bg, bold=True)
    hi("WinBarNC",         fg=p.on_surface_variant,  bg=wbar_bg)

    a("")
    a("-- Messages")
    hi("MsgArea",          fg=p.on_surface)
    hi("ModeMsg",          fg=p.primary, bold=True)
    hi("MoreMsg",          fg=p.primary)
    hi("WarningMsg",       fg=p.error)
    hi("ErrorMsg",         fg=p.on_error, bg=p.error)
    hi("Question",         fg=p.primary)

    a("")
    a("-- Text")
    hi("Title",            fg=p.primary, bold=True)
    hi("Directory",        fg=p.primary)
    hi("MatchParen",       fg=p.primary, bg=p.surface_container_high, bold=True)
    hi("NonText",          fg=p.outline)
    hi("SpecialKey",       fg=p.outline)
    hi("Whitespace",       fg=p.outline_variant)
    hi("EndOfBuffer",      fg=eob_fg)
    hi("Conceal",          fg=p.outline)

    a("")
    a("-- Diff")
    hi("DiffAdd",          bg=p.diff_add)
    hi("DiffChange",       bg=p.diff_change)
    hi("DiffDelete",       bg=p.diff_delete)
    hi("DiffText",         bg=p.diff_text)

    a("")
    a("-- Diagnostics (built-in)")
    hi("DiagnosticError",  fg=p.error)
    hi("DiagnosticWarn",   fg=p.diag_warn)
    hi("DiagnosticInfo",   fg=p.primary)
    hi("DiagnosticHint",   fg=p.diag_hint)
    hi("DiagnosticOk",     fg=p.tertiary)
    hi("DiagnosticUnderlineError", undercurl=True, sp=p.error)
    hi("DiagnosticUnderlineWarn",  undercurl=True, sp=p.diag_warn)
    hi("DiagnosticUnderlineInfo",  undercurl=True, sp=p.primary)
    hi("DiagnosticUnderlineHint",  undercurl=True, sp=p.diag_hint)
    hi("DiagnosticVirtualTextError", fg=p.error,     bg=blend(p.surface, p.error, 0.1))
    hi("DiagnosticVirtualTextWarn",  fg=p.diag_warn, bg=blend(p.surface, p.diag_warn, 0.1))
    hi("DiagnosticVirtualTextInfo",  fg=p.primary,   bg=blend(p.surface, p.primary, 0.1))
    hi("DiagnosticVirtualTextHint",  fg=p.diag_hint, bg=blend(p.surface, p.diag_hint, 0.1))

    a("")
    a("-- Spell")
    hi("SpellBad",         undercurl=True, sp=p.error)
    hi("SpellCap",         undercurl=True, sp=p.diag_warn)
    hi("SpellLocal",       undercurl=True, sp=p.primary)
    hi("SpellRare",        undercurl=True, sp=p.tertiary)

    a("")
    a("-- Standard syntax (`:help group-name`)")
    hi("Comment",          fg=p.on_surface_variant, italic=True)
    hi("Constant",         fg=p.tertiary)
    hi("String",           fg=p.string_fg)
    hi("Character",        fg=p.tertiary)
    hi("Number",           fg=p.tertiary)
    hi("Boolean",          fg=p.tertiary, bold=True)
    hi("Float",            fg=p.tertiary)
    hi("Identifier",       fg=p.on_surface)
    hi("Function",         fg=p.primary)
    hi("Statement",        fg=p.primary)
    hi("Conditional",      fg=p.primary)
    hi("Repeat",           fg=p.primary)
    hi("Label",            fg=p.secondary)
    hi("Operator",         fg=p.on_surface_variant)
    hi("Keyword",          fg=p.primary, italic=True)
    hi("Exception",        fg=p.error)
    hi("PreProc",          fg=p.secondary)
    hi("Include",          fg=p.secondary)
    hi("Define",           fg=p.secondary)
    hi("Macro",            fg=p.macro_fg)
    hi("PreCondit",        fg=p.secondary)
    hi("Type",             fg=p.secondary)
    hi("StorageClass",     fg=p.primary)
    hi("Structure",        fg=p.secondary)
    hi("Typedef",          fg=p.secondary)
    hi("Special",          fg=p.primary)
    hi("SpecialChar",      fg=p.tertiary)
    hi("Tag",              fg=p.primary)
    hi("Delimiter",        fg=p.on_surface_variant)
    hi("SpecialComment",   fg=p.outline, italic=True)
    hi("Debug",            fg=p.error)
    hi("Underlined",       fg=p.primary, underline=True)
    hi("Error",            fg=p.on_error, bg=p.error)
    hi("Todo",             fg=p.on_primary_container, bg=p.primary_container, bold=True)
    hi("Added",            fg=p.tertiary)
    hi("Changed",          fg=p.primary)
    hi("Removed",          fg=p.error)

    a("")
    a("-- Treesitter (built-in, Neovim >= 0.9)")
    hi("@variable",              fg=p.on_surface)
    hi("@variable.builtin",      fg=p.secondary, italic=True)
    hi("@variable.parameter",    fg=p.on_surface_variant)
    hi("@variable.member",       fg=p.on_surface)
    hi("@constant",              fg=p.tertiary)
    hi("@constant.builtin",      fg=p.tertiary, bold=True)
    hi("@module",                fg=p.secondary)
    hi("@string",                fg=p.string_fg)
    hi("@string.escape",         fg=p.tertiary, bold=True)
    hi("@string.regex",          fg=p.tertiary)
    hi("@character",             fg=p.tertiary)
    hi("@number",                fg=p.tertiary)
    hi("@boolean",               fg=p.tertiary, bold=True)
    hi("@float",                 fg=p.tertiary)
    hi("@function",              fg=p.primary)
    hi("@function.builtin",      fg=p.primary, italic=True)
    hi("@function.call",         fg=p.primary)
    hi("@function.method",       fg=p.primary)
    hi("@function.method.call",  fg=p.primary)
    hi("@constructor",           fg=p.secondary)
    hi("@keyword",               fg=p.primary, italic=True)
    hi("@keyword.function",      fg=p.primary, italic=True)
    hi("@keyword.operator",      fg=p.primary)
    hi("@keyword.return",        fg=p.primary, italic=True)
    hi("@keyword.conditional",   fg=p.primary)
    hi("@keyword.repeat",        fg=p.primary)
    hi("@keyword.import",        fg=p.secondary)
    hi("@keyword.exception",     fg=p.error)
    hi("@type",                  fg=p.secondary)
    hi("@type.builtin",          fg=p.secondary, italic=True)
    hi("@type.qualifier",        fg=p.primary, italic=True)
    hi("@attribute",             fg=p.secondary)
    hi("@property",              fg=p.on_surface)
    hi("@operator",              fg=p.on_surface_variant)
    hi("@punctuation",           fg=p.on_surface_variant)
    hi("@punctuation.bracket",   fg=p.on_surface_variant)
    hi("@punctuation.delimiter", fg=p.on_surface_variant)
    hi("@punctuation.special",   fg=p.primary)
    hi("@comment",               fg=p.on_surface_variant, italic=True)
    hi("@tag",                   fg=p.primary)
    hi("@tag.attribute",         fg=p.secondary, italic=True)
    hi("@tag.delimiter",         fg=p.on_surface_variant)
    hi("@markup.heading",        fg=p.primary, bold=True)
    hi("@markup.italic",         italic=True)
    hi("@markup.strong",         bold=True)
    hi("@markup.strikethrough",  strikethrough=True)
    hi("@markup.link",           fg=p.primary, underline=True)
    hi("@markup.link.url",       fg=p.tertiary, underline=True)
    hi("@markup.raw",            fg=p.tertiary)
    hi("@markup.list",           fg=p.primary)

    a("")
    a("-- LSP semantic tokens (built-in, Neovim >= 0.9)")
    hi("@lsp.type.class",          fg=p.secondary)
    hi("@lsp.type.decorator",      fg=p.secondary)
    hi("@lsp.type.enum",           fg=p.secondary)
    hi("@lsp.type.enumMember",     fg=p.tertiary)
    hi("@lsp.type.function",       fg=p.primary)
    hi("@lsp.type.interface",      fg=p.secondary, italic=True)
    hi("@lsp.type.macro",          fg=p.macro_fg)
    hi("@lsp.type.method",         fg=p.primary)
    hi("@lsp.type.namespace",      fg=p.secondary)
    hi("@lsp.type.parameter",      fg=p.on_surface_variant)
    hi("@lsp.type.property",       fg=p.on_surface)
    hi("@lsp.type.struct",         fg=p.secondary)
    hi("@lsp.type.type",           fg=p.secondary)
    hi("@lsp.type.typeParameter",  fg=p.secondary, italic=True)
    hi("@lsp.type.variable",       fg=p.on_surface)

    a("")
    a("-- Terminal colours")
    for i in range(16):
        a(f'vim.g.terminal_color_{i} = "{p.term(i)}"')

    a("")
    return "\n".join(lines) + "\n"


# Vim .vim generator

def generate_vim(p: Palette, transparent: bool) -> str:
    """Return a complete Vim colorscheme as VimScript."""

    bg_mode = "dark" if p.is_dark else "light"
    tr_label = "yes" if transparent else "no"

    NONE = "NONE"
    n_bg    = NONE if transparent else p.surface
    sign_bg = NONE if transparent else p.surface
    fcol_bg = NONE if transparent else p.surface
    tfill   = NONE if transparent else p.surface
    wbar_bg = NONE if transparent else p.surface
    sl_bg   = NONE if transparent else p.surface_container
    slnc_bg = NONE if transparent else p.surface_container_low
    eob_fg  = NONE if transparent else p.surface

    lines: list[str] = []
    a = lines.append

    a(f'" Caelestia for Vim (auto-generated)')
    a(f'" Scheme: {p.name} | Flavour: {p.flavour} | Mode: {p.mode} | Transparent: {tr_label}')
    a(f'" https://github.com/caelestia-dots')
    a(f'')
    a(f'set background={bg_mode}')
    a(f'highlight clear')
    a(f'if exists("syntax_on") | syntax reset | endif')
    a(f'let g:colors_name = "caelestia"')
    a(f'')
    a(f'if has("termguicolors")')
    a(f'  set termguicolors')
    a(f'endif')

    def hi(group: str, fg: str | None = None, bg: str | None = None,
           bold: bool = False, italic: bool = False, underline: bool = False,
           undercurl: bool = False, strikethrough: bool = False,
           sp: str | None = None, reverse: bool = False):
        parts = [f"highlight {group}"]
        parts.append(f" guifg={fg}" if fg else " guifg=NONE")
        parts.append(f" guibg={bg}" if bg else " guibg=NONE")

        attrs = []
        if bold:          attrs.append("bold")
        if italic:        attrs.append("italic")
        if underline:     attrs.append("underline")
        if undercurl:     attrs.append("undercurl")
        if strikethrough: attrs.append("strikethrough")
        if reverse:       attrs.append("reverse")
        parts.append(f" gui={','.join(attrs)}" if attrs else " gui=NONE")

        if sp:
            parts.append(f" guisp={sp}")

        a("".join(parts))

    a("")
    a('" Editor')
    hi("Normal",           fg=p.on_surface,          bg=n_bg)
    hi("NormalFloat",      fg=p.on_surface,          bg=p.surface_container)
    hi("Cursor",           fg=p.surface,             bg=p.on_surface)
    hi("CursorLine",       bg=p.cursorline_bg)
    hi("CursorColumn",     bg=p.cursorline_bg)
    hi("ColorColumn",      bg=p.surface_container_low)
    hi("LineNr",           fg=p.outline)
    hi("CursorLineNr",     fg=p.on_surface, bold=True)
    hi("SignColumn",       fg=p.on_surface_variant,  bg=sign_bg)
    hi("FoldColumn",       fg=p.outline,             bg=fcol_bg)
    hi("Folded",           fg=p.on_surface_variant,  bg=p.surface_container_low)
    hi("VertSplit",        fg=p.outline_variant)

    a("")
    a('" Selection & Search')
    hi("Visual",           bg=p.visual_bg)
    hi("VisualNOS",        bg=p.visual_bg)
    hi("Search",           fg=p.on_surface, bg=p.search_bg)
    hi("IncSearch",        fg=p.on_primary, bg=p.primary)

    a("")
    a('" Popup menu')
    hi("Pmenu",            fg=p.on_surface,            bg=p.surface_container_high)
    hi("PmenuSel",         fg=p.on_primary_container,  bg=p.primary_container)
    hi("PmenuSbar",        bg=p.surface_container)
    hi("PmenuThumb",       bg=p.outline)

    a("")
    a('" Status / Tab')
    hi("StatusLine",       fg=p.on_surface,          bg=sl_bg)
    hi("StatusLineNC",     fg=p.on_surface_variant,  bg=slnc_bg)
    hi("TabLine",          fg=p.on_surface_variant,  bg=p.surface_container)
    hi("TabLineFill",      bg=tfill)
    hi("TabLineSel",       fg=p.on_primary_container, bg=p.primary_container, bold=True)

    a("")
    a('" Messages')
    hi("ModeMsg",          fg=p.primary, bold=True)
    hi("MoreMsg",          fg=p.primary)
    hi("WarningMsg",       fg=p.error)
    hi("ErrorMsg",         fg=p.on_error, bg=p.error)
    hi("Question",         fg=p.primary)

    a("")
    a('" Text')
    hi("Title",            fg=p.primary, bold=True)
    hi("Directory",        fg=p.primary)
    hi("MatchParen",       fg=p.primary, bg=p.surface_container_high, bold=True)
    hi("NonText",          fg=p.outline)
    hi("SpecialKey",       fg=p.outline)
    hi("EndOfBuffer",      fg=eob_fg)
    hi("Conceal",          fg=p.outline)

    a("")
    a('" Diff')
    hi("DiffAdd",          bg=p.diff_add)
    hi("DiffChange",       bg=p.diff_change)
    hi("DiffDelete",       bg=p.diff_delete)
    hi("DiffText",         bg=p.diff_text)

    a("")
    a('" Spell')
    hi("SpellBad",         undercurl=True, sp=p.error)
    hi("SpellCap",         undercurl=True, sp=p.diag_warn)
    hi("SpellLocal",       undercurl=True, sp=p.primary)
    hi("SpellRare",        undercurl=True, sp=p.tertiary)

    a("")
    a('" Standard syntax (`:help group-name`)')
    hi("Comment",          fg=p.on_surface_variant, italic=True)
    hi("Constant",         fg=p.tertiary)
    hi("String",           fg=p.string_fg)
    hi("Character",        fg=p.tertiary)
    hi("Number",           fg=p.tertiary)
    hi("Boolean",          fg=p.tertiary, bold=True)
    hi("Float",            fg=p.tertiary)
    hi("Identifier",       fg=p.on_surface)
    hi("Function",         fg=p.primary)
    hi("Statement",        fg=p.primary)
    hi("Conditional",      fg=p.primary)
    hi("Repeat",           fg=p.primary)
    hi("Label",            fg=p.secondary)
    hi("Operator",         fg=p.on_surface_variant)
    hi("Keyword",          fg=p.primary, italic=True)
    hi("Exception",        fg=p.error)
    hi("PreProc",          fg=p.secondary)
    hi("Include",          fg=p.secondary)
    hi("Define",           fg=p.secondary)
    hi("Macro",            fg=p.macro_fg)
    hi("PreCondit",        fg=p.secondary)
    hi("Type",             fg=p.secondary)
    hi("StorageClass",     fg=p.primary)
    hi("Structure",        fg=p.secondary)
    hi("Typedef",          fg=p.secondary)
    hi("Special",          fg=p.primary)
    hi("SpecialChar",      fg=p.tertiary)
    hi("Tag",              fg=p.primary)
    hi("Delimiter",        fg=p.on_surface_variant)
    hi("SpecialComment",   fg=p.outline, italic=True)
    hi("Debug",            fg=p.error)
    hi("Underlined",       fg=p.primary, underline=True)
    hi("Error",            fg=p.on_error, bg=p.error)
    hi("Todo",             fg=p.on_primary_container, bg=p.primary_container, bold=True)

    a("")
    a('" Terminal colours')
    a("let g:terminal_ansi_colors = [")
    for i in range(16):
        comma = "," if i < 15 else ""
        a(f'      \\ "{p.term(i)}"{comma}')
    a("      \\ ]")

    a("")
    return "\n".join(lines) + "\n"


# Signalling

def signal_neovim():
    """Send SIGUSR1 to every running nvim process."""
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-x", "nvim"], capture_output=True, text=True)
        if result.returncode == 0:
            for pid in result.stdout.strip().splitlines():
                try:
                    os.kill(int(pid), signal.SIGUSR1)
                except (ProcessLookupError, PermissionError):
                    pass
    except FileNotFoundError:
        # pgrep unavailable - try /proc
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                try:
                    if (entry / "comm").read_text().strip() == "nvim":
                        os.kill(int(entry.name), signal.SIGUSR1)
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    pass


# CLI

def main():
    parser = argparse.ArgumentParser(
        prog="caelestia-colorgen",
        description="Generate Vim/Neovim colorschemes from Caelestia's scheme.json.",
    )
    parser.add_argument(
        "-t", "--transparent",
        action="store_true",
        default=os.environ.get("CAELESTIA_TRANSPARENT", "").lower()
            in ("1", "true", "yes"),
        help="Transparent editor background (env: CAELESTIA_TRANSPARENT=1).",
    )
    parser.add_argument(
        "--with-vim", action="store_true",
        help="Also generate the Vim colorscheme (only Neovim by default).",
    )
    parser.add_argument(
        "--vim-only", action="store_true",
        help="Only generate the Vim colorscheme (skip Neovim).",
    )
    parser.add_argument(
        "--no-signal", action="store_true",
        help="Do not send SIGUSR1 to running Neovim instances.",
    )
    args = parser.parse_args()

    if not SCHEME_PATH.exists():
        print(
            f"error: {SCHEME_PATH} not found.\n"
            f"Set a wallpaper first: caelestia wallpaper -f <path>",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        scheme = json.loads(SCHEME_PATH.read_text())
    except (json.JSONDecodeError, IOError) as exc:
        print(f"error: could not read scheme: {exc}", file=sys.stderr)
        sys.exit(1)

    p = Palette(scheme)
    wrote: list[str] = []

    if not args.vim_only:
        NVIM_COLORS_DIR.mkdir(parents=True, exist_ok=True)
        out = NVIM_COLORS_DIR / "caelestia.lua"
        tmp = out.with_suffix(".lua.tmp")
        tmp.write_text(generate_lua(p, args.transparent))
        tmp.rename(out)
        wrote.append(str(out))

    if args.with_vim or args.vim_only:
        VIM_COLORS_DIR.mkdir(parents=True, exist_ok=True)
        out = VIM_COLORS_DIR / "caelestia.vim"
        tmp = out.with_suffix(".vim.tmp")
        tmp.write_text(generate_vim(p, args.transparent))
        tmp.rename(out)
        wrote.append(str(out))

    if not args.no_signal:
        signal_neovim()

    tr = " +transparent" if args.transparent else ""
    print(f"[caelestia-colorgen] {p.name} ({p.mode}{tr}) -> {', '.join(wrote)}")


if __name__ == "__main__":
    main()
