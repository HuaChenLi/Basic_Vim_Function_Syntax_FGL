import re
import os

TAGS_FILE = ".temp_tags"
FGL_SUFFIX = ".4gl"

def generateTags(inputString, currentFile):
	tokenList = tokenizeLinesOfFiles(inputString)

	# This is the part where we want to loop through and find the function definitions
	# We need to first set a couple of flags when we're ignoring sections
	isNewLineNeeded = False
	isClosedCurlyBracketNeeded = False

	isSingleQuoteNeeded = False
	isDoubleQuotesNeeded = False
	isBackQuoteNeeded = False # back tick / backtick

	tagsLinesList = []

	isImportingLibrary = False

	currentDirectory = os.path.dirname(currentFile)
	importFilePath = currentDirectory

	prevPrevToken = ""
	prevToken = ""
	token = "\n"

	for tokenBlock in tokenList:
		prevPrevToken = prevToken
		prevToken = token
		token = tokenBlock[0]
		lineNumber = tokenBlock[1]

		# occasionally there are blank tokens
		if token == "":
			continue

		# Skip booleans
		if isNewLineNeeded and token != "\n":
			continue
		elif isNewLineNeeded and token == "\n":
			isNewLineNeeded = False
			continue

		# with the quotes, need to also account for escape character "\"
		if isSingleQuoteNeeded and (token != "'" or prevToken == "\\"):
			continue
		elif isSingleQuoteNeeded and token == "'":
			isSingleQuoteNeeded = False
			continue

		if isDoubleQuotesNeeded and (token != '"' or prevToken == "\\"):
			continue
		elif isDoubleQuotesNeeded and token == '"':
			isDoubleQuotesNeeded = False
			continue

		if isBackQuoteNeeded and token != "`":
			continue
		elif isBackQuoteNeeded and token == "`": 			# I believe the back quote can't be escaped in Genero
			isBackQuoteNeeded = False
			continue

		# Comments
		if token == "#" or (token == "-" and prevToken == "-"):
			isNewLineNeeded = True
			continue

		if token == "{":
			isClosedCurlyBracketNeeded = True
			continue

		if isClosedCurlyBracketNeeded and token != "}":
			continue
		elif isClosedCurlyBracketNeeded and token == "}":
			isClosedCurlyBracketNeeded = False
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

		isPrevPrevTokenEnd = re.match("^end$", prevPrevToken, flags=re.IGNORECASE)
		isPreviousTokenFunctionOrReport = (re.match("^function$", prevToken, flags=re.IGNORECASE) or re.match("^report$", prevToken, flags=re.IGNORECASE))

		if isPreviousTokenFunctionOrReport and not isPrevPrevTokenEnd:
			# We create the list of the function tags
			tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=currentFile, fileAlias=currentFile, currentDirectory=currentDirectory))

		if re.match("^import$", token, flags=re.IGNORECASE) and prevToken == "\n":
			# we need to check that Import is at the start of the line
			isImportingLibrary = True
			continue

		isPreviousTokenAs = re.match("^as$", prevToken, flags=re.IGNORECASE)

		if isImportingLibrary and token != "." and token != "\n" and not re.match("^as$", token, flags=re.IGNORECASE) and not isPreviousTokenAs:
			importFilePath = os.path.join(importFilePath, token)
			continue

		# When it's imported AS something else, we need to create the tags file, but the mapping line is just a bit different
		# The functionName is the AS file, while the file is the path to the file

		if isImportingLibrary and token == "\n" and not isPreviousTokenAs:
			isImportingLibrary = False
			importFilePath = importFilePath + FGL_SUFFIX
			tagsLinesList.extend(getPublicFunctionsFromLibrary(importFilePath, importFilePath, currentDirectory))
			importFilePath = currentDirectory
			continue
		elif isImportingLibrary and isPreviousTokenAs:
			isImportingLibrary = False
			tagsLinesList.extend(getPublicFunctionsFromLibrary(importFilePath, token, currentDirectory))
			importFilePath = currentDirectory


		if isImportingLibrary and re.match("^as$", token, flags=re.IGNORECASE):
			importFilePath = importFilePath + FGL_SUFFIX
			continue


	writeTagsFile(tagsLinesList)

def createListOfTags(functionName, lineNumber, currentFile, fileAlias, currentDirectory):
	# this is interesting, I would need to, for each separation, create a tagLine
	tagsLinesList = []
	functionCallRoot = currentFile.replace(currentDirectory + "\\", "")
	functionCallRoot = functionCallRoot.replace(FGL_SUFFIX, "")
	functionTokens = functionCallRoot.split("\\")

	tagLine = functionName + "\t" + currentFile + "\t" + str(lineNumber) + "\n"
	tagsLinesList.append(tagLine)

	functionNameString = functionName
	for token in reversed(functionTokens):
		functionNameString = token + "." + functionNameString
		tagLine = functionNameString + "\t" + currentFile + "\t" + str(lineNumber) + "\n"
		tagsLinesList.append(tagLine)

	if fileAlias != currentFile:
		aliasFunctionName = fileAlias + "." + functionName
		tagLine = aliasFunctionName + "\t" + currentFile + "\t" + str(lineNumber) + "\n"
		tagsLinesList.append(tagLine)

	return tagsLinesList


def writeTagsFile(tagsLinesList):
	# The tags file needs to be sorted alphabetically (by ASCII code) in order to work
	tagsLinesList.sort()
	file = open(TAGS_FILE, "a")
	for line in tagsLinesList:
		file.write(line)
	file.close()


def getPublicFunctionsFromLibrary(importFilePath, fileAlias, workingDirectory):
	file = open(importFilePath, "r")

	tokenList = tokenizeLinesOfFiles(file)

	# This is copy and pasted from function printTokens() but with a few changes

	# This is the part where we want to loop through and find the function definitions
	# We need to first set a couple of flags when we're ignoring sections
	isNewLineNeeded = False
	isClosedCurlyBracketNeeded = False

	isSingleQuoteNeeded = False
	isDoubleQuotesNeeded = False
	isBackQuoteNeeded = False # back tick / backtick

	isPreviousTokenFunction = False
	isPreviousTokenEnd = False
	isPreviousTokenPrivate = False

	tagsLinesList = []

	previousToken = ""
	token = ""

	for tokenBlock in tokenList:
			previousToken = token
			token = tokenBlock[0]
			lineNumber = tokenBlock[1]

			# occasionally there are blank tokens
			if token == "":
				continue

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
			elif isBackQuoteNeeded and token == "`": 			# I believe the back quote can't be escaped in Genero
				isBackQuoteNeeded = False
				continue

			# Comments
			if token == "#" or (token == "-" and previousToken == "-"):
				isNewLineNeeded = True
				continue

			if token == "{":
				isClosedCurlyBracketNeeded = True
				continue

			if isClosedCurlyBracketNeeded and token != "}":
				continue
			elif isClosedCurlyBracketNeeded and token == "}":
				isClosedCurlyBracketNeeded = False
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


			isPreviousTokenEnd = re.match("^end$", previousToken, flags=re.IGNORECASE)
			isPreviousTokenFunctionOrReport = (re.match("^function$", previousToken, flags=re.IGNORECASE) or re.match("^report$", previousToken, flags=re.IGNORECASE))


			if re.match("^private$", token, flags=re.IGNORECASE):
				isPreviousTokenPrivate = True
				continue

			if (re.match("^function$", token, flags=re.IGNORECASE) or re.match("^report$", token, flags=re.IGNORECASE)) and not isPreviousTokenEnd and not isPreviousTokenPrivate:
				isPreviousTokenFunction = True
				isPreviousTokenPrivate = False
				continue
			elif (re.match("^function$", token, flags=re.IGNORECASE) or re.match("^report$", token, flags=re.IGNORECASE)) and isPreviousTokenEnd:
				isPreviousTokenPrivate = False

			if re.match("^end$", token, flags=re.IGNORECASE):
				isPreviousTokenPrivate = False
				continue

			if isPreviousTokenFunction and not isPreviousTokenEnd:
				isPreviousTokenFunction = False
				# We create the list of the function tags
				tagsLinesList.extend(createListOfTags(functionName=token, lineNumber=lineNumber, currentFile=importFilePath, fileAlias=fileAlias, currentDirectory=workingDirectory))

	return tagsLinesList


def tokenizeString(inputString):
	# basically, the massive line of regex code repeats, so we will grab all printable characters (since all printable characters are between ! to ~ except white spaces)
	# the repeating section contains all the special characters in Genero
	# probably can create a regex that is smart enough to do the whole thing by itself, but can probably just handle it in the python code afterwards
	tokenBlock = re.findall(r"(?:(?!\.|,|'|`|\"\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|\n)[!-~])+|\.|,|'|`|\"\||\(|\)|#|{|}|\[|\]|<|>|-|!|$|\\|\n", inputString)
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
		previousToken = token
		token = tokenBlock[0]
		lineNumber = tokenBlock[1]

		# occasionally there are blank tokens
		if token == "":
			continue

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
		elif isBackQuoteNeeded and token == "`": 			# I believe the back quote can't be escaped in Genero
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
