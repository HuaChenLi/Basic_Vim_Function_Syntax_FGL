import os
import unittest

from unittest import TextTestRunner

import lib.tokenize
import findGeneroObject
import lib.libLogging as libLogging

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
UNIT_TEST_DIRECTORY = os.path.join(CURRENT_DIRECTORY, "unitTestFiles")


class TestStringMethods(unittest.TestCase):

    def test_tokenizeString(self):
        inputString = "jk,89"
        outputArray = ["jk", ",", "89"]
        self.assertEqual(lib.tokenize.tokenizeString(inputString), outputArray)

        inputString = "import fgl function"
        outputArray = ["import", "fgl", "function"]
        self.assertEqual(lib.tokenize.tokenizeString(inputString), outputArray)

        inputString = "\"This is a string"
        outputArray = ["\"", "This", "is", "a", "string"]
        self.assertEqual(lib.tokenize.tokenizeString(inputString), outputArray)

        inputString = "-- string yeah comment"
        outputArray = ["--", "string", "yeah", "comment"]
        self.assertEqual(lib.tokenize.tokenizeString(inputString), outputArray)

        inputString = "\\\\\\r whacko escapes \""
        outputArray = ["\\\\\\", "r", "whacko", "escapes", "\""]
        self.assertEqual(lib.tokenize.tokenizeString(inputString), outputArray)


class TestFileSearches(unittest.TestCase):
    PACKAGE_FILE_TEST_DIRECTORY = os.path.join(UNIT_TEST_DIRECTORY, "getPackageFile")
    FIND_FUNCTION_FROM_SPECIFIC_LIBRARY_DIRECTORY = os.path.join(UNIT_TEST_DIRECTORY, "findFunctionFromSpecificLibrary")
    FIND_FUNCTION_FROM_MAKEFILE_DIRECTORY = os.path.join(UNIT_TEST_DIRECTORY, "findFunctionFromMakefile")
    FIND_FUNCTION_AND_METHODS_DIRECTORY = os.path.join(UNIT_TEST_DIRECTORY, "findFunctionAndMethods")

    def test_getPackageFile(self):
        libPath = os.path.join(self.PACKAGE_FILE_TEST_DIRECTORY, "testLib")
        self.assertEqual( str(findGeneroObject.getPackageFile("test2.4gl", [libPath])), str(os.path.join(libPath, "test2.4gl")) )

    def test_findFunctionFromSpecificLibrary(self):
        # find basic function
        libPath = os.path.join(self.FIND_FUNCTION_FROM_SPECIFIC_LIBRARY_DIRECTORY, "testLib")
        self.assertEqual( findGeneroObject.findFunctionFromSpecificLibrary("test3.4gl", [libPath], "test_function"), (str(os.path.join(libPath, "test3.4gl")), 5) )

    def test_findFunctionFromMakefile(self):
        # find basic function
        libPath = os.path.join(self.FIND_FUNCTION_FROM_MAKEFILE_DIRECTORY, "testLib")
        os.environ['FGLLDPATH'] = libPath
        self.assertEqual( findGeneroObject.findFunctionFromMakefile(self.FIND_FUNCTION_FROM_MAKEFILE_DIRECTORY, "test_function400"), (str(os.path.join(libPath, "test4.4gl")), 6) )

    def test_findFunctionAndMethods(self):
        # find basic function
        tokenList = ["import", "fgl", "test5", "\n", "call", "testLib", ".", "test_function100", "("]
        libPath = os.path.join(self.FIND_FUNCTION_AND_METHODS_DIRECTORY, "testLib")
        currentFile = os.path.join(self.FIND_FUNCTION_AND_METHODS_DIRECTORY, "nonExistantFile.4gl")
        libFile = os.path.join(libPath, "test5.4gl")
        self.assertEqual( findGeneroObject.findFunctionAndMethods("test_function100", tokenList, currentFile, [libPath], 2), (libFile, 7))

    def test_findGeneroObject(self):
        pass


def runTests():
    libLogging.LogLevel.logLevel = libLogging.OFF_LEVEL
    return len(unittest.main(__name__, exit=False).result.failures) == 0
    

if __name__ == '__main__':
    unittest.main()