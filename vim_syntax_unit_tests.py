import unittest
import vim_syntax_in_python



class TestStringMethods(unittest.TestCase):

    def test_tokenizeString(self):
        inputString = "jk,89"
        outputArray = ["jk", ",", "89", ""]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "import fgl function"
        outputArray = ["import", "fgl", "function", ""]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

        inputString = "\"This is a string"
        outputArray = ["\"", "This", "is", "a", "string", ""]
        self.assertEqual(vim_syntax_in_python.tokenizeString(inputString), outputArray)

    def test_tokenizeLinesOfFiles(self):
        inputString = [("import fgl import.basic.functions"), ("import fgl other.functions")]
        outputArray = [("import", 1), ("fgl", 1), ("import", 1), (".", 1), ("basic", 1), (".", 1), ("functions", 1), ("", 1), ("\n", 1), ("import", 2), ("fgl", 2), ("other", 2), (".", 2), ("functions", 2), ("", 2), ("\n", 2)]
        self.assertEqual(vim_syntax_in_python.tokenizeLinesOfFiles(inputString), outputArray)

if __name__ == '__main__':
    unittest.main()

