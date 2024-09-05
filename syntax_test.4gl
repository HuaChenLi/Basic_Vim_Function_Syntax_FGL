import fgl libPackage
import fgl otherPackage as libPackage2

import fgl libTest.libFile
IMPORT fgl same_directory
IMPORT fgl libTest.libFile2 as libTestFile2
IMPORT fgl junkFile
import os

	display "this function"
	display `this function`
	display 'this function'

define
 variable string,

	   variable2 STRING,
	   sweet STRING

define variable3 STRING,
	   somethine INTEGER

define v5 integer

define testString = 'something\else'

private function _privFunc()
    # this func starts with _
end function


CONSTANT NEW_CONSTANT = 'something else' #something here
CONSTANT MY_CONSTANT = 'great' -- another type of comment
CONSTANT ANOTHER_CONSTANT = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\'ing'
CONSTANT ANOTHER_CONSTANT_2 = "something"

-- commenting comment
-- function commentFunction()

    { 3rd type of comment
" '
}
define variable4 STRING

display v5

let variable4 = `different string type`

LET variable = "he%5llo"
LET variable2="goodbye"
    FUNCTION madeup4()
	END FUNCTION

PRIVATE function print(text STRING)
	DEFINE temp string
	define  temp2 integer

	DISPLAY text
	display temp
	display temp2
	DISPLAY MY_CONSTANT
end function



PRIVATE function print3(text STRING)
	DEFINE temp string

	DISPLAY text
	display temp2
	DISPLAY MY_CONSTANT

	--FUNCTION madeup2()
	
	--END FUNCTION

	
	#FUNCTION madeUp()
	#	
#{
    #}
	{

	 FUNCTION madeup3()



    }


end function


PRIVATE function print2(text STRING)

end function


DISPLAY "FUNCTION THAT \"I Display"
DISPLAY 'FUNCTION THAT I Display'
DISPLAY `FUNCTION THAT I Display`

        PRIVATE function print3(text STRING)

end  function something()

CALL print()
# yeah this is a comment too


REPORT report1()

    #Report stuff

END REPORT




call libTest.libFile.publicFunction()

CALL libTestFile2.publicFunction2()

CALL libTest.libFile.privateFunction()

CALL publicFunction()
CALL publicFunction2()

CALL libFile.publicFunction()

CALL libFile.publicReport()

CALL same_directory.publicFunction4()

public function publicFunction7()
end function


call testFunction()

call libPackage2.anotherFunction()
