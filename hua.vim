syn match keywordGroup '\c\<BOOLEAN\>'
syn match keywordGroup '\c\<CALL\>'
syn match keywordGroup '\c\<CONSTANT\>'
syn match keywordGroup '\c\<DEFINE\>'
syn match keywordGroup '\c\<DISPLAY\>'
syn match keywordGroup '\c\<END\>'
syn match keywordGroup '\c\<FOR\>'
syn match keywordGroup '\c\<FUNCTION\>'
syn match keywordGroup '\c\<INTEGER\>'
syn match keywordGroup '\c\<LET\>'
syn match keywordGroup '\c\<PRIVATE\>'
syn match keywordGroup '\c\<REPORT\>'
syn match keywordGroup '\c\<STRING\>'
syn match keywordGroup '\c\<VAR\>'

hi keywordGroup ctermfg=darkblue
hi variableGroup ctermfg=lightblue
hi functionGroup ctermfg=yellow
hi constantGroup ctermfg=darkyellow
hi stringRegion ctermfg=brown
hi commentRegion ctermfg=darkgreen


syntax region commentRegion start=/#/ end=/\n/
syntax region commentRegion start=/--/ end=/\n/
syntax region commentRegion start=/{/ end=/}/

syntax region stringRegion start=/\"/ skip=/\\"/ end=/\"/
syntax region stringRegion start=/\'/ skip=/\\'/ end=/\'/
syntax region stringRegion start=/`/ end=/`/


"""""""""""""""""""""""""""""""""""""""
" automatic closing of open syntax
"""""""""""""""""""""""""""""""""""""""
inoremap " ""<left>
inoremap ' ''<left>
inoremap ` ``<left>
inoremap ( ()<left>
inoremap [ []<left>
inoremap { {}<left>

"rather than typing out the whole word, you can change the word to be something different
inoremap FUNCTION FUNCTION<CR>END<SPACE>FUNCTION<UP>
inoremap function function<CR>end<SPACE>function<UP>
inoremap REPORT REPORT<CR>END<SPACE>REPORT<UP>
inoremap report report<CR>end<SPACE>report<UP>
inoremap IF IF<CR>END<SPACE>IF<UP>
inoremap if if<CR>end<SPACE>if<UP>



" interesting, so it feels like this section of the code is somehow run twice
let FUNCTION_REGION_PREFIX = 'functionRegion_'
let FUNCTION_GROUP_PREFIX = 'functionGroup_'
let FILE_START = 'FILE_START'
let VARIABLE_INPUT = 'VARIABLE_INPUT'
let FUNCTION_VARIABLE = 'FUNCTION_VARIABLE'
let DEFINE = 'DEFINE'
let MAIN = 'MAIN'


"""""""""""""""""""""""""""""""""""""""
" removes the .temp_tags file when vim is opened for the tags
call delete('.temp_tags')
"""""""""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""
"call LoadSyntax()

"autocmd TextChanged <buffer> call LoadSyntax()
"autocmd TextChangedI <buffer> call LoadSyntax()
autocmd CursorMoved <buffer> call ShowFuncName(line('.') + 1, col('.'), line('.'), col('.'))
autocmd CursorMovedI <buffer> call ShowFuncName(line('.') + 1, col('.'), line('.'), col('.'))
"""""""""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""
function LoadSyntax()
"""""""""""""""""""""""""""""""""""""""
	" clears the current syntax for this group
	syn clear variableGroup

	"let fileContent = readfile(expand('%:t'))
	let fileContent = getline(1, '$')
	let fileContentList = []
	
	" the issue with split() is that it doesn't count ( and others as token, only white spaces and new lines
	" it has a built in regex, which means that as long as I add all the things, it's ok
	
	for line in fileContent
	
		" the problem of the token being wiped is now solved, but the regex is pretty painful
		" it might be better to split it up, since it would be nearly impossible to actually read it properly
	
		let tempVariable = split(line, SplitRegex())
		for token in split(line, SplitRegex())
			call add(fileContentList, token)
		endfor
	endfor
	
	
	
	" now we want to add modes, is this variable definition mode?
	
	let mode = [g:FILE_START, g:FILE_START]
	let variableList = []
	let functionList = []
	let typeList = []
	let constantList = []

	let functionName = g:MAIN
	let functionNameList = [g:MAIN]
	
	"echo fileContentList
	
	for token in fileContentList
		" the below code helps with debugging a lot
"		echo mode[0] . ' ' . token

		if token == '('
			continue
		endif
	
		if mode[0] == g:VARIABLE_INPUT
			call add(variableList, token)
			call AddFunctionVariable(functionName, token)
			let mode =  SetMode(mode, 'TYPE')
		elseif mode[0] == 'FUNCTION NAME' && mode[1] != 'END'
			let functionName = token
			call add(functionNameList, functionName)
			call CreateFunctionRegion(functionName)
			call HighlightFunction(functionName)
			call CreateFunctionTag(functionName)
			let mode =  SetMode(mode, g:FUNCTION_VARIABLE)
		elseif mode[0] == g:FUNCTION_VARIABLE && mode[1] != 'END'
			call add(functionList, token)
			call HighlightVariable(token, functionName)
			let mode =  SetMode(mode, 'FUNCTION VARIABLE DATATYPE')
		elseif mode[0] == 'CONSTANT'
			call add(constantList, token)
			call HighlightConstant(token)
			let mode = SetMode(mode, 'CONSTANT VARIABLE')
		elseif toupper(token) == g:DEFINE
			" ahhhhhhhhhhhhhhhhhhhhhhh
			" can't use the IsCurrentRegionInFunction(), since that uses the cursor
			" so we're back to the flags until I can think of something else
			if functionName == g:MAIN
				let mode = SetMode(mode, g:VARIABLE_INPUT)
			else
				let mode = SetMode(mode, g:FUNCTION_VARIABLE)
			endif
			continue
		elseif toupper(token) == 'FUNCTION'
			let mode = SetMode(mode, 'FUNCTION NAME')
			continue
		elseif toupper(token) == 'END'
			let mode = SetMode(mode, 'END')
			continue
		elseif toupper(token) == 'CONSTANT'
			let mode = SetMode(mode, 'CONSTANT')
			continue
		endif
	
		" commas are funny, because you would need to keep track of what was there 2 modes ago
		if token == ','
			"echo mode[1]
			let mode = SetMode(mode, mode[1])
			continue
		endif
	endfor

	call HighlightFunctionVariables(functionNameList)
endfunction

function SplitRegex()
    let specialCharacterList = ['\.', ',', '\(',  '\)', '\[', '\]', '{', '}', '#', '\$', "'", '"', '`', '\\', '\+', '\-', '=', '\*', '&', '!', '\|', ';', '<', '>', '@']
    " dunno why this can't be v:null
    let specialCharacterString = ''

    for specialCharacter in specialCharacterList
    	let specialCharacterString = specialCharacterString . specialCharacter
    endfor

    let regexString = '\s\|\v(([' . specialCharacterString . '])@<=|([' . specialCharacterString . '])@=)'

    return regexString
endfunction

function AddFunctionVariable(functionName, inputString)
	if a:functionName == g:MAIN
		execute 'syn keyword ' . g:FUNCTION_GROUP_PREFIX . a:functionName . ' ' . a:inputString
	else
		execute 'syn keyword ' . g:FUNCTION_GROUP_PREFIX . a:functionName . ' ' . a:inputString . ' contained containedin=' . g:FUNCTION_REGION_PREFIX .  a:functionName
	endif
endfunction

function HighlightVariable(variable, functionName)
	if a:functionName == g:MAIN
		execute 'syn keyword variableGroup ' . a:variable
	else
		let functionRegion = g:FUNCTION_REGION_PREFIX . a:functionName
		let command = 'syntax keyword '. g:FUNCTION_GROUP_PREFIX . a:functionName . ' ' . a:variable . ' contained containedin=' . functionRegion
		"echo command
		execute command


		syntax region myRegion start="thina" end='thinb' contains=myMatch,keywordGroup,constantGroup keepend
	syntax match myMatch 'temp2' contained containedin=myRegion
"	hi myMatch ctermfg=red
	endif
endfunction

function HighlightFunction(inputString)
    execute 'syn keyword functionGroup ' . a:inputString
endfunction

function HighlightConstant(inputString)
    execute 'syn keyword constantGroup ' . a:inputString
endfunction

function HighlightFunctionVariables(functionNameList)
    for name in a:functionNameList
    	execute 'hi '. g:FUNCTION_GROUP_PREFIX . name . ' ctermfg=lightblue'
    endfor
endfunction

function CreateFunctionRegion(functionName)
	" feels a big flimsy having the functionGroup_ as well as the keywordGroup within the text.
	" I suppose it's fine, but it feels like it could be a little bit more backwards compatible
	"echo 'syntax region ' . g:FUNCTION_REGION_PREFIX . a:functionName . ' start="\cFUNCTION ' . a:functionName . '" end="\cEND FUNCTION" contains=functionGroup_' . a:functionName . ' keepend'

	" this thing does so much, including folding
	execute 'syntax region ' . g:FUNCTION_REGION_PREFIX . a:functionName . ' start="\cFUNCTION ' . a:functionName . '" end="\cEND FUNCTION" contains=keywordGroup,functionGroup,constantGroup,' . g:FUNCTION_GROUP_PREFIX . a:functionName . ' keepend extend fold'
	execute 'hi ' . g:FUNCTION_GROUP_PREFIX . a:functionName . ' ctermfg=red'
endfunction

function SetMode(inputList, inputMode)
    let a:inputList[1] = a:inputList[0]
    let a:inputList[0] = a:inputMode
    return a:inputList
endfunction

"""""""""""""""""""""""""""""""""""""""
" In Genero manuals
"""""""""""""""""""""""""""""""""""""""
set suffixesadd=.4gl

function! LoadModule(fname)
    let x = stridx(a:fname,'.')
    if x > 1
        let fn = a:fname[0:x-1]
    else
        let fn = a:fname
    endif
    let fn = fn . ".4gl"
    if filereadable(fn)
        return fn
    else
        return a:fname
    endif
endfunction

set includeexpr=LoadModule(v:fname)



"""""""""""""""""""""""""""""""""""""""
" tags playground, trying to jump to function definition
"""""""""""""""""""""""""""""""""""""""
set tags=.temp_tags
setlocal iskeyword+=\. "allows '.' to be considered part of a word

function CreateFunctionTag(functionName)
	let fileName = expand('%:t')
	call writefile([a:functionName . "\t" . fileName . "\t/\\cFUNCTION " . a:functionName . '/;" c'] , '.temp_tags', 'a')
endfunction





"""""""""""""""""""""""""""""""""""""""
" trying to set the statusline
"""""""""""""""""""""""""""""""""""""""
set laststatus=2

function! ShowFuncName(newLine, newColumn, originalLine, originalColumn)
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
	    call ShowFuncName(tempLineOpenCurlyNumber - 1, a:newColumn, a:originalLine, a:originalColumn)
	endif

    else
	let newLineNumber = SearchNotCommentLineNumber('{', tempLineCloseCurlyNumber, a:newColumn, a:originalLine, a:originalColumn)
	call ShowFuncName(newLineNumber - 1, a:newColumn, a:originalLine, a:originalColumn)
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

"""""""""""""""""""""""""""""""""""""""
function! GetCurrentRegion()
"""""""""""""""""""""""""""""""""""""""
    let region = v:null
    for id in synstack(line("."), col("."))
	let region = synIDattr(id, "name")
    endfor
    return region
endfunction




"""""""""""""""""""""""""""""""""""""""
function! IsCurrentRegionInFunction()
"""""""""""""""""""""""""""""""""""""""
	let region = GetCurrentRegion()
	if stridx(region, g:FUNCTION_REGION_PREFIX) >=0
		return 1
	endif
	return 0
endfunction


" This is the wrapper function of the python script
" This sets the directory to be the same directory, which I think is fine

let s:script_dir = fnamemodify(resolve(expand('<sfile>', ':p')), ':h')
"""""""""""""""""""""""""""""""""""""""
function! DoSomething()
"""""""""""""""""""""""""""""""""""""""


let fileContent = getline(1, '$')
let fileName = expand('%:t')

" python for 2, python3 for 3

python3 << EOF
import sys
import vim

script_dir = vim.eval('s:script_dir')
sys.path.insert(0, script_dir)

import vim_syntax_in_python

vim_syntax_in_python.printTokens(vim.eval('fileContent'), vim.eval('fileName'))
EOF

endfunction

call DoSomething()
