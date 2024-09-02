"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"The entire below section is for jumping to variable definition
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GotoDefinition()
    let line = line('.')
    let col = col('.')
    let searchString = '\<\cdefine\>\([\n \t]\+\w\+[\n \t]\+\w\+,\([\n \t]*\)*\)*[\n \t]\+\<' . expand('<cword>') . '\>'
    let returnLine =  SearchNotCommentLineNumber(searchString, line, col, line, col)
    call cursor(returnLine, 1)
endfunction


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" The entire below section is for generating the tags so that you can jump to function definitions (the default is <CTRL>-])
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


" This is the wrapper function of the python script
" This sets the directory to be the same directory, which I think is fine
let s:script_dir = fnamemodify(resolve(expand('<sfile>', ':p')), ':h')
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
function! setFunctions#GenerateTags(filePath)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
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

vim_syntax_in_python.generateTags(vim.eval('fileContent'), vim.eval('a:filePath'))
EOF

endfunction



"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Allows the '.' to be used as a keyword temporarily for searching for 200 milliseconds
function! setFunctions#CWordWithKey(key) abort
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
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
       	execute "set statusline=" . statusMessage

	if IsEndOfFunction(currentLine)
	    let statusMessage = "end of function"
	    let statusMessage = substitute(statusMessage, '\s', '\\ ', 'g')
	    execute "set statusline=" . statusMessage
	endif

	if IsEndOfReport(currentLine)
	    let statusMessage = "end of report"
	    let statusMessage = substitute(statusMessage, '\s', '\\ ', 'g')
	    execute "set statusline=" . statusMessage
	endif

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
    let isComment = v:true
    " still can't quite get the comment in {}

    let hashCommentString = '\#.*\c' . a:comparedString
    let doubleDashString = '\--.*\c' . a:comparedString
    let doubleQuoteString = '\".*\c' . a:comparedString
    let singleQuoteString = "'.*\\c" . a:comparedString
    let backTickQuoteString = '`.*\c' . a:comparedString
    if match(a:currentLine, hashCommentString) < 0 && match(a:currentLine, doubleDashString) < 0 && match(a:currentLine, doubleQuoteString) < 0 && match(a:currentLine, singleQuoteString) < 0 && match(a:currentLine, backTickQuoteString) < 0
        let isComment = v:false
    endif
return isComment
endfunction

function! IsEndOfFunction(statusMessage)
    let isEndOfFunction = v:false
    if match(a:statusMessage, '\c\<END\>\s*\<FUNCTION\>') >= 0
	let isEndOfFunction = v:true
    endif
    return isEndOfFunction
endfunction

function! IsEndOfReport(statusMessage)
    let isEndOfFunction = v:false
    if match(a:statusMessage, '\c\<END\>\s*\<REPORT\>') >= 0
	let isEndOfFunction = v:true
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
