import os
import unittest

from unittest import TextTestRunner

import lib.tokenize
import findGeneroObject

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
UNIT_TEST_DIRECTORY = os.path.join(CURRENT_DIRECTORY, "unitTestFiles")
PACKAGE_FILE_TEST_DIRECTORY = os.path.join(UNIT_TEST_DIRECTORY, "getPackageFile")

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

    def test_getPackageFile(self):
        libPath = os.path.join(PACKAGE_FILE_TEST_DIRECTORY, "testLib")
        self.assertEqual( str(findGeneroObject.getPackageFile("test2.4gl", [libPath])), str(os.path.join(libPath, "test2.4gl")))


def runTests():
    return len(unittest.main(__name__, exit=False).result.failures) == 0
    

if __name__ == '__main__':
    unittest.main()