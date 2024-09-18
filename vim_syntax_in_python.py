import re
import os
import time
from os.path import expanduser
from datetime import datetime

HOME = expanduser("~")
TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")
TAGS_FILE_BASE = os.path.join(HOME, ".temp_tags",".temp_tags")
FGL_SUFFIX = ".4gl"
LOG_DIRECTORY = os.path.join(TAGS_FILE_DIRECTORY, "fgl_syntax_log")

def generateTags(inputString, currentFile, pid, bufNum):
    start = time.time()
    writeSingleLineToLog("vim syntax start")

    if not os.path.exists(TAGS_FILE_DIRECTORY):
        os.makedirs(TAGS_FILE_DIRECTORY)

    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum
    if os.path.exists(tagsFile):
        writeSingleLineToLog("vim tags file: " + tagsFile + " exists, exiting")
        return

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

        token, prevToken, prevPrevToken = tokenBlock[0], token, prevToken
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
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=currentFile, fileAlias=fileWithoutExtension))

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

def createListOfTags(functionName, lineNumber, currentFile, fileAlias):
    # this is interesting, I would need to, for each separation, create a tagLine
    tagsLinesList = []
    functionTokens = fileAlias.split(".")

    tagLine = "{0}\t{1}\t{2}\n".format(functionName, currentFile, lineNumber)
    tagsLinesList.append(tagLine)

    functionNameString = functionName
    for token in reversed(functionTokens):
        functionNameString = token + "." + functionNameString
        tagLine = "{0}\t{1}\t{2}\n".format(functionNameString, currentFile, lineNumber)
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
    writeSingleLineToLog("finding file " + importFilePath)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFilePath)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + importFilePath)
        return []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenizeLinesOfFiles(file)
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFilePath + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    # This is the part where we want to loop through and find the function definitions

    tagsLinesList = []

    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    token = "\n"

    startTime = time.time()

    for tokenBlock in tokenList:
        # occasionally there are blank tokens
        if tokenBlock[0] == "":
            continue

        token, prevToken, prevPrevToken = tokenBlock[0], token, prevToken
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
        isPrevPrevTokenPrivate = prevPrevToken.lower() == "private"
        isPreviousTokenFunctionOrReport = (prevToken.lower() == "function") or (prevToken.lower() == "report")

        if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd and not isPrevPrevTokenPrivate:
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=packageFile, fileAlias=fileAlias))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return tagsLinesList


def tokenizeString(inputString):
    # basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
    # the repeating section contains all the special characters in Genero
    # probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards
    tokenBlock = re.findall(r"(?:(?!\.|,|'|`|\"|\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|=|\*)[!-~])+|\.|,|'|`|\"|\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|=|\*", inputString)
    return tokenBlock


def findVariableDefinition(buffer):
    tokenList = tokenizeLinesOfFiles(buffer)

    prevToken = ""
    token = "\n"
    for tokenBlock in tokenList:
        # occasionally there are blank tokens
        if tokenBlock[0] == "":
            continue

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


def findFunctionWrapper(buffer):
    tokenList = tokenizeLinesOfFiles(buffer)
    requiredToken = ""
    prevToken = ""
    token = "\n"

    latestFunctionLineNumber = 0

    for tokenBlock in tokenList:
        # occasionally there are blank tokens
        if tokenBlock[0] == "":
            continue

        token, prevToken = tokenBlock[0], token
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

        if token.lower() == "function" or token.lower() == "report":
            latestFunctionLineNumber = lineNumber

    return latestFunctionLineNumber


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

    isImportingLibFiles = False
    isImportingObjectFiles = False
    prevPrevToken = ""
    prevToken = ""
    token = "\n"

    packagePaths = []
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    for tokenBlock in tokenList:
        if tokenBlock[0] == "":
            continue

        token, prevToken, prevPrevToken = tokenBlock[0], token, prevToken
        lineNumber = tokenBlock[1]

        curDir = [currentDirectory]

        if token == "=" and prevToken == "OBJFILES":
            isImportingObjectFiles = True

        if token == "=" and prevToken != "OBJFILES":
            isImportingObjectFiles = False

        if isImportingObjectFiles and token == "o" and prevToken == ".":
            file = prevPrevToken + FGL_SUFFIX
            writeSingleLineToLog(file)
            tagsList.extend(getPublicFunctionsFromLibrary(file, prevPrevToken, currentDirectory, curDir))


        if token == "=" and prevToken == "CUSTLIBS":
            isImportingLibFiles = True

        if token == "=" and prevToken != "CUSTLIBS":
            isImportingLibFiles = False

        if isImportingLibFiles and token == "o" and prevToken == ".":
            file = prevPrevToken + FGL_SUFFIX
            writeSingleLineToLog(file)
            tagsList.extend(getPublicFunctionsFromLibrary(file, prevPrevToken, currentDirectory, packagePaths))

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