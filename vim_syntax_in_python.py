import re
import os
import time
import shutil
import vim # type: ignore
from os.path import expanduser
from datetime import datetime

HOME = expanduser("~")
TAGS_FILE_DIRECTORY = os.path.join(HOME, ".temp_tags")
TAGS_FILE_BASE = os.path.join(HOME, ".temp_tags",".temp_tags")
FGL_DIRECTORY_SUFFIX = ".4gs"
FGL_SUFFIX = ".4gl"
LOG_DIRECTORY = os.path.join(TAGS_FILE_DIRECTORY, "fgl_syntax_log")
TAGS_SUFFIX = ".ctags"
CONSTANTS_SUFFIX = ".cons"

GENERO_KEY_WORDS = set()
KEYWORDS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "genero_key_words.txt")
if os.path.isfile(KEYWORDS_FILE):
    GENERO_KEY_WORDS.update(open(KEYWORDS_FILE, "r").read().split("\n"))

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
    startTime = time.time()
    writeSingleLineToLog("=========================================================")
    writeSingleLineToLog("vim syntax start for file: " + currentFile)
    writeSingleLineToLog("=========================================================")

    if not os.path.exists(TAGS_FILE_DIRECTORY):
        os.makedirs(TAGS_FILE_DIRECTORY)

    vim.command("execute 'set tags='") # resets the tags

    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + TAGS_SUFFIX

    searchString = r"\b" + re.escape(pid + "." + bufNum) + r"\b" + r"\.\w+" + re.escape(TAGS_SUFFIX)

    allTagFiles = os.listdir(TAGS_FILE_DIRECTORY)
    for f in allTagFiles:
        existingTagsFile = os.path.join(TAGS_FILE_DIRECTORY, f)
        if os.path.isfile(existingTagsFile) and re.search(searchString, os.path.join(TAGS_FILE_DIRECTORY, f)):
            vim.command("execute 'set tags+=" + existingTagsFile + "'")

    currentDirectory = os.path.dirname(currentFile)
    packagePaths = [currentDirectory]
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    tokenList = tokenizeString(inputString)

    # This is the part where we want to loop through and find the function definitions in the current file
    tagsLinesList = []
    librariesList = []
    existingFunctionNames = set()
    existingTypes = {}

    isImportingLibrary = False
    isTypeFunction = False
    currentType = ""

    isDefiningVariable = False

    importFilePath = ""
    concatenatedImportString = ""
    requiredToken = None
    prevPrevToken = ""
    prevToken = ""
    tokenLower = "\n"
    isImportingGlobal = False
    globalFilePath = ""
    lineNumber = 1

    for token in tokenList:
        tokenLower, prevToken = token, tokenLower
        if token == "\n":
            lineNumber += 1
        else:
            prevTokenNotNewline = tokenLower
            prevPrevToken = prevToken

        if isImportingGlobal:
            if (requiredToken == '"' and token != '"') or (requiredToken == "'" and token != "'") or (requiredToken == "`" and token != "`"):
                globalFilePath = globalFilePath + token
            elif (requiredToken == '"' and token == '"') or (requiredToken == "'" and token == "'") or (requiredToken == "`" and token == "`"):
                isImportingGlobal = False
                tagsLinesList.extend(getPublicConstantsFromLibrary(globalFilePath, [globalFilePath], [currentDirectory])[0])

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

        if ((prevToken == "function") or (prevToken == "report")) and not prevPrevToken == "end":
            if token == "(":
                isTypeFunction = True
                continue
            else:
                # We create the list of regular function tags
                fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
                tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=existingFunctionNames))
                existingFunctionNames.add(token)
                continue

        if isTypeFunction and not prevToken == "(" and not prevToken == ")" and not token == ")":
            currentType = token
            continue

        if isTypeFunction and prevToken == ")":
            if currentType in existingTypes:
                existingTypes[currentType].add(token)
            isTypeFunction = False
            currentType = ""
            continue

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
            continue

        if prevToken == "constant":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))
            continue

        if prevToken == "type":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            existingTypes[token] = set()
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))
            continue

        if tokenLower == "define":
            isDefiningVariable = True
            continue

        if isDefiningVariable and token in existingFunctionNames:
            pass

    writeTagsFile(tagsLinesList, tagsFile, "w")
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("going through current buffer took " + str(lengthTime) + " seconds")

    constantsFile = os.path.join(TAGS_FILE_DIRECTORY, ".constants." + pid + "." + bufNum + CONSTANTS_SUFFIX)

    startTime = time.time()
    for lib in librariesList:
        importFilePath = lib[0]
        fileAlias = lib[1].split(".")
        libraryTagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + "." + lib[1] + TAGS_SUFFIX
        if not os.path.isfile(libraryTagsFile):
            tmpTuple = getPublicFunctionsFromLibrary(importFilePath, fileAlias, packagePaths, existingFunctionNames)
            if tmpTuple[0] is not None:
                writeTagsFile(tmpTuple[0], libraryTagsFile, "a")
                existingFunctionNames.update(tmpTuple[1])
            if tmpTuple[2] is not None:
                writeConstantsFile(tmpTuple[2], constantsFile, "a")
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting public functions took " + str(lengthTime) + " seconds")

    startTime = time.time()
    makefileTagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + ".Makefile" + TAGS_SUFFIX
    if not os.path.isfile(makefileTagsFile):
        writeTagsFile(getMakefileFunctions(currentDirectory, existingFunctionNames), makefileTagsFile, "a")
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting Makefile Functions took " + str(lengthTime) + " seconds")

    vimSyntaxEnd = time.time()
    vimSyntaxLengthOfTime = vimSyntaxEnd - vimSyntaxStart
    writeSingleLineToLog("vim syntax for " + currentFile + " took " + str(vimSyntaxLengthOfTime) + " seconds")

    highlightExistingConstants(constantsFile)

def generateTagsForCurrentBuffer(inputString, currentFile, pid, bufNum):
    vimSyntaxStart = time.time()
    writeSingleLineToLog("=========================================================")
    writeSingleLineToLog("vim syntax start for file: " + currentFile)
    writeSingleLineToLog("=========================================================")

    if not os.path.exists(TAGS_FILE_DIRECTORY):
        os.makedirs(TAGS_FILE_DIRECTORY)

    tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + TAGS_SUFFIX

    currentDirectory = os.path.dirname(currentFile)
    packagePaths = [currentDirectory]
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    tokenList = tokenizeString(inputString)

    # This is the part where we want to loop through and find the function definitions in the current file
    tagsLinesList = []
    existingFunctionNames = set()

    isImportingLibrary = False

    importFilePath = ""
    concatenatedImportString = ""
    requiredToken = None
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
                tagsLinesList.extend(getPublicConstantsFromLibrary(globalFilePath, [globalFilePath], [currentDirectory])[0])

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

        if ((prevToken == "function") or (prevToken == "report")) and not prevPrevToken == "end":
            # We create the list of the function tags
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            existingFunctionNames.add(token)
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=existingFunctionNames))
            continue

        if tokenLower == "import" and prevToken == "\n":
            # we need to check that Import is at the start of the line
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "import" and tokenLower == "fgl":
            continue
        elif isImportingLibrary and prevToken == "import" and not tokenLower == "fgl" and token != ".":
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
            tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, None))
            importFilePath = ""
            concatenatedImportString = ""
            continue
        elif isImportingLibrary and isPreviousTokenAs:
            isImportingLibrary = False
            tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, token))
            importFilePath = ""
            concatenatedImportString = ""
            continue

        if isImportingLibrary and tokenLower == "as":
            importFilePath = importFilePath + FGL_SUFFIX
            continue

        if prevToken == "\n" and tokenLower == "globals":
            isImportingGlobal = True
            continue

        if prevToken == "constant":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))

        if prevToken == "type":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))

    writeTagsFile(tagsLinesList, tagsFile, "w")

    constantsFile = os.path.join(TAGS_FILE_DIRECTORY, ".constants." + pid + "." + bufNum + CONSTANTS_SUFFIX)
    highlightExistingConstants(constantsFile)

    vimSyntaxEnd = time.time()
    vimSyntaxLengthOfTime = vimSyntaxEnd - vimSyntaxStart
    writeSingleLineToLog("vim syntax for " + currentFile + " took " + str(vimSyntaxLengthOfTime) + " seconds")

def createListOfTags(functionName, currentFile, lineNumber, functionTokens, existingFunctionNames):
    # this is interesting, I would need to, for each separation, create a tagLine
    tagsLinesList = []

    # I've inlined the createSingleTagLine() function to increase the speed very marginally
    if existingFunctionNames is None:
        tagsLinesList.append("%s\t%s\t%s\n" % (functionName, currentFile, lineNumber))
    elif functionName not in existingFunctionNames:
        tagsLinesList.append("%s\t%s\t%s\n" % (functionName, currentFile, lineNumber))
    elif len(existingFunctionNames) == 0:
        tagsLinesList.append("%s\t%s\t%s\n" % (functionName, currentFile, lineNumber))

    functionNameString = functionName
    for token in reversed(functionTokens):
        functionNameString = "%s.%s" % (token, functionNameString)
        tagsLinesList.append("%s\t%s\t%s\n" % (functionNameString, currentFile, lineNumber))

    return tagsLinesList

def createSingleTagLine(jumpToString, jumpToFile, lineNumber):
    return "%s\t%s\t%s\n" % (jumpToString, jumpToFile, lineNumber)

def writeTagsFile(tagsLinesList, tagsFile, mode):
    # The tags file needs to be sorted alphabetically (by ASCII code) in order to work
    tagsLinesList.sort()
    file = open(tagsFile, mode)
    file.write("".join(tagsLinesList))
    file.close()
    vim.command("execute 'set tags+=" + tagsFile + "'")

def writeConstantsFile(constantsList, constantsFile, mode):
    file = open(constantsFile, mode)
    file.write("".join(constantsList))
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
        return [], set(), []

    file = open(packageFile, "r")

    startTime = time.time()
    tokenList = tokenizeString(file.read())
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    # This is the part where we want to loop through and find the function definitions

    tagsLinesList = []
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
            # We create the list of the function tags
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=existingFunctionNames))
            existingFunctionNames.add(token)
            continue

        if prevToken == "constant" and prevPrevToken == "public":
            if token not in GENERO_KEY_WORDS:
                constantsList.append("%s%s" % (token, "\n"))
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=None))

        if prevToken == "type" and prevPrevToken == "public":
            if token not in GENERO_KEY_WORDS:
                constantsList.append("%s%s" % (token, "\n"))
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=None))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return tagsLinesList, existingFunctionNames, constantsList

def tokenizeString(inputString):
    # basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
    # the repeating section contains all the special characters in Genero
    # probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards

    # this regex is a bit more efficient than before, not sure if it can be even more efficient
    tokenBlock = re.findall(r"\w+|!|\"|#|\$|%|&|'|\(|\)|\*|\+|,|--|-|\/|\.|:|;|<|=|>|\?|@|\[|\\+|\]|\^|`|{|\||}|~|\n", inputString)
    return tokenBlock

def findVariableDefinition(buffer):
    tokenList = tokenizeString(buffer)

    requiredToken = None
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0
    for token in tokenList:
        prevToken = tmpToken
        token = token
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

def findFunctionWrapper(buffer):
    tokenList = tokenizeString(buffer)
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

def removeTempTags(pid, bufNum):
    try:
        tagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + TAGS_SUFFIX
        os.remove(tagsFile)
    except OSError:
        pass

def getMakefileFunctions(currentDirectory, existingFunctionNames):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return []
    file = open(makeFile, "r")
    tokenList = tokenizeString(file.read())

    tagsList = []
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
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("checking tokens in Makefile took " + str(lengthTime) + " seconds")

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
        tmpTuple = getPublicConstantsFromLibrary(globalFile[0], [globalFile[1]], [currentDirectory])
        tagsList.extend(tmpTuple[0])
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
    tokenList = tokenizeString(file.read())
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    tagsLinesList = []
    constantsList = []

    requiredToken = None
    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0

    startTime = time.time()

    for token in tokenList:
        tmpToken, prevToken, prevPrevToken = token, tmpToken, prevToken
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
            requiredToken is None
            continue

        prevToken = prevToken.lower() # putting .lower() here so it doesn't run when it doesn't have to

        if prevToken == "constant" and prevPrevToken == "public":
            # We create the list of the function tags
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
                constantsList.append(token)
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=None))

        if prevToken == "type" and prevPrevToken == "public":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
                constantsList.append(token)
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=None))

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return tagsLinesList, constantsList

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
            writeSingleLineToLog("archived " + tagsFile)

def highlightExistingConstants(constantsFile):
    if os.path.isfile(constantsFile):
        highlightExistingConstants = open(constantsFile, "r").read().split("\n")
        for const in highlightExistingConstants:
            vim.command("execute 'syn match constantGroup /\\<" + const + "\\>/'")