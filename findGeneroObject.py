import os
import time
import sys
import re

sys.path.append(os.path.abspath(""))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'syntax')))

import lib.libLogging as libLogging
import lib.tokenize as tokenize

from lib.constants import tokenDictionary
from lib.constants import GENERO_KEY_WORDS
from lib.constants import FGL_SUFFIX
from lib.constants import FGL_DIRECTORY_SUFFIX


def findFunctionFromSpecificLibrary(importFile, packagePaths, functionName):
    libLogging.writeSingleLineToLog("getting functions from here " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        libLogging.writeSingleLineToLog(packageFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        libLogging.writeSingleLineToLog("couldn't find file " + importFile)
        return "", 0

    file = open(packageFile, "r")
    fileContent = file.read()

    if not re.search(functionName, fileContent):
        libLogging.writeSingleLineToLog("no function name in here")
        return "", 0

    startTime = time.time()
    tokenList = tokenize.tokenizeString(fileContent)
    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("tokenizing " + importFile + " took " + str(length) + " seconds and the number of tokens is " + str(len(tokenList)))

    requiredToken = None
    prevPrevToken = ""
    prevTokenNotNewline = ""
    prevToken = ""
    tmpToken = "\n"
    lineNumber = 0
    functionLine = 0

    isFunctionFound = False

    variableList = set()
    isDefiningVariable = False

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

        if not isDefiningVariable and prevTokenNotNewline == "constant":
            variableList.add(token)
            isDefiningVariable = True

        if token == functionName:
            if isDefiningVariable and (prevTokenNotNewline == "constant" or prevTokenNotNewline == ","):
                libLogging.writeSingleLineToLog("found public constant " + token) # remove later
                functionLine = lineNumber
                isFunctionFound = True
                break

            if ((prevTokenNotNewline == "function") or (prevTokenNotNewline == "report")) and not prevPrevToken == "end" and not prevPrevToken == "private":
                libLogging.writeSingleLineToLog("found public function " + token)
                functionLine = lineNumber
                isFunctionFound = True
                break

            if prevTokenNotNewline == "type" and not prevPrevToken == "private":
                libLogging.writeSingleLineToLog("found public type " + token)
                functionLine = lineNumber
                isFunctionFound = True
                break

        # this is awful
        if isDefiningVariable and token != "\n" and token != "=" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and token not in variableList and token not in GENERO_KEY_WORDS and token not in tokenDictionary:
            isDefiningVariable = False
            variableList = set()

    endTime = time.time()
    length = endTime - startTime
    libLogging.writeSingleLineToLog("if statements took " + str(length) + " seconds")

    if isFunctionFound:
        return packageFile, functionLine
    else:
        return "", 0

def findFunctionFromMakefile(currentDirectory, varName):
    makeFile = os.path.join(currentDirectory, "Makefile")
    if not os.path.isfile(makeFile):
        return "", 0
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

    libLogging.writeSingleLineToLog("looking at OBJFILES")
    for obj in objFileList:
        tmpTuple = findFunctionFromSpecificLibrary(obj[0], [currentDirectory], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    libLogging.writeSingleLineToLog("looking at CUSTLIBS")
    for custLib in custLibFileList:
        tmpTuple = findFunctionFromSpecificLibrary(custLib[0], packagePaths, varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    libLogging.writeSingleLineToLog("looking at LIBFILES")
    for libFile in libFileList:
        libLogging.writeSingleLineToLog(libFile)
        tmpTuple = findFunctionFromSpecificLibrary(libFile, [libFilePath], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    libLogging.writeSingleLineToLog("looking at GLOBALS")
    for globalFile in globalFileList:
        tmpTuple = findFunctionFromSpecificLibrary(globalFile[0], [currentDirectory], varName)
        if tmpTuple[0] != "":
            packageFile = tmpTuple[0]
            functionLine = tmpTuple[1]
            return packageFile, functionLine

    return packageFile, functionLine

def findFunctionAndMethods(varName, tokenList, currentFile, packagePaths, currentLineNumber):
    numParts = len(varName.split("."))

    isDefiningVariable = False
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

    if numParts > 1:
        prefix = varName.rsplit(".", 1)[0]
        functionName = varName.rsplit(".", 1)[1]
    else:
        prefix = varName
        functionName = varName

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
            packageFile = getPackageFile(importFilePath + FGL_SUFFIX, packagePaths)
            functionLine = 1
            isLibraryFunction = True
            break

        if isImportingLibrary:
            if prevToken == "as":
                importFilePath = importFilePath + FGL_SUFFIX
                if prefix == token:
                    libLogging.writeSingleLineToLog("with alias " + importFilePath)
                    if numParts == 1:
                        packageFile = getPackageFile(importFilePath, packagePaths)
                        functionLine = 1
                    elif numParts > 1:
                        tmpTuple = findFunctionFromSpecificLibrary(importFilePath, packagePaths, functionName)
                        packageFile = tmpTuple[0]
                        functionLine = tmpTuple[1]
                    isLibraryFunction = True
                    break
                librariesList.append((importFilePath, token))
            elif token == "\n" and prevPrevToken != "as":
                importFilePath = importFilePath + FGL_SUFFIX
                if concatenatedImportString.endswith(prefix):
                    libLogging.writeSingleLineToLog("without alias " + importFilePath + " " + concatenatedImportString)
                    tmpTuple = findFunctionFromSpecificLibrary(importFilePath, packagePaths, functionName)
                    packageFile = tmpTuple[0]
                    functionLine = tmpTuple[1]
                    isLibraryFunction = True
                    break
                librariesList.append((importFilePath, concatenatedImportString))

            if token == "\n":
                isImportingLibrary = False
                importFilePath = ""
                concatenatedImportString = ""

        if not isDefiningVariable and prevTokenNotNewline == "define":
            variableList.add(token)
            isDefiningVariable = True

        if not isDefiningVariable and prevTokenNotNewline == "constant":
            variableList.add(token)
            isDefiningVariable = True

        if token == varName:
            if lineNumber < currentLineNumber and isDefiningVariable and (prevTokenNotNewline == "define" or prevTokenNotNewline == ","):
                libLogging.writeSingleLineToLog("Found Definition " + token) # remove later
                isVarFound = True
                packageFile = currentFile
                functionLine = lineNumber
                continue
            if (prevTokenNotNewline == "function" or prevTokenNotNewline == "report") and prevPrevToken != "end":
                libLogging.writeSingleLineToLog("Found Function " + token) # remove later
                isFunctionFound = True
                break
            elif isDefiningVariable and (prevTokenNotNewline == "constant" or prevTokenNotNewline == ","):
                libLogging.writeSingleLineToLog("Found Constant " + token) # remove later
                isFunctionFound = True
                break
            elif prevTokenNotNewline == "type":
                libLogging.writeSingleLineToLog("Found Type " + token) # remove later
                isFunctionFound = True
                break

        if isDefiningVariable and token != "\n" and prevToken != "\n" and token != "," and prevTokenNotNewline != "," and token not in variableList and token not in GENERO_KEY_WORDS:
            isDefiningVariable = False
            variableList = set()

    if isFunctionFound and not isLibraryFunction:
        packageFile = currentFile
        functionLine = lineNumber

    if isVarFound and not isLibraryFunction:
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

    if not isFunctionFound and not isLibraryFunction:
        tmpTuple = findFunctionFromMakefile(currentDirectory, varName)
        packageFile = tmpTuple[0]
        functionLine = tmpTuple[1]

    return packageFile, functionLine

def getPackageFile(importFile, packagePaths):    
    libLogging.writeSingleLineToLog("getting functions from here " + importFile)
    isExistingPackageFile = False

    for package in packagePaths:
        packageFile = os.path.join(package, importFile)
        libLogging.writeSingleLineToLog(packageFile)
        if os.path.isfile(packageFile):
            isExistingPackageFile = True
            break

    if not isExistingPackageFile:
        libLogging.writeSingleLineToLog("couldn't find file " + importFile)
        return ""

    return packageFile

def findGeneroObject(varName, buffer, currentFile, currentLineNumber):
    startTime = time.time()
    libLogging.writeSingleLineToLog("=========================================================")
    libLogging.writeSingleLineToLog("looking for object " + varName)
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

    tmpTuple = findFunctionAndMethods(varName, tokenList, currentFile, packagePaths, currentLineNumber)
    packageFile = tmpTuple[0]
    functionLine = tmpTuple[1]

    endTime = time.time()
    lengthTime = endTime - startTime
    libLogging.writeSingleLineToLog("looking for definition took " + str(lengthTime))

    return packageFile, functionLine

