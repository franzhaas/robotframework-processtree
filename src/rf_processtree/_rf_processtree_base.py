from robot.api.deco import keyword, library
from typing import Any
import robot.libraries.BuiltIn as BuiltIn
import uuid
import robot.api.logger as logger
from dataclasses import dataclass


@dataclass
class Data:
    link_forward: str
    link_back: str
    message: Any


@library(listener='SELF')
class _rf_processtree_base():
    _linkRedirectQueue = None
    _linkRedirectFileName = "redirect.html"
    
    def __init__(self, readQueue, writeQueue):
        self._readQueue = readQueue
        self._writeQueue = writeQueue
        self._logFilePath = BuiltIn.BuiltIn().get_variable_value("${LOG_FILE}")
        self._oDir = BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}")+"/"

    def start_keyword(self, data, result):
        self.id = result.id

    @keyword
    def send_message(self, message: Any) -> None:
        uid_linkback = str(uuid.uuid4())
        uid_linkforward = str(uuid.uuid4())
        self._linkRedirectQueue.put((uid_linkback, f"{self._logFilePath}#{self.id}",))
        self._writeQueue.put((uid_linkforward, uid_linkback, message,))
        logger.info(f"""Sending message to <a href="{self._linkRedirectFileName}#{uid_linkforward}">log</a>: {message}""", html=True)
        self._linkRedirectQueue.join()

    @keyword
    def receive_message(self) -> None:
        uid_linkforward, uid_linkback, message = self._readQueue.get()
        self._linkRedirectQueue.put((uid_linkforward, f"{self._logFilePath}#{self.id}",))
        logger.info(f"""Receiving message from <a href="{self._linkRedirectFileName}#{uid_linkback}">log</a>: {message}""", html=True)
        self._linkRedirectQueue.join()
        return message
