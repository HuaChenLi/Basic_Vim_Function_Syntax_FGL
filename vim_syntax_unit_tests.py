import unittest

import lib.tokenize



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
        # importFile = 
        self.assertTrue(1==1)


if __name__ == '__main__':
    unittest.main()

