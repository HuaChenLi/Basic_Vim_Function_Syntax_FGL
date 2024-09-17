import re
import os
import time
from os.path import expanduser
from datetime import datetime

HOME = expanduser("~")
TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")
TAGS_FILE_BASE = os.path.join(HOME, ".temp_tags",".temp_tags")
FGL_SUFFIX = ".4gl"
LOG_DIRECTORY = os.path.join(HOME, "fgl_syntax_log")

def generateTags(inputString, currentFile, pid, bufNum):
    start = time.time()
    writeSingleLineToLog("vim syntax start")

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

    tokenList = tokenizeLinesOfFiles(inputString)

    # This is the part where we want to loop through and find the function definitions in the current file

    tagsLinesList = []
    librariesList = []

    isImportingLibrary = False

    importFilePath = ""
    fileAlias = ""
    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    token = "\n"

    for index, tokenBlock in enumerate(tokenList):
        # I don't get why it doesn't duplicate by putting it in the for loop instead of outside the for loop :(
        if index == 0:
            tagsLinesList.extend(getMakefileFunctions(currentDirectory))

        prevPrevToken = prevToken
        prevToken = token
        token = tokenBlock[0]
        lineNumber = tokenBlock[1]

        # occasionally there are blank tokens
        if token == "":
            continue

        # this section is all about skipping based on strings and comments
        if token == "-" and prevToken == "-":
            token = "--"
            continue

        if requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and prevToken == "\\":
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        isPrevPrevTokenEnd = prevPrevToken.lower() == "end"
        isPreviousTokenFunctionOrReport = (prevToken.lower() == "function") or (prevToken.lower() == "report")

        if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd:
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=currentFile, fileAlias=currentFile, currentDirectory=currentDirectory))

        if token.lower() == "import" and prevToken == "\n":
            # we need to check that Import is at the start of the line
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken.lower() == "import" and token.lower() == "fgl":
            continue
        elif isImportingLibrary and prevToken.lower() == "import" and not token.lower() == "fgl":
            # for when importing not an FGL library
            isImportingLibrary = False
            continue

        isPreviousTokenAs = prevToken.lower() == "as"

        if isImportingLibrary and token != "." and token != "\n" and not token == "as" and not isPreviousTokenAs:
            importFilePath = os.path.join(importFilePath, token)
            if fileAlias == "":
                fileAlias = token
            else:
                fileAlias = fileAlias + "." + token
            continue

        # When it's imported AS something else, we need to create the tags file, but the mapping line is just a bit different
        # The functionName is the AS file, while the file is the path to the file

        if isImportingLibrary and token == "\n" and not isPreviousTokenAs:
            isImportingLibrary = False
            importFilePath = importFilePath + FGL_SUFFIX
            librariesList.append((importFilePath, fileAlias))
            importFilePath = ""
            fileAlias = ""
            continue
        elif isImportingLibrary and isPreviousTokenAs:
            isImportingLibrary = False
            librariesList.append((importFilePath, token))
            importFilePath = ""
            fileAlias = ""
            continue


        if isImportingLibrary and token.lower() == "as":
            importFilePath = importFilePath + FGL_SUFFIX
            continue

    startTime = time.time()

    for lib in librariesList:
        importFilePath = lib[0]
        fileAlias = lib[1]
        tagsLinesList.extend(getPublicFunctionsFromLibrary(importFilePath, fileAlias, currentDirectory, packagePaths))

    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting public functions took " + str(lengthTime) + " seconds")

    writeTagsFile(tagsLinesList, pid, bufNum)

    end = time.time()
    length = end - start
    writeSingleLineToLog("vim syntax took " + str(length) + " seconds")

def createListOfTags(functionName, lineNumber, currentFile, fileAlias, currentDirectory):
    # this is interesting, I would need to, for each separation, create a tagLine
    tagsLinesList = []
    functionCallRoot = currentFile.replace(currentDirectory + os.sep, "")
    functionCallRoot = functionCallRoot.replace(FGL_SUFFIX, "")
    functionTokens = functionCallRoot.split(os.sep)

    tagLine = "{0}\t{1}\t{2}\n".format(functionName, currentFile, lineNumber)
    tagsLinesList.append(tagLine)

    functionNameString = functionName
    for token in reversed(functionTokens):
        functionNameString = token + "." + functionNameString
        tagLine = "{0}\t{1}\t{2}\n".format(functionNameString, currentFile, lineNumber)
        tagsLinesList.append(tagLine)

    # check if the Alias is already in the file path (this means we didn't actually alias)
    isAliasInFilePath = re.search(fileAlias, currentFile.replace(os.sep, "."), flags=re.IGNORECASE)

    if fileAlias != currentFile and isAliasInFilePath is None:
        aliasFunctionName = fileAlias + "." + functionName
        tagLine = "{0}\t{1}\t{2}\n".format(aliasFunctionName, currentFile, lineNumber)
        tagsLinesList.append(tagLine)

    return tagsLinesList


def writeTagsFile(tagsLinesList, pid, bufNum):
    # The tags file needs to be sorted alphabetically (by ASCII code) in order to work
    tagsLinesList.sort()
    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum
    file = open(tagsFile, "a")
    for line in tagsLinesList:
        file.write(line)
    file.close()


def getPublicFunctionsFromLibrary(importFilePath, fileAlias, workingDirectory, packagePaths):
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFilePath)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        return []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenizeLinesOfFiles(file)
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFilePath + " took " + str(length) + " seconds")

    # This is the part where we want to loop through and find the function definitions

    tagsLinesList = []

    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    token = "\n"

    writeSingleLineToLog("the number of tokens is " + str(len(tokenList)))

    startTime = time.time()

    for tokenBlock in tokenList:
        # occasionally there are blank tokens
        if tokenBlock[0] == "":
            continue

        prevPrevToken = prevToken
        prevToken = token
        token = tokenBlock[0]
        lineNumber = tokenBlock[1]

        # this section is all about skipping based on strings and comments
        if token == "-" and prevToken == "-":
            token = "--"

        if requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and prevToken == "\\":
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        isPrevPrevTokenEnd = prevPrevToken.lower() == "end"
        isPrevPrevTokenPrivate = prevPrevToken.lower() == "end"
        isPreviousTokenFunctionOrReport = (prevToken.lower() == "function") or (prevToken.lower() == "report")

        if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd and not isPrevPrevTokenPrivate:
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=packageFile, fileAlias=fileAlias, currentDirectory=workingDirectory))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("If statements took " + str(length) + " seconds")

    return tagsLinesList


def tokenizeString(inputString):
    # basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
    # the repeating section contains all the special characters in Genero
    # probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards
    tokenBlock = re.findall(r"(?:(?!\.|,|'|`|\"|\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|=)[!-~])+|\.|,|'|`|\"|\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|=", inputString)
    return tokenBlock


def findVariableDefinition(buffer):
    tokenList = tokenizeLinesOfFiles(buffer)

    # This is copy and pasted from function printTokens() but with a few changes

    # This is the part where we want to loop through and find the function definitions
    # We need to first set a couple of flags when we're ignoring sections

    isNewLineNeeded = False
    isClosedCurlyBracketNeeded = False

    isSingleQuoteNeeded = False
    isDoubleQuotesNeeded = False
    isBackQuoteNeeded = False # back tick / backtick

    previousToken = ""
    token = ""
    for tokenBlock in tokenList:
        # occasionally there are blank tokens
        if tokenBlock[0] == "":
            continue

        previousToken = token
        token = tokenBlock[0]
        lineNumber = tokenBlock[1]

        # Skip booleans
        if isNewLineNeeded and token != "\n":
            continue
        elif isNewLineNeeded and token == "\n":
            isNewLineNeeded = False
            continue

        # with the quotes, need to also account for escape character "\"
        if isSingleQuoteNeeded and (token != "'" or previousToken == "\\"):
            continue
        elif isSingleQuoteNeeded and token == "'":
            isSingleQuoteNeeded = False
            continue

        if isDoubleQuotesNeeded and (token != '"' or previousToken == "\\"):
            continue
        elif isDoubleQuotesNeeded and token == '"':
            isDoubleQuotesNeeded = False
            continue

        if isBackQuoteNeeded and token != "`":
            continue
        elif isBackQuoteNeeded and token == "`":             # I believe the back quote can't be escaped in Genero
            isBackQuoteNeeded = False
            continue

        # Comments
        if token == "#" or token == "--":
            isNewLineNeeded = True
            continue

        if isClosedCurlyBracketNeeded and token != "}":
            continue
        elif isClosedCurlyBracketNeeded and token == "}":
            isClosedCurlyBracketNeeded = False
            continue

        if token == "{":
            isClosedCurlyBracketNeeded = True
            continue

        # Strings
        if token == '"':
            isDoubleQuotesNeeded = True
            continue

        if token == "'":
            isSingleQuoteNeeded = True
            continue

        if token == "`":
            isBackQuoteNeeded = True
            continue




def tokenizeLinesOfFiles(file):
    tokenList = []
    for lineNumber, line in enumerate(file, start=1):
        tokenBlock = tokenizeString(line)
        tokenBlock.append("\n")
        tokenList.extend([(token,lineNumber) for token in tokenBlock])
    return tokenList


def getRequiredToken(inputToken):
    tokenDictionary = {
        "'" : "'",
        '"' : '"',
        "`" : "`",
        "#" : "\n",
        "--" : "\n",
        "{" : "}"
    }
    return tokenDictionary.get(inputToken, "")

def removeTempTags(pid, bufNum):
    try:
        tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum
        os.remove(tagsFile)
    except OSError:
        pass

def getMakefileFunctions(currentDirectory):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return []
    file = open(makeFile, "r")
    tokenList = tokenizeLinesOfFiles(file)

    tagsList = []

    isImportingObjectFiles = False
    prevToken = ""
    token = "\n"

    for tokenBlock in tokenList:
        if tokenBlock[0] == "":
            continue

        prevToken = token
        token = tokenBlock[0]
        lineNumber = tokenBlock[1]

        packagePaths = [currentDirectory]

        if token == "OBJFILES":
            isImportingObjectFiles = True

        # This feels like the weakest syntax check
        if isImportingObjectFiles and token == ".":
            continue
        elif isImportingObjectFiles and prevToken == "=":
            file = token + FGL_SUFFIX
            tagsList.extend(getPublicFunctionsFromLibrary(file, token, currentDirectory, packagePaths))
            continue
        elif isImportingObjectFiles and token == "\n" and prevToken != "\\":
            isImportingObjectFiles = False

    return tagsList

def writeSingleLineToLog(inputString):
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    fileToday = datetime.today().strftime('%Y-%m-%d')
    logFile = os.path.join(LOG_DIRECTORY, fileToday + ".log")

    file = open(logFile, "a")
    currentTime = datetime.today().strftime('%Y-%m-%d-%H:%M:%S.%f')
    outputString = currentTime + ": " + inputString + "\n"
    file.write(outputString)