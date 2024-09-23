import unittest
import vim_syntax_in_python



class TestStringMethods(unittest.TestCase):

    def test_tokenizeString(self):
        inputString = "jk,89"
        outputArray = ["jk", ",", "89"]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "import fgl function"
        outputArray = ["import", "fgl", "function"]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "\"This is a string"
        outputArray = ["\"", "This", "is", "a", "string"]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "-- string yeah comment"
        outputArray = ["--", "string", "yeah", "comment"]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "\\\\\\r whacko escapes \""
        outputArray = ["\\\\\\", "r", "whacko", "escapes", "\""]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

if __name__ == '__main__':
    unittest.main()

