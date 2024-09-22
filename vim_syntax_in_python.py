import re
import os
import time
from os.path import expanduser
from datetime import datetime

HOME = expanduser("~")
TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")
TAGS_FILE_BASE = os.path.join(HOME, ".temp_tags",".temp_tags")
FGL_DIRECTORY_SUFFIX = ".4gs"
FGL_SUFFIX = ".4gl"
LOG_DIRECTORY = os.path.join(TAGS_FILE_DIRECTORY, "fgl_syntax_log")

tokenDictionary = {
    "'" : "'",
    '"' : '"',
    "`" : "`",
    "#" : "\n",
    "--" : "\n",
    "{" : "}"
}

def generateTags(inputString, currentFile, pid, bufNum):
    vimSyntaxStart = time.time()
    writeSingleLineToLog("=========================================================")
    writeSingleLineToLog("vim syntax start for file: " + currentFile)
    writeSingleLineToLog("=========================================================")

    if not os.path.exists(TAGS_FILE_DIRECTORY):
        os.makedirs(TAGS_FILE_DIRECTORY)

    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + ".ctags"
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
    existingFunctionNames = set()

    isImportingLibrary = False

    importFilePath = ""
    concatenatedImportString = ""
    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    tokenLower = "\n"
    isImportingGlobal = False
    globalFilePath = ""
    lineNumber = 1

    for token in tokenList:
        tokenLower, prevToken, prevPrevToken = token, tokenLower, prevToken
        if token == "\n":
            lineNumber += 1

        if isImportingGlobal:
            if (requiredToken == '"' and token != '"') or (requiredToken == "'" and token != "'") or (requiredToken == "`" and token != "`"):
                globalFilePath = globalFilePath + token
            elif (requiredToken == '"' and token == '"') or (requiredToken == "'" and token == "'") or (requiredToken == "`" and token == "`"):
                isImportingGlobal = False
                tagsLinesList.extend(getPublicConstantsFromLibrary(globalFilePath, [globalFilePath], [currentDirectory]))

        if token in tokenDictionary and requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif requiredToken != "" and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        tokenLower = tokenLower.lower() # putting .lower() here so it doesn't run when it doesn't have to

        isPrevPrevTokenEnd = prevPrevToken == "end"
        isPreviousTokenFunctionOrReport = (prevToken == "function") or (prevToken == "report")

        if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd:
            # We create the list of the function tags
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            existingFunctionNames.add(token)
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension]))

        if tokenLower == "import" and prevToken == "\n":
            # we need to check that Import is at the start of the line
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "import" and tokenLower == "fgl":
            continue
        elif isImportingLibrary and prevToken == "import" and not tokenLower == "fgl":
            # for when importing not an FGL library
            isImportingLibrary = False
            continue

        isPreviousTokenAs = prevToken == "as"

        if isImportingLibrary and token != "." and token != "\n" and not tokenLower == "as" and not isPreviousTokenAs:
            importFilePath = os.path.join(importFilePath, token)
            if concatenatedImportString == "":
                concatenatedImportString = token
            else:
                concatenatedImportString = concatenatedImportString + "." + token
            continue

        # When it's imported AS something else, we need to create the tags file, but the mapping line is just a bit different
        # The functionName is the AS file, while the file is the path to the file

        if isImportingLibrary and token == "\n" and not isPreviousTokenAs:
            isImportingLibrary = False
            importFilePath = importFilePath + FGL_SUFFIX
            librariesList.append((importFilePath, concatenatedImportString))
            tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, None))
            importFilePath = ""
            concatenatedImportString = ""
            continue
        elif isImportingLibrary and isPreviousTokenAs:
            isImportingLibrary = False
            librariesList.append((importFilePath, token))
            tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, token))
            importFilePath = ""
            concatenatedImportString = ""
            continue

        if isImportingLibrary and tokenLower == "as":
            importFilePath = importFilePath + FGL_SUFFIX
            continue

        if prevToken == "\n" and tokenLower == "globals":
            isImportingGlobal = True

    startTime = time.time()
    for lib in librariesList:
        importFilePath = lib[0]
        fileAlias = lib[1].split(".")
        tmpTuple = getPublicFunctionsFromLibrary(importFilePath, fileAlias, packagePaths, existingFunctionNames)
        tagsLinesList.extend(tmpTuple[0])
        existingFunctionNames.update(tmpTuple[1])
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting public functions took " + str(lengthTime) + " seconds")

    startTime = time.time()
    tagsLinesList.extend(getMakefileFunctions(currentDirectory, existingFunctionNames))
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting Makefile Functions took " + str(lengthTime) + " seconds")

    writeTagsFile(tagsLinesList, pid, bufNum)

    vimSyntaxEnd = time.time()
    vimSyntaxLengthOfTime = vimSyntaxEnd - vimSyntaxStart
    writeSingleLineToLog("vim syntax for " + currentFile + " took " + str(vimSyntaxLengthOfTime) + " seconds")

def createListOfTags(functionName, currentFile, lineNumber, functionTokens):
    # this is interesting, I would need to, for each separation, create a tagLine
    tagsLinesList = []

    tagLine = "{0}\t{1}\t{2}\n".format(functionName, currentFile, lineNumber)
    tagsLinesList.append(tagLine)

    functionNameString = functionName
    for token in reversed(functionTokens):
        functionNameString = token + "." + functionNameString
        tagsLinesList.append(createSingleTagLine(functionNameString, currentFile, lineNumber))

    return tagsLinesList

def createSingleTagLine(jumpToString, jumpToFile, lineNumber):
    return "{0}\t{1}\t{2}\n".format(jumpToString, jumpToFile, lineNumber)

def writeTagsFile(tagsLinesList, pid, bufNum):
    # The tags file needs to be sorted alphabetically (by ASCII code) in order to work
    tagsLinesList.sort()
    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + ".ctags"
    file = open(tagsFile, "a")
    for line in tagsLinesList:
        file.write(line)
    file.close()

def getPublicFunctionsFromLibrary(importFile, fileAlias, packagePaths, existingFunctionNames):
    # I think Genero probably doesn't have overloading, but I think the priority for function scope goes
    # Current File > Imported Library > OBJFILES > CUSTLIBS > LIBFILES
    writeSingleLineToLog("getting functions from " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + importFile)
        return [], set()

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenizeLinesOfFiles(file)
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    # This is the part where we want to loop through and find the function definitions

    tagsLinesList = []

    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    token = "\n"
    lineNumber = 1

    startTime = time.time()

    for tokenBlock in tokenList:
        token, prevToken, prevPrevToken = tokenBlock, token, prevToken
        if token == "\n":
            lineNumber += 1

        if token in tokenDictionary and requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif requiredToken != "" and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        prevToken = prevToken.lower() # putting .lower() here so it doesn't run when it doesn't have to

        isPrevPrevTokenEnd = prevPrevToken == "end"
        isPrevPrevTokenPrivate = prevPrevToken == "private"
        isPreviousTokenFunctionOrReport = (prevToken == "function") or (prevToken == "report")

        if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd and not isPrevPrevTokenPrivate and token not in existingFunctionNames:
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias))
            existingFunctionNames.add(token)
            continue

        isPrevPrevTokenPublic = prevPrevToken == "public"
        isPrevTokenConstant = prevToken == "constant"

        if isPrevTokenConstant and isPrevPrevTokenPublic:
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return tagsLinesList, existingFunctionNames

def tokenizeString(inputString):
    # basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
    # the repeating section contains all the special characters in Genero
    # probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards

    # this regex is a bit more efficient than before, not sure if it can be even more efficient
    tokenBlock = re.findall(r"\w+|!|\"|#|\$|%|&|'|\(|\)|\*|\+|,|--|-|\/|\.|:|;|<|=|>|\?|@|\[|\\+|\]|\^|`|{|\||}|~", inputString)
    return tokenBlock

def findVariableDefinition(buffer):
    tokenList = tokenizeLinesOfFiles(buffer)

    prevToken = ""
    token = "\n"
    lineNumber = 0
    for tokenBlock in tokenList:
        prevToken = token
        token = tokenBlock
        if token == "\n":
            lineNumber += 1

        # this section is all about skipping based on strings and comments
        if token in tokenDictionary and requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif requiredToken != "" and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
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
    lineNumber = 0

    for tokenBlock in tokenList:
        token, prevToken = tokenBlock, token
        if token == "\n":
            lineNumber += 1

        # this section is all about skipping based on strings and comments
        if token in tokenDictionary and requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif requiredToken != "" and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        token = token.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if token == "function" or token == "report":
            latestFunctionLineNumber = lineNumber

    return latestFunctionLineNumber

def tokenizeLinesOfFiles(file):
    tokenList = []
    for line in file:
        tokenBlock = tokenizeString(line)
        tokenBlock.append("\n")
        tokenList.extend([token for token in tokenBlock])
    return tokenList

def getRequiredToken(inputToken):
    return tokenDictionary.get(inputToken, "")

def removeTempTags(pid, bufNum):
    try:
        tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + ".ctags"
        os.remove(tagsFile)
    except OSError:
        pass

def getMakefileFunctions(currentDirectory, existingFunctionNames):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return []
    file = open(makeFile, "r")
    tokenList = tokenizeLinesOfFiles(file)

    tagsList = []
    objFileList = []
    custLibFileList = []
    libFileList = []
    globalFileList = []

    importingFileType = ""

    prevPrevToken = ""
    prevToken = ""
    token = "\n"

    libFilePath = ""

    packagePaths = []
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    for tokenBlock in tokenList:
        if tokenBlock == "":
            continue

        token, prevToken, prevPrevToken = tokenBlock, token, prevToken
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
                    writeSingleLineToLog("can't find " + libFilePath)
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

    startTime = time.time()
    for obj in objFileList:
        tmpTuple = getPublicFunctionsFromLibrary(obj[0], [obj[1]], [currentDirectory], existingFunctionNames)
        tagsList.extend(tmpTuple[0])
        existingFunctionNames.update(tmpTuple[1])
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("OBJFILES took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for custLib in custLibFileList:
        tmpTuple = getPublicFunctionsFromLibrary(custLib[0], [custLib[1]], packagePaths, existingFunctionNames)
        tagsList.extend(tmpTuple[0])
        existingFunctionNames.update(tmpTuple[1])
    endTime = time.time()
    writeSingleLineToLog("CUSTLIBS took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for libFile in libFileList:
        tmpTuple = getPublicFunctionsFromLibrary(libFile, [os.path.splitext(os.path.basename(libFile))[0]], [libFilePath], existingFunctionNames)
        tagsList.extend(tmpTuple[0])
    endTime = time.time()
    writeSingleLineToLog("LIBFILES took " + str(lengthTime) + " seconds")

    startTime = time.time()
    for globalFile in globalFileList:
        tagsList.extend(getPublicConstantsFromLibrary(globalFile[0], [globalFile[1]], [currentDirectory]))
    endTime = time.time()
    writeSingleLineToLog("GLOBALS took " + str(lengthTime) + " seconds")

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

def createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, fileAlias):
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFilePath)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + concatenatedImportString)
        return []

    tagsLineList = [createSingleTagLine(concatenatedImportString, packageFile, 1)]

    if fileAlias is not None:
        tagsLineList.append(createSingleTagLine(fileAlias, packageFile, 1))

    return tagsLineList

def getPublicConstantsFromLibrary(importFile, fileAlias, packagePaths):
    writeSingleLineToLog("getting constants from " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + importFile)
        return []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenizeLinesOfFiles(file)
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    tagsLinesList = []

    requiredToken = ""
    prevPrevToken = ""
    prevToken = ""
    token = "\n"
    lineNumber = 0

    startTime = time.time()

    for tokenBlock in tokenList:
        token, prevToken, prevPrevToken = tokenBlock, token, prevToken
        if token == "\n":
            lineNumber += 1

        # this section is all about skipping based on strings and comments
        if token in tokenDictionary and requiredToken == "":
            requiredToken = getRequiredToken(token)
        elif requiredToken != "" and token != requiredToken:
            continue
        elif ((token == "'" and requiredToken == "'") or (token == '"' and requiredToken == '"')) and re.match(r"^\\(\\\\)*$", prevToken):
            continue
        elif token == requiredToken:
            requiredToken = ""
            continue

        prevToken = prevToken.lower() # putting .lower() here so it doesn't run when it doesn't have to

        isPrevPrevTokenPublic = prevPrevToken == "public"
        isPrevTokenConstant = prevToken == "constant"

        if isPrevTokenConstant and isPrevPrevTokenPublic:
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return tagsLinesList