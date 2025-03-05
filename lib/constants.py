import os
from os.path import expanduser

HOME = expanduser("~")

TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")

CONSTANTS_SUFFIX = ".cons"

FGL_DIRECTORY_SUFFIX = ".4gs"

FGL_SUFFIX = ".4gl"

GENERO_KEY_WORDS = set()

KEYWORDS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "genero_key_words.txt")

if os.path.isfile(KEYWORDS_FILE):
    GENERO_KEY_WORDS.update(open(KEYWORDS_FILE, "r").read().lower().split("\n"))

tokenDictionary = {
    "'" : "'",
    '"' : '"',
    "`" : "`",
    "#" : "\n",
    "--" : "\n",
    "{" : "}"
}