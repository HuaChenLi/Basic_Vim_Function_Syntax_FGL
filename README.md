"# Basic_Vim_Function_Syntax_FGL" 


Run these commands on my Windows Machine

set FGLLDPATH=C:\Users\hua-c\vimfiles\syntax\packages;C:\Users\hua-c\vimfiles\syntax\packages2 & set fg=C:\Users\hua-c\FG

cd %HOMEPATH% & del vimfiles\autoload\vim_syntax_in_python.py & del vimfiles\autoload\setFunctions.vim & del vimfiles\autoload\genero_key_words.txt & del vimfiles\autoload\findGeneroObject.py & mklink /H vimfiles\autoload\vim_syntax_in_python.py vimfiles\syntax\vim_syntax_in_python.py & mklink /H vimfiles\autoload\setFunctions.vim vimfiles\syntax\setFunctions.vim & mklink /H vimfiles\autoload\genero_key_words.txt vimfiles\syntax\genero_key_words.txt & mklink /H vimfiles\autoload\findGeneroObject.py vimfiles\syntax\findGeneroObject.py


Instructions to add to vim
    1. go to .vimrc
    2. add lib folder to .vimrc/syntax
    3. add vim_syntax_in_python.py to .vimrc/syntax
    4. add findGeneroObject.py to .vimrc/syntax
    5. add setFunctions.vim to .vimrc/autoload
    6. update .vimrc/syntax/4gl.vim and add line call setFunctions#Setup()
