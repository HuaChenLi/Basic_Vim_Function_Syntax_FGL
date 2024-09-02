""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"The entire below section is for jumping to variable definition
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GotoDefinition()
    let line = line('.')
    let col = col('.')
    let searchString = '\<\cdefine\>\([\n \t]\+\w\+[\n \t]\+\w\+,\([\n \t]*\)*\)*[\n \t]\+\<' . expand('<cword>') . '\>'
    let returnLine =  SearchNotCommentLineNumber(searchString, line, col, line, col)
    call cursor(returnLine, 1)
endfunction


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" The entire below section is for generating the tags so that you can jump to function definitions (the default is <CTRL>-])
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


" This is the wrapper function of the python script
" This sets the directory to be the same directory, which I think is fine
let s:script_dir = fnamemodify(resolve(expand('<sfile>', ':p')), ':h')
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GenerateTags(filePath)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    set tags=.temp_tags
    let fileContent = getline(1, '$')

    " removes the .temp_tags file when vim is opened for the tags
    " could change in the future where it doesn't need to delete the .temp_tags
    call delete('.temp_tags')

    " python for 2, python3 for 3
python3 << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.generateTags(vim.eval('fileContent'), vim.eval('filePath'))
EOF

endfunction



" Allows the '.' to be used as a keyword temporarily for searching for 200 milliseconds
function! setFunctions#CWordWithKey(key) abort
    let s:saved_iskeyword = &iskeyword
    let s:saved_updatetime = &updatetime
    if &updatetime > 200 | let &updatetime = 200 | endif
    augroup CWordWithKeyAuGroup
        autocmd CursorHold,CursorHoldI <buffer>
                    \ let &updatetime = s:saved_updatetime |
                    \ let &iskeyword = s:saved_iskeyword |
                    \ autocmd! CWordWithKeyAuGroup
    augroup END
    execute 'set iskeyword+='.a:key
    return expand('<cword>')
endfunction
