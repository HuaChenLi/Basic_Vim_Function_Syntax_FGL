"# Basic_Vim_Function_Syntax_FGL" 






cd %HOMEPATH%

So symbolic link works for python
maybe it doesn't work for python 
mklink /H vimfiles\autoload\vim_syntax_in_python.py vimfiles\syntax\vim_syntax_in_python.py

but only a hardlink works for setFunctions.vim
And a hardlink gets destroyed whenever you switch to a different branch
mklink /H vimfiles\autoload\setFunctions.vim vimfiles\syntax\setFunctions.vim

set FGLLDPATH=C:\Users\hua-c\vimfiles\syntax\packages;C:\Users\hua-c\vimfiles\syntax\packages2
