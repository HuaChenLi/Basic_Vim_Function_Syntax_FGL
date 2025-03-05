import os
from datetime import datetime
from os.path import expanduser

from lib.constants import TAGS_FILE_DIRECTORY

LOG_DIRECTORY = os.path.join(TAGS_FILE_DIRECTORY, "fgl_syntax_log")


def writeSingleLineToLog(inputString):
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    fileToday = datetime.today().strftime('%Y-%m-%d')
    logFile = os.path.join(LOG_DIRECTORY, fileToday + ".log")

    file = open(logFile, "a")
    currentTime = datetime.today().strftime('%Y-%m-%d-%H:%M:%S.%f')
    outputString = currentTime + ": " + inputString + "\n"
    file.write(outputString)