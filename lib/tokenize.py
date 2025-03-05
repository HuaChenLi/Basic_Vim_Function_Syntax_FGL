import re

def tokenizeString(inputString):
    # basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
    # the repeating section contains all the special characters in Genero
    # probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards

    # this regex is a bit more efficient than before, not sure if it can be even more efficient
    tokenBlock = re.findall(r"\w+|!|\"|#|\$|%|&|'|\(|\)|\*|\+|,|--|-|\/|\.|:|;|<|=|>|\?|@|\[|\\+|\]|\^|`|{|\||}|~|\n", inputString)
    return tokenBlock