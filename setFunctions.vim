let TRUE = 1
let FALSE = 0


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This sets the directory to be the same directory, which I think is fine
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
let s:script_dir = fnamemodify(resolve(expand('<sfile>', ':p')), ':h')

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"The entire below section is for jumping to variable definition
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GotoDefinition()
    let line = line('.')
    let col = col('.')
    let fileContent = getline(1, line)
    " I'd rather pass everything into a python script and find the define that way

python << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

lineNumber = vim_syntax_in_python.findVariableDefinition(vim.eval('fileContent'))
vim.command("let lineNumber = '%s'"% lineNumber)
EOF
    echo lineNumber
   " let searchString = '\<\cdefine\>\([\n \t]\+\w\+[\n \t]\+\w\+,\([\n \t]*\)*\)*[\n \t]\+\<' . expand('<cword>') . '\>'
   " let returnLine =  SearchNotCommentLineNumber(searchString, line, col, line, col)
    call cursor(lineNumber, 1)
endfunction


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This is the wrapper function of the python script
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GenerateTags(filePath, pid, bufNum)
    execute 'set tags=~/.temp_tags/.temp_tags.' . a:pid . '.' . a:bufNum
    let fileContent = getline(1, '$')

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
" Allows the '.' to be used as a keyword temporarily for searching for 200 milliseconds
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#CWordWithKey(key, filePath, pid, bufNum) abort
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
    call setFunctions#GenerateTags(a:filePath, a:pid, a:bufNum)
    return expand('<cword>')
endfunction


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#ShowFuncName(newLine, newColumn, originalLine, originalColumn)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    call cursor(a:newLine, a:newColumn)

    let tempFunctionLineNumber = SearchNotCommentLineNumber('\c\<FUNCTION\>', a:newLine, a:newColumn, a:originalLine, a:originalColumn)

    let tempReportLineNumber = SearchNotCommentLineNumber('\c\<REPORT\>', a:newLine, a:newColumn, a:originalLine, a:originalColumn)

    if tempFunctionLineNumber < tempReportLineNumber
	let tempFunctionLineNumber = tempReportLineNumber
    endif

    let tempLineCloseCurlyNumber = SearchNotCommentLineNumber('}', a:newLine, a:newColumn, a:originalLine, a:originalColumn)


    if tempFunctionLineNumber >= tempLineCloseCurlyNumber
	" check that there is a closed curly bracket before the Function anywhere or there is no open curly brack before the Function
	let tempLineOpenCurlyNumber = 0
	if tempFunctionLineNumber != 0
	    let tempLineOpenCurlyNumber = SearchNotCommentLineNumber('{', a:newLine - 1, a:newColumn, a:originalLine, a:originalColumn)
	endif

	let currentLine = getline(tempFunctionLineNumber)

       	call cursor(a:originalLine, a:originalColumn)

       	let statusMessage = substitute(currentLine, '\s', '\\ ', 'g')

	if IsEndOfFunction(currentLine)
	    let statusMessage = "end of function"
	    let statusMessage = substitute(statusMessage, '\s', '\\ ', 'g')
	endif

	if IsEndOfReport(currentLine)
	    let statusMessage = "end of report"
	    let statusMessage = substitute(statusMessage, '\s', '\\ ', 'g')
	endif

	execute "set statusline=" . statusMessage . "%=%p%%"

	if tempLineOpenCurlyNumber > tempLineCloseCurlyNumber
	    call setFunctions#ShowFuncName(tempLineOpenCurlyNumber - 1, a:newColumn, a:originalLine, a:originalColumn)
	endif

    else
	let newLineNumber = SearchNotCommentLineNumber('{', tempLineCloseCurlyNumber, a:newColumn, a:originalLine, a:originalColumn)
	call setFunctions#ShowFuncName(newLineNumber - 1, a:newColumn, a:originalLine, a:originalColumn)
    endif
endfunction

function! IsComment(currentLine, comparedString)
    " will need to update so that it doesn't need a comparedString and can just recognise if the position is a comment
    let isComment = g:TRUE
    " still can't quite get the comment in {}

    let hashCommentString = '\#.*\c' . a:comparedString
    let doubleDashString = '\--.*\c' . a:comparedString
    let doubleQuoteString = '\".*\c' . a:comparedString
    let singleQuoteString = "'.*\\c" . a:comparedString
    let backTickQuoteString = '`.*\c' . a:comparedString
    if match(a:currentLine, hashCommentString) < 0 && match(a:currentLine, doubleDashString) < 0 && match(a:currentLine, doubleQuoteString) < 0 && match(a:currentLine, singleQuoteString) < 0 && match(a:currentLine, backTickQuoteString) < 0
        let isComment = g:FALSE
    endif
return isComment
endfunction

function! IsEndOfFunction(statusMessage)
    let isEndOfFunction = g:FALSE
    if match(a:statusMessage, '\c\<END\>\s*\<FUNCTION\>') >= 0
	let isEndOfFunction = g:TRUE
    endif
    return isEndOfFunction
endfunction

function! IsEndOfReport(statusMessage)
    let isEndOfFunction = g:FALSE
    if match(a:statusMessage, '\c\<END\>\s*\<REPORT\>') >= 0
	let isEndOfFunction = g:TRUE
    endif
    return isEndOfFunction
endfunction

function! SearchNotCommentLineNumber(searchString, currentLineNumber, currentColumnNumber, originalLine, originalColumn)
    call cursor(a:currentLineNumber, a:currentColumnNumber)
    let returnLine = search(a:searchString, 'bnW', 'g')
    let currentLine = getline(returnLine)
    if IsComment(currentLine, a:searchString)
	call cursor(a:currentLineNumber, a:currentColumnNumber)
	let returnLine = SearchNotCommentLineNumber(a:searchString, returnLine - 1, a:currentColumnNumber, a:originalLine, a:originalColumn)
    else
	call cursor(a:originalLine, a:originalColumn)
    endif
    return returnLine
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

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#Setup()
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    " The below section sets the Status Line to show the current function
    set laststatus=2

    " You can change the colour of the Status Line
    hi StatusLine ctermfg=black ctermbg=yellow

    nnoremap <F10> : call setFunctions#ShowFuncName(line('.') + 1, col('.'), line('.'), col('.'))

    " Grabs the filepath of the buffer
    let g:filePath = expand('%:p')

    " This runs the GenerateTags() whenever a buffer is switched to
    " This could potentially get pretty heavy depending on the number of files there are
    autocmd! BufEnter <buffer> silent! call setFunctions#GenerateTags(g:filePath, getpid(), bufnr('%'))

    " The below section remaps CTRL-] so that the behaviour of the word is only changed when jumping to tag
    nnoremap <buffer> <silent> <C-]> :execute 'tag '.setFunctions#CWordWithKey(46, g:filePath, getpid(), bufnr('%'))<CR>

    " The below section allows the user to jump to the definition of a variable (still in progress)
    nnoremap <F12> : call setFunctions#GotoDefinition()<CR>

endfunction

