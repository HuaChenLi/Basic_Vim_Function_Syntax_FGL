syn match keywordGroup /\c\<ARRAY\>/
syn match keywordGroup /\c\<AS\>/
syn match keywordGroup /\c\<BOOLEAN\>/
syn match keywordGroup /\c\<CALL\>/
syn match keywordGroup /\c\<CONSTANT\>/
syn match keywordGroup /\c\<DEFINE\>/
syn match keywordGroup /\c\<DISPLAY\>/
syn match keywordGroup /\c\<DYNAMIC\>/
syn match keywordGroup /\c\<END\>/
syn match keywordGroup /\c\<FGL\>/
syn match keywordGroup /\c\<FLOAT\>/
syn match keywordGroup /\c\<FOR\>/
syn match keywordGroup /\c\<FUNCTION\>/
syn match keywordGroup /\c\<GLOBALS\>/
syn match keywordGroup /\c\<IMPORT\>/
syn match keywordGroup /\c\<INTEGER\>/
syn match keywordGroup /\c\<LET\>/
syn match keywordGroup /\c\<PRIVATE\>/
syn match keywordGroup /\c\<PUBLIC\>/
syn match keywordGroup /\c\<RECORD\>/
syn match keywordGroup /\c\<REPORT\>/
syn match keywordGroup /\c\<RETURN\>/
syn match keywordGroup /\c\<RETURNS\>/
syn match keywordGroup /\c\<STRING\>/
syn match keywordGroup /\c\<TYPE\>/
syn match keywordGroup /\c\<VAR\>/

hi keywordGroup ctermfg=darkblue
hi variableGroup ctermfg=lightblue
hi functionGroup ctermfg=yellow
hi constantGroup ctermfg=darkyellow
hi stringRegion ctermfg=brown
hi commentRegion ctermfg=darkgreen

syntax region commentRegion start=/#/ end=/\n/
syntax region commentRegion start=/--/ end=/\n/
syntax region commentRegion start=/{/ end=/}/

" the two syntaxes are equivalent in function, I don't know which is better
"syntax region stringRegion start=/"/ skip=/\(\\\)\@<!\(\\\\\)*\\"/ end=/"/
syntax region stringRegion start=/"/ skip=/\\\\\|\\"/ end=/"/
"syntax region stringRegion start=/'/ skip=/\(\\\)\@<!\(\\\\\)*\\'/ end=/'/
syntax region stringRegion start=/'/ skip=/\\\\\|\\'/ end=/'/
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
"call LoadSyntax()

"autocmd TextChanged <buffer> call LoadSyntax()
"autocmd TextChangedI <buffer> call LoadSyntax()
"""""""""""""""""""""""""""""""""""""""

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" In Genero manuals: allows you to press gf to go to the file with the function
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
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

call setFunctions#Setup()

