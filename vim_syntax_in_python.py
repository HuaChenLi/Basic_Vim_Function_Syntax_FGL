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
    GENERO_KEY_WORDS.update(open(KEYWORDS_FILE, "r").read().lower().split("\n"))

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

    searchString = r"\b" + re.escape(pid + "." + bufNum) + r"\b" + r"[\.\w]+" + re.escape(TAGS_SUFFIX)

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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if ((prevTokenNotNewline == "function") or (prevTokenNotNewline == "report")) and not prevPrevToken == "end":
            if token == "(":
                isTypeFunction = True
                continue
            else:
                # We create the list of regular function tags
                fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
                tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=existingFunctionNames))
                existingFunctionNames.add(token)
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
                tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, token))
            elif token == "\n":
                importFilePath = importFilePath + FGL_SUFFIX
                librariesList.append((importFilePath, concatenatedImportString))
                tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, None))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if prevToken == "\n" and tokenLower == "globals":
            isImportingGlobal = True
            continue

        if prevTokenNotNewline == "constant":
            if tokenLower not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))
            continue

        if prevTokenNotNewline == "type":
            if tokenLower not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            existingTypes[token] = []
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))
            continue

        if not isDefiningVariable and tokenLower == "define":
            isDefiningVariable = True
            continue

        if isDefiningVariable and (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token != "\n":
            currentVariables.add(token)
            continue

        if isDefiningVariable and not (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token in existingTypes:
            tagsLinesList.extend(createListOfTypeMethodTags(currentVariables, existingTypes[token], currentFile))
            currentVariables = set()

        # this statement is 100% gonna fail with DYNAMIC ARRAY OF RECORD
        if isDefiningVariable and token != "\n" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and prevPrevToken != "define":
            isDefiningVariable = False
            currentVariables = set()

    writeTagsFile(tagsLinesList, tagsFile, "w")
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("going through current buffer took " + str(lengthTime) + " seconds")

    constantsFile = os.path.join(TAGS_FILE_DIRECTORY, ".constants." + pid + "." + bufNum + CONSTANTS_SUFFIX)

    constantsList = []
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
                constantsList.extend(tmpTuple[2])
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting public functions took " + str(lengthTime) + " seconds")

    startTime = time.time()
    makefileTagsFile = TAGS_FILE_BASE + "." + pid + "." + bufNum + ".Makefile" + TAGS_SUFFIX
    if not os.path.isfile(makefileTagsFile):
        tmpTuple = getMakefileFunctions(currentDirectory, existingFunctionNames)
        writeTagsFile(tmpTuple[0], makefileTagsFile, "a")
        constantsList.extend(tmpTuple[1])
    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("getting Makefile Functions took " + str(lengthTime) + " seconds")

    writeConstantsFile(constantsList, constantsFile, "a")
    highlightExistingConstants(constantsFile)

    vimSyntaxEnd = time.time()
    vimSyntaxLengthOfTime = vimSyntaxEnd - vimSyntaxStart
    writeSingleLineToLog("vim syntax for " + currentFile + " took " + str(vimSyntaxLengthOfTime) + " seconds")

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

    existingTypes = {}
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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if ((prevTokenNotNewline == "function") or (prevTokenNotNewline == "report")) and not prevPrevToken == "end":
            if token == "(":
                isTypeFunction = True
                continue
            else:
                # We create the list of the function tags
                fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
                tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=existingFunctionNames))
                existingFunctionNames.add(token)
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
                tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, token))
            elif token == "\n":
                importFilePath = importFilePath + FGL_SUFFIX
                tagsLinesList.extend(createImportLibraryTag(importFilePath, concatenatedImportString, packagePaths, None))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if prevToken == "\n" and tokenLower == "globals":
            isImportingGlobal = True
            continue

        if prevTokenNotNewline == "constant":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))

        if prevTokenNotNewline == "type":
            if token not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
            fileWithoutExtension = os.path.splitext(os.path.basename(currentFile))[0]
            existingTypes[token] = []
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=currentFile, lineNumber=lineNumber, functionTokens=[fileWithoutExtension], existingFunctionNames=None))

        if not isDefiningVariable and tokenLower == "define":
            isDefiningVariable = True
            continue

        if isDefiningVariable and (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token != "\n":
            currentVariables.add(token)
            continue

        if isDefiningVariable and not (prevTokenNotNewline == "define" or prevTokenNotNewline == ",") and token in existingTypes:
            tagsLinesList.extend(createListOfTypeMethodTags(currentVariables, existingTypes[token], currentFile))

        if isDefiningVariable and token != "\n" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and not prevTokenNotNewline in currentVariables:
            isDefiningVariable = False
            currentVariables = set()

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

def createListOfTypeMethodTags(currentVariables, typeDefinition, jumpToFile):
    tagsLineList = []
    for v in currentVariables:
        for t in typeDefinition:
            tagsLineList.append("%s.%s\t%s\t%s\n" % (v, t[0], jumpToFile, t[1]))
    return tagsLineList

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

def findVariableDefinition(varName, buffer, currentFile, currentLineNumber):
    startTime = time.time()

    tokenList = tokenizeString(buffer)

    currentDirectory = os.path.dirname(currentFile)
    packagePaths = [currentDirectory]
    try:
        # allows the environment variable to be split depending on the os
        packagePaths.extend(os.environ['FGLLDPATH'].split(os.pathsep))
    except:
        # this is in case the FGLLDPATH doesn't exist
        pass

    # if the token has ".", then we need to match it with either functions or the public types
    parts = varName.split(".")
    writeSingleLineToLog(str(len(parts)))
    if len(parts) > 2:
        # then this can only be function call or type/constant definition
        tmpTuple = findFunctionDefinitionFromLibraryPackage(varName, tokenList, packagePaths)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]
    elif len(parts) == 2:
        # then this can be only be function/method call or type/constant definition
        # did not factor in importing libraries, like libPackage.file
        tmpTuple = findFunctionAndMethods(varName, tokenList, currentFile, packagePaths, currentLineNumber)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]
    else:
        # if len(parts) == 1, then can only be function call or type/constant definition
        # did not factor in importing libraries, like libFile
        tmpTuple = findSingularToken(varName, tokenList, currentFile, packagePaths, currentLineNumber)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]

    endTime = time.time()
    lengthTime = endTime - startTime
    writeSingleLineToLog("looking for definition took " + str(lengthTime))

    return packageFile, functionLine

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
        return [], []
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

    constantsList = []
    startTime = time.time()
    for globalFile in globalFileList:
        tmpTuple = getPublicConstantsFromLibrary(globalFile[0], [globalFile[1]], [currentDirectory])
        tagsList.extend(tmpTuple[0])
        constantsList.extend(tmpTuple[1])
    endTime = time.time()
    writeSingleLineToLog("GLOBALS took " + str(lengthTime) + " seconds")

    return tagsList, constantsList

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
        return [], []

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
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
                constantsList.append("%s%s" % (token, "\n"))
            tagsLinesList.extend(createListOfTags(functionName=token, currentFile=packageFile, lineNumber=lineNumber, functionTokens=fileAlias, existingFunctionNames=None))
            continue

        # this statement is 100% gonna fail with DYNAMIC ARRAY OF RECORD
        if isDefiningConstant and token != "\n" and prevToken != "\n" and token != "," and token != "=" and token not in tokenDictionary and prevTokenNotNewline != "," and prevPrevToken != "define":
            isDefiningConstant = False

        if prevToken == "type" and not prevPrevToken == "private":
            if token.lower() not in GENERO_KEY_WORDS:
                vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")
                constantsList.append("%s%s" % (token, "\n"))
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

def findFunctionDefinitionFromLibraryPackage(varName, tokenList, packagePaths):
    requiredToken = None
    isImportingLibrary = False
    concatenatedImportString = ""
    prevTokenNotNewline = ""
    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0

    importFilePath = ""
    packageFile = ""
    functionLine = 0

    prefix = varName.rsplit(".", 1)[0]
    functionName = varName.rsplit(".", 1)[1]

    for token in tokenList:
        prevToken = tmpToken.lower()
        tmpToken = token
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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if prevToken == "fgl" and prevPrevToken == "import":
            importFilePath = token
            concatenatedImportString = token
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "." and token != "\n":
            importFilePath = os.path.join(importFilePath, token)
            concatenatedImportString = concatenatedImportString + "." + token
            continue

        if isImportingLibrary and concatenatedImportString.endswith(varName):
            packageFile = checkLibraryExists(importFilePath + FGL_SUFFIX, packagePaths)
            functionLine = 1
            break

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
            elif token == "\n":
                importFilePath = importFilePath + FGL_SUFFIX
                if concatenatedImportString.endswith(prefix):
                    tmpTuple = findFunctionFromSpecificLibrary(importFilePath, packagePaths, functionName)
                    packageFile = tmpTuple[0]
                    functionLine = tmpTuple[1]
                    break

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

    return packageFile, functionLine

def findFunctionFromSpecificLibrary(importFile, packagePaths, functionName):
    writeSingleLineToLog("getting functions from here " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        writeSingleLineToLog(packageFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + importFile)
        return "", 0

    file = open(packageFile, "r")
    fileContent = file.read()

    if not re.search(functionName, fileContent):
        writeSingleLineToLog("no function name in here")
        return "", 0

    startTime = time.time()
    tokenList = tokenizeString(fileContent)
    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    requiredToken = None
    prevPrevToken = ""
    prevTokenNotNewline = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0
    functionLine = 0

    startTime = time.time()

    for token in tokenList:
        tmpToken, prevToken = token, tmpToken
        if prevToken == "\n":
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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if token == functionName and ((prevTokenNotNewline == "function") or (prevTokenNotNewline == "report")) and not prevPrevToken == "end" and not prevPrevToken == "private":
            writeSingleLineToLog("found public function " + token)
            functionLine = lineNumber
            break

        if token == functionName and prevTokenNotNewline == "constant" and not prevPrevToken == "private":
            writeSingleLineToLog("found public constant " + token)
            functionLine = lineNumber
            break

        if token == functionName and prevTokenNotNewline == "type" and not prevPrevToken == "private":
            writeSingleLineToLog("found public type " + token)
            functionLine = lineNumber
            break

    endTime = time.time()
    length = endTime - startTime
    writeSingleLineToLog("if statements took " + str(length) + " seconds")

    return packageFile, functionLine

def findSingularToken(varName, tokenList, currentFile, packagePaths, currentLineNumber):
    isDefiningVariable = False
    isLibraryFunction = False
    isFunctionFound = False
    isVarFound = False
    isImportingGlobal = False
    isImportingLibrary = False
    requiredToken = None
    prevTokenNotNewline = ""
    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"
    globalFilePath = ""
    lineNumber = 0

    packageFile = ""
    functionLine = 0

    librariesList = []

    currentDirectory = os.path.dirname(currentFile)

    variableList = set()

    for token in tokenList:
        prevToken = tmpToken.lower()
        tmpToken = token
        if prevToken == "\n":
            lineNumber += 1

        if isImportingGlobal:
            if (requiredToken == '"' and token != '"') or (requiredToken == "'" and token != "'") or (requiredToken == "`" and token != "`"):
                globalFilePath = globalFilePath + token
            elif (requiredToken == '"' and token == '"') or (requiredToken == "'" and token == "'") or (requiredToken == "`" and token == "`"):
                isImportingGlobal = False

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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if prevToken == "fgl" and prevPrevToken == "import":
            importFilePath = token
            concatenatedImportString = token
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "." and token != "\n":
            importFilePath = os.path.join(importFilePath, token)
            concatenatedImportString = concatenatedImportString + "." + token
            continue

        if isImportingLibrary and concatenatedImportString.endswith(varName):
            packageFile = checkLibraryExists(importFilePath + FGL_SUFFIX, packagePaths)
            functionLine = 1
            isLibraryFunction = True
            break

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
                writeSingleLineToLog("with alias " + importFilePath)
                librariesList.append((importFilePath, token))
                if varName == token:
                    packageFile = checkLibraryExists(importFilePath, packagePaths)
                    functionLine = 1
                    isLibraryFunction = True
                    break
            elif token == "\n" and prevPrevToken != "as":
                importFilePath = importFilePath + FGL_SUFFIX
                writeSingleLineToLog("without alias " + importFilePath)
                librariesList.append((importFilePath, concatenatedImportString))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if not isDefiningVariable and prevTokenNotNewline == "define":
            variableList.add(token)
            isDefiningVariable = True

        if token == varName:
            if lineNumber < currentLineNumber and isDefiningVariable and (prevTokenNotNewline == "define" or prevTokenNotNewline == ","):
                writeSingleLineToLog("Found Definition " + token) # remove later
                isVarFound = True
                packageFile = currentFile
                functionLine = lineNumber
                continue
            if (prevTokenNotNewline == "function" or prevTokenNotNewline == "report") and prevPrevToken != "end":
                writeSingleLineToLog("Found Function " + token) # remove later
                isFunctionFound = True
                break
            elif prevTokenNotNewline == "constant":
                writeSingleLineToLog("Found Constant" + token) # remove later
                isFunctionFound = True
                break
            elif prevTokenNotNewline == "type":
                writeSingleLineToLog("Found Type " + token) # remove later
                isFunctionFound = True
                break

        if isDefiningVariable and token != "\n" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and token not in variableList and token not in GENERO_KEY_WORDS:
            isDefiningVariable = False
            variableList = set()

    if isFunctionFound and not isLibraryFunction:
        packageFile = currentFile
        functionLine = lineNumber

    if not isFunctionFound and not isVarFound and not isLibraryFunction:
        # look in other files
        # Current File > Imported Library > OBJFILES > CUSTLIBS > LIBFILES
        for l in librariesList:
            # need to loop through each library and check if has string
            tmpTuple = findFunctionFromSpecificLibrary(l[0], packagePaths, varName)
            if tmpTuple[0] != "":
                packageFile = tmpTuple[0]
                functionLine = tmpTuple[1]
                isFunctionFound = True
                break

    if not isFunctionFound and not isLibraryFunction and not isVarFound:
        # need to get Makefile functions
        tmpTuple = findFunctionFromMakefile(currentDirectory, varName)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]

    return packageFile, functionLine

def findFunctionFromMakefile(currentDirectory, varName):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return "", 0
    file = open(makeFile, "r")
    tokenList = tokenizeString(file.read())

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
    packageFile = ""
    functionLine = 0
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

    writeSingleLineToLog("looking at OBJFILES")
    for obj in objFileList:
        tmpTuple = findFunctionFromSpecificLibrary(obj[0], [currentDirectory], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    writeSingleLineToLog("looking at CUSTLIBS")
    for custLib in custLibFileList:
        tmpTuple = findFunctionFromSpecificLibrary(custLib[0], packagePaths, varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    writeSingleLineToLog("looking at LIBFILES")
    for libFile in libFileList:
        writeSingleLineToLog(libFile)
        tmpTuple = findFunctionFromSpecificLibrary(libFile, [libFilePath], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    writeSingleLineToLog("looking at GLOBALS")
    for globalFile in globalFileList:
        tmpTuple = findFunctionFromSpecificLibrary(globalFile[0], [currentDirectory], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    return packageFile, functionLine

def findFunctionAndMethods(varName, tokenList, currentFile, packagePaths, currentLineNumber):
    isFunctionFound = False
    isLibraryFunction = False
    isVarFound = False
    isImportingGlobal = False
    isImportingLibrary = False
    requiredToken = None
    prevTokenNotNewline = ""
    prevPrevToken = ""
    prevToken = ""
    tmpToken = "\n"
    globalFilePath = ""
    lineNumber = 0

    concatenatedImportString = ""
    packageFile = ""
    functionLine = 0

    librariesList = []

    prefix = varName.rsplit(".", 1)[0]
    functionName = varName.rsplit(".", 1)[1]

    currentDirectory = os.path.dirname(currentFile)

    writeSingleLineToLog("brand new function")

    for token in tokenList:
        prevToken = tmpToken.lower()
        tmpToken = token
        if prevToken == "\n":
            lineNumber += 1

        if isImportingGlobal:
            if (requiredToken == '"' and token != '"') or (requiredToken == "'" and token != "'") or (requiredToken == "`" and token != "`"):
                globalFilePath = globalFilePath + token
            elif (requiredToken == '"' and token == '"') or (requiredToken == "'" and token == "'") or (requiredToken == "`" and token == "`"):
                isImportingGlobal = False

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

        if prevToken not in tokenDictionary and prevToken != "\n":
            prevPrevToken = prevTokenNotNewline
            prevTokenNotNewline = prevToken

        if prevToken == "fgl" and prevPrevToken == "import":
            importFilePath = token
            concatenatedImportString = token
            isImportingLibrary = True
            continue

        if isImportingLibrary and prevToken == "." and token != "\n":
            importFilePath = os.path.join(importFilePath, token)
            concatenatedImportString = concatenatedImportString + "." + token
            continue

        if isImportingLibrary and concatenatedImportString.endswith(varName):
            packageFile = checkLibraryExists(importFilePath + FGL_SUFFIX, packagePaths)
            functionLine = 1
            isLibraryFunction = True
            break

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
                if token == prefix:
                    tmpTuple = findFunctionFromSpecificLibrary(importFilePath, packagePaths, functionName)
                    packageFile = tmpTuple[0]
                    functionLine = tmpTuple[1]
                    isLibraryFunction = True
            elif token == "\n":
                importFilePath = importFilePath + FGL_SUFFIX
                if concatenatedImportString.endswith(prefix):
                    tmpTuple = findFunctionFromSpecificLibrary(importFilePath, packagePaths, functionName)
                    packageFile = tmpTuple[0]
                    functionLine = tmpTuple[1]
                    isLibraryFunction = True
                    break

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
                writeSingleLineToLog("with alias " + importFilePath)
                librariesList.append((importFilePath, token))
            elif token == "\n" and prevPrevToken != "as":
                importFilePath = importFilePath + FGL_SUFFIX
                writeSingleLineToLog("without alias " + importFilePath)
                librariesList.append((importFilePath, concatenatedImportString))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if token == varName:
            if lineNumber < currentLineNumber and prevTokenNotNewline == "define":
                writeSingleLineToLog("Found Definition " + token) # remove later
                isVarFound = True
                break
            if (prevTokenNotNewline == "function" or prevTokenNotNewline == "report") and prevPrevToken != "end":
                writeSingleLineToLog("Found Function " + token) # remove later
                isFunctionFound = True
                break
            elif prevTokenNotNewline == "constant":
                writeSingleLineToLog("Found Constant" + token) # remove later
                isFunctionFound = True
                break
            elif prevTokenNotNewline == "type":
                writeSingleLineToLog("Found Type " + token) # remove later
                isFunctionFound = True
                break

    if isFunctionFound and not isLibraryFunction:
        packageFile = currentFile
        functionLine = lineNumber

    if isVarFound and not isLibraryFunction:
        packageFile = currentFile
        functionLine = lineNumber

    if not isFunctionFound and not isVarFound and not isLibraryFunction:
        writeSingleLineToLog("here?????????????????????????? " + str(len(librariesList)))
        writeSingleLineToLog(str(librariesList))
        # look in other files
        # Current File > Imported Library > OBJFILES > CUSTLIBS > LIBFILES
        for l in librariesList:
            writeSingleLineToLog(" why is there no suffix here?????? " + l[0])
            # need to loop through each library and check if has string
            # tmpTuple = checkVariableInLibrary(varName, l[0], packagePaths)

            tmpTuple = findFunctionFromSpecificLibrary(l[0], packagePaths, varName)
            if tmpTuple[0] != "":
                packageFile = tmpTuple[0]
                functionLine = tmpTuple[1]
                isFunctionFound = True
                break

    if not isFunctionFound and not isLibraryFunction:
        # need to get Makefile functions
        tmpTuple = findFunctionFromMakefile(currentDirectory, varName)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]

    writeSingleLineToLog("we should have ended with this " + packageFile)

    return packageFile, functionLine

def checkLibraryExists(importFile, packagePaths):
    writeSingleLineToLog("getting functions from here " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        writeSingleLineToLog(packageFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        writeSingleLineToLog("couldn't find file " + importFile)
        return ""

    return packageFile