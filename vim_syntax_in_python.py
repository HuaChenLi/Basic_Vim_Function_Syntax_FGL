import re
import os
import time
import shutil
from os.path import expanduser
from datetime import datetime

import find
import libLogging
import tokenize
import vimCommands

HOME = expanduser("~")
TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")
LOG_DIRECTORY = os.path.join(TAGS_FILE_DIRECTORY, "fgl_syntax_log")
TAGS_FILE_BASE = os.path.join(HOME, ".temp_tags",".temp_tags")
FGL_DIRECTORY_SUFFIX = ".4gs"
FGL_SUFFIX = ".4gl"
CONSTANTS_SUFFIX = ".cons"

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

def highlightVariables(inputString, currentFile, pid, bufNum):
    vimSyntaxStart = time.time()
    startTime = time.time()
    libLogging.writeSingleLineToLog("=========================================================")
    libLogging.writeSingleLineToLog("vim syntax start for file: " + currentFile)
    libLogging.writeSingleLineToLog("=========================================================")

    if not os.path.exists(TAGS_FILE_DIRECTORY):
        os.makedirs(TAGS_FILE_DIRECTORY)

    currentDirectory = os.path.dirname(currentFile)
    packagePaths = [currentDirectory]
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    tokenList = tokenize.tokenizeString(inputString)

    # This is the part where we want to loop through and find the function definitions in the current file
    librariesList = []

    existingTypes = {}
    isImportingLibrary = False
    isTypeFunction = False
    currentType = ""

    isDefiningVariable = False
    currentVariables = set()

    importFilePath = ""
    concatenatedImportString = ""
    requiredToken = None
    prevPrevToken = ""
    prevTokenNotNewline = ""
    prevToken = ""
    tokenLower = "\n"
    isImportingGlobal = False
    globalFilePath = ""
    lineNumber = 0

    for token in tokenList:
        tokenLower, prevToken = token, tokenLower
        if prevToken == "\n":
            lineNumber += 1

        if isImportingGlobal:
            if (requiredToken == '"' and token != '"') or (requiredToken == "'" and token != "'") or (requiredToken == "`" and token != "`"):
                globalFilePath = globalFilePath + token
            elif (requiredToken == '"' and token == '"') or (requiredToken == "'" and token == "'") or (requiredToken == "`" and token == "`"):
                isImportingGlobal = False

        if token in tokenDictionary and requiredToken is None:
            requiredToken = tokenDictionary.get(token)
        elif requiredToken is not None and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = None
            continue

        tokenLower = tokenLower.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if ((prevTokenNotNewline == "function") or (prevTokenNotNewline == "report")) and not prevPrevToken == "end":
            if token == "(":
                isTypeFunction = True
                continue
            else:
                continue

        if isTypeFunction and not prevTokenNotNewline == "(" and not prevTokenNotNewline == ")" and not token == ")":
            currentType = token
            continue

        if isTypeFunction and prevTokenNotNewline == ")":
            if currentType in existingTypes:
                existingTypes[currentType].append((token,lineNumber))
            isTypeFunction = False
            currentType = ""
            continue

        if prevToken == "fgl" and prevPrevToken == "import":
            importFilePath = token
            concatenatedImportString = token
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "." and token != "\n":
            importFilePath = os.path.join(importFilePath, token)
            concatenatedImportString = concatenatedImportString + "." + token
            continue

        # When it's imported AS something else, we need to create the tags file, but the mapping line is just a bit different
        # The functionName is the AS file, while the file is the path to the file

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
                librariesList.append((importFilePath, token))
            elif token == "\n":
                if prevPrevToken != "as":
                    importFilePath = importFilePath + FGL_SUFFIX
                librariesList.append((importFilePath, concatenatedImportString))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if prevToken == "\n" and tokenLower == "globals":
            isImportingGlobal = True
            continue

        if prevTokenNotNewline == "constant":
            if tokenLower not in GENERO_KEY_WORDS:
                vimCommands.highlightConstant(token)
            continue

        if prevTokenNotNewline == "type":
            if tokenLower not in GENERO_KEY_WORDS:
                vimCommands.highlightConstant(token)
            existingTypes[token] = []
            continue

        if not isDefiningVariable and tokenLower == "define":
            isDefiningVariable = True
            continue

        if isDefiningVariable and (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token != "\n":
            currentVariables.add(token)
            continue

        if isDefiningVariable and not (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token in existingTypes:
            currentVariables = set()

        # this statement is 100% gonna fail with DYNAMIC ARRAY OF RECORD
        if isDefiningVariable and token != "\n" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and prevPrevToken != "define":
            isDefiningVariable = False
            currentVariables = set()

    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("going through current buffer took " + str(lengthTime) + " seconds")

    constantsFile = os.path.join(TAGS_FILE_DIRECTORY, "constants." + pid + "." + bufNum + CONSTANTS_SUFFIX)

    constantsList = []
    startTime = time.time()
    for lib in librariesList:
        importFilePath = lib[0]
        tmpTuple = getPublicVariablesFromLibrary(importFilePath, packagePaths)
        if tmpTuple[2] is not None:
            constantsList.extend(tmpTuple[2])
    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("getting public functions took " + str(lengthTime) + " seconds")

    startTime = time.time()
    tmpTuple = getMakefileFunctions(currentDirectory)
    constantsList.extend(tmpTuple[1])
    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("getting Makefile Functions took " + str(lengthTime) + " seconds")

    writeConstantsFile(constantsList, constantsFile, "a")
    highlightExistingConstants(constantsFile)

    vimSyntaxEnd = time.time()
    vimSyntaxLengthOfTime = vimSyntaxEnd - vimSyntaxStart
    libLogging.writeSingleLineToLog("vim syntax for " + currentFile + " took " + str(vimSyntaxLengthOfTime) + " seconds")

def writeConstantsFile(constantsList, constantsFile, mode):
    file = open(constantsFile, mode)
    file.write("".join(constantsList))
    file.close()

def getPublicVariablesFromLibrary(importFile, packagePaths):
    # I think Genero probably doesn't have overloading, but I think the priority for function scope goes
    # Current File > Imported Library > OBJFILES > CUSTLIBS > LIBFILES
    libLogging.writeSingleLineToLog("getting functions from " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        libLogging.writeSingleLineToLog("couldn't find file " + importFile)
        return [], set(), []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenize.tokenizeString(file.read())
    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    # This is the part where we want to loop through and find the function definitions

    constantsList = []

    requiredToken = None
    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 1

    startTime = time.time()

    for token in tokenList:
        tmpToken, prevToken, prevPrevToken = token, tmpToken, prevToken
        if token == "\n":
            lineNumber += 1

        if token in tokenDictionary and requiredToken is None:
            requiredToken = tokenDictionary.get(token)
        elif requiredToken is not None and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = None
            continue

        prevToken = prevToken.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if ((prevToken == "function") or (prevToken == "report")) and not prevPrevToken == "end" and not prevPrevToken == "private":
            continue

        if prevToken == "constant" and prevPrevToken == "public":
            if token not in GENERO_KEY_WORDS:
                constantsList.append("%s%s" % (token, "\n"))
                vimCommands.highlightConstant(token)

        if prevToken == "type" and prevPrevToken == "public":
            if token not in GENERO_KEY_WORDS:
                constantsList.append("%s%s" % (token, "\n"))                
                vimCommands.highlightConstant(token)

    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return [], set(), constantsList

def findVariableDefinition(varName, buffer, currentFile, currentLineNumber):
    startTime = time.time()
    libLogging.writeSingleLineToLog("=========================================================")
    libLogging.writeSingleLineToLog("looking for variable " + varName)
    libLogging.writeSingleLineToLog("=========================================================")

    tokenList = tokenize.tokenizeString(buffer)

    currentDirectory = os.path.dirname(currentFile)
    packagePaths = [currentDirectory]
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    tmpTuple = find.findFunctionAndMethods(varName, tokenList, currentFile, packagePaths, currentLineNumber)
    packageFile = tmpTuple[0]
    functionLine = tmpTuple[1]

    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("looking for definition took " + str(lengthTime))

    return packageFile, functionLine

def findFunctionWrapper(buffer):
    tokenList = tokenize.tokenizeString(buffer)
    requiredToken = None
    prevToken = ""
    tmpToken = "\n"

    latestFunctionLineNumber = 0
    lineNumber = 1

    for token in tokenList:
        tmpToken, prevToken = token, tmpToken
        if token == "\n":
            lineNumber += 1

        # this section is all about skipping based on strings and comments
        if token in tokenDictionary and requiredToken is None:
            requiredToken = tokenDictionary.get(token)
        elif requiredToken is not None and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = None
            continue

        token = token.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if token == "function" or token == "report":
            latestFunctionLineNumber = lineNumber

    return latestFunctionLineNumber

def getMakefileFunctions(currentDirectory):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return [], []
    file = open(makeFile, "r")
    tokenList = tokenize.tokenizeString(file.read())

    objFileList = []
    custLibFileList = []
    libFileList = []
    globalFileList = []

    importingFileType = ""

    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"

    libFilePath = ""

    packagePaths = []
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    startTime = time.time()
    for token in tokenList:
        if token == "":
            continue

        tmpToken, prevToken, prevPrevToken = token, tmpToken, prevToken
        if token == "=":
            importingFileType = prevToken
            continue

        if importingFileType == "OBJFILES" and token == "o" and prevToken == ".":
            file = prevPrevToken + FGL_SUFFIX
            objFileList.append((file, prevPrevToken))
        elif importingFileType == "CUSTLIBS" and token == "o" and prevToken == ".":
            file = prevPrevToken + FGL_SUFFIX
            custLibFileList.append((file, prevPrevToken))
        elif importingFileType == "LIBFILES":
            if token == "a" and prevToken == ".":
                libFilePath = libFilePath + FGL_DIRECTORY_SUFFIX
                if os.path.isdir(libFilePath):
                    libFileList = [f for f in os.listdir(libFilePath) if os.path.isfile(os.path.join(libFilePath, f))]
                else:
                    libLogging.writeSingleLineToLog("can't find " + libFilePath)
            elif (prevPrevToken == "$" and prevToken == "(") or (prevToken == "$" and token != "("):
                try:
                    # allows the environment variable to be split depending on the os
                    libFilePath = os.environ[token]
                except:
                    # this is in case the environment variable doesn't exist
                    pass
            elif token != "a" and prevToken == "/":
                libFilePath = os.path.join(libFilePath, token)
        elif importingFileType == "GLOBALS" and token == "o" and prevToken == ".":
            file = prevPrevToken + FGL_SUFFIX
            globalFileList.append((file, prevPrevToken))
    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("checking tokens in Makefile took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for obj in objFileList:
        tmpTuple = getPublicVariablesFromLibrary(obj[0], [currentDirectory])
    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("OBJFILES took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for custLib in custLibFileList:
        tmpTuple = getPublicVariablesFromLibrary(custLib[0], packagePaths)
    endTime = time.time()
    libLogging.writeSingleLineToLog("CUSTLIBS took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for libFile in libFileList:
        tmpTuple = getPublicVariablesFromLibrary(libFile, [libFilePath])
    endTime = time.time()
    libLogging.writeSingleLineToLog("LIBFILES took " + str(lengthTime) + " seconds")

    constantsList = []
    startTime = time.time()
    for globalFile in globalFileList:
        tmpTuple = getPublicConstantsFromLibrary(globalFile[0], [currentDirectory])
        constantsList.extend(tmpTuple[1])
    endTime = time.time()
    libLogging.writeSingleLineToLog("GLOBALS took " + str(lengthTime) + " seconds")

    return [], constantsList


def getPublicConstantsFromLibrary(importFile, packagePaths):
    libLogging.writeSingleLineToLog("getting constants from " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        libLogging.writeSingleLineToLog("couldn't find file " + importFile)
        return [], []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenize.tokenizeString(file.read())
    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    constantsList = []

    requiredToken = None
    prevPrevToken = ""
    prevTokenNotNewline = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0

    isDefiningConstant = False

    startTime = time.time()

    for token in tokenList:
        tmpToken, prevToken = token, tmpToken
        if prevToken == "\n":
            lineNumber += 1

        # this section is all about skipping based on strings and comments
        if token in tokenDictionary and requiredToken is None:
            requiredToken = tokenDictionary.get(token)
        elif requiredToken is not None and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = None
            continue

        prevToken = prevToken.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if not isDefiningConstant and prevToken == "constant" and not prevPrevToken == "private":
            isDefiningConstant = True

        if isDefiningConstant and (prevTokenNotNewline == "constant" or prevTokenNotNewline == ",") and token != "\n":
            if token.lower() not in GENERO_KEY_WORDS:
                vimCommands.highlightConstant(token)
                constantsList.append("%s%s" % (token, "\n"))
            continue

        # this statement is 100% gonna fail with DYNAMIC ARRAY OF RECORD
        if isDefiningConstant and token != "\n" and prevToken != "\n" and token != "," and token != "=" and token not in tokenDictionary and prevTokenNotNewline != "," and prevPrevToken != "define":
            isDefiningConstant = False

        if prevToken == "type" and not prevPrevToken == "private":
            if token.lower() not in GENERO_KEY_WORDS:
                vimCommands.highlightConstant(token)
                constantsList.append("%s%s" % (token, "\n"))

    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return [], constantsList

def archiveTempTags(pid):
    archiveDirectory = os.path.join(TAGS_FILE_DIRECTORY, datetime.today().strftime('%Y-%m-%d'))
    if not os.path.isdir(archiveDirectory):
        os.makedirs(archiveDirectory)

    searchString = r"\b" + re.escape(pid) + r"\b"
    allTagFiles = os.listdir(TAGS_FILE_DIRECTORY)
    for f in allTagFiles:
        tagsFile = os.path.join(TAGS_FILE_DIRECTORY, f)
        if os.path.isfile(tagsFile) and re.search(searchString, os.path.join(TAGS_FILE_DIRECTORY, f)):
            shutil.move(tagsFile, archiveDirectory)
            libLogging.writeSingleLineToLog("archived " + tagsFile)

def highlightExistingConstants(constantsFile):
    if os.path.isfile(constantsFile):
        highlightExistingConstants = open(constantsFile, "r").read().split("\n")
        for const in highlightExistingConstants:
            vimCommands.highlightConstant(const)
