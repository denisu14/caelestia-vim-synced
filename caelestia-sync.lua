-- caelestia-sync.lua
-- Add to your Neovim config:  require("caelestia-sync")
--
-- Loads the caelestia colorscheme and hot-reloads it when
-- caelestia-colorwatch sends SIGUSR1 after a wallpaper change.
-- Requires Neovim >= 0.10 for the Signal autocmd.

local function load()
    local path = vim.fn.stdpath("config") .. "/colors/caelestia.lua"
    if vim.fn.filereadable(path) == 1 then
        vim.cmd.colorscheme("caelestia")
        return true
    end
    return false
end

if not load() then
    vim.notify(
        "caelestia colorscheme not found - run caelestia-colorgen.py",
        vim.log.levels.WARN
    )
end

if vim.fn.has("nvim-0.10") == 1 then
    vim.api.nvim_create_autocmd("Signal", {
        pattern  = "SIGUSR1",
        -- Wrap load() so its return value doesn't propagate;
        -- returning true from an autocmd callback deletes the autocmd.
        callback = function() load() end,
        desc     = "Hot-reload caelestia colours",
    })
end
