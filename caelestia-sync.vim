" caelestia-sync.vim
" Add to your .vimrc:  source ~/.vim/caelestia-sync.vim
"
" Loads the caelestia colorscheme and reloads it when Vim regains focus
" (after a wallpaper change).

if filereadable(expand('~/.vim/colors/caelestia.vim'))
    colorscheme caelestia
endif

" Reload when Vim regains focus (e.g. after alt-tabbing back from
" a wallpaper change).  This is the best Vim can do without signals.
augroup caelestia_sync
    autocmd!
    autocmd FocusGained * if filereadable(expand('~/.vim/colors/caelestia.vim'))
                       \|     colorscheme caelestia
                       \| endif
augroup END
