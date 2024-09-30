let TRUE = 1
let FALSE = 0


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This sets the directory to be the same directory, which I think is fine
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
let s:script_dir = fnamemodify(resolve(expand('<sfile>', ':p')), ':h')

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"The entire below section is for jumping to variable definition
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GotoDefinition(filePath)
    let lineNumber = line('.')
    let fileContent = join(getline(1, '$'), "\n")
    let varName = setFunctions#CWordWithKey()

python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

tmpTuple = vim_syntax_in_python.findVariableDefinition(vim.eval('varName'), vim.eval('fileContent'), vim.eval('g:filePath'), vim.eval('lineNumber'))

execCommand = "let packageFile = escape('" + str(tmpTuple[0]) + "', '\\')"
vim.command(execCommand)
print(execCommand)

execCommand = "let functionLine = escape('" + str(tmpTuple[1]) + "', '\\')"
vim.command(execCommand)
EOF
    echo packageFile
    execute 'e +' . functionLine . ' ' . packageFile
endfunction


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This is the wrapper function of the python script
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GenerateTags(filePath, pid, bufNum)
    let fileContent = join(getline(1,'$'), "\n")

    " python for 2, python3 for 3
python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.generateTags(vim.eval('fileContent'), vim.eval('a:filePath'), vim.eval('a:pid'), vim.eval('a:bufNum'))
EOF

endfunction

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GenerateTagsForCurrentBuffer(filePath, pid, bufNum)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    let fileContent = join(getline(1,'$'), "\n")

    " python for 2, python3 for 3
python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.generateTagsForCurrentBuffer(vim.eval('fileContent'), vim.eval('a:filePath'), vim.eval('a:pid'), vim.eval('a:bufNum'))
EOF

endfunction

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#CWordWithKey() abort
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    " Allows the '.' to be used as a keyword temporarily
    execute 'set iskeyword+=46'
    let selectedWord = expand('<cword>')
    execute 'set iskeyword-=46'

    return selectedWord
endfunction


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! ShowFunctionName()
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    let fileContent = join(getline(1, line('.')),"\n")

python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

lineNumber = vim_syntax_in_python.findFunctionWrapper(vim.eval('fileContent'))

vim.command("let line=" + str(lineNumber))
EOF

    let statusMessage = getline(line)
    let statusMessage = substitute("line " . line . ": " . statusMessage, '\s', '\\ ', 'g')
    execute "set statusline=" . statusMessage . "%=%p%%"

endfunction


function! setFunctions#DeleteTempTags(pid, bufNum)

python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.removeTempTags(vim.eval('a:pid'), vim.eval('a:bufNum'))
EOF

endfunction

function! setFunctions#ArchiveTempTags(pid)

python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.archiveTempTags(vim.eval('a:pid'))
EOF

endfunction

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#Setup()
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    " The below section sets the Status Line to show the current function
    set laststatus=2

    " You can change the colour of the Status Line
    hi StatusLine ctermfg=black ctermbg=yellow

    nnoremap <F11> : call ShowFunctionName()<CR>

    " Grabs the filepath of the buffer
    let g:filePath = expand('%:p')

    " This runs the GenerateTags() whenever a buffer is switched to
    " This could potentially get pretty heavy depending on the number of files there are
    autocmd! BufEnter <buffer> call setFunctions#GenerateTags(g:filePath, getpid(), bufnr('%'))
    autocmd! VimLeave <buffer> call setFunctions#ArchiveTempTags(getpid())
    autocmd! InsertLeave <buffer> call setFunctions#GenerateTagsForCurrentBuffer(g:filePath, getpid(), bufnr('%'))
    autocmd! BufWritePost <buffer> call setFunctions#GenerateTags(g:filePath, getpid(), bufnr('%'))

    " The below section remaps CTRL-] so that the behaviour of the word is only changed when jumping to tag
    nnoremap <buffer> <silent> <C-]> : execute 'tag '.setFunctions#CWordWithKey()<CR>

    " The below section allows the user to jump to the definition of a variable (still in progress)
    nnoremap <F12> : call setFunctions#GotoDefinition(g:filePath)<CR>

endfunction

