from robot.api.deco import keyword, library
from typing import Any
import robot.libraries.BuiltIn as BuiltIn
import uuid
import robot.api.logger as logger
from dataclasses import dataclass


@dataclass
class _queue_bewtween_processes_payload:
    link_forward: str
    link_back: str
    message: Any

@dataclass
class _logging_data:
    key: str
    dest: str

@library(listener='SELF')
class _rf_processtree_base():
    _linkRedirectQueue = None
    _linkRedirectFileName = None
    
    def __init__(self, readQueue, writeQueue):
        self._readQueue = readQueue
        self._writeQueue = writeQueue
        self._logFilePath = BuiltIn.BuiltIn().get_variable_value("${LOG_FILE}")
        self._oDir = BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}")+"/"

    def start_keyword(self, data, result):
        self.id = result.id

    @keyword
    def send_message(self, message: Any) -> None:
        payload = _queue_bewtween_processes_payload(link_forward=str(uuid.uuid4()), link_back=str(uuid.uuid4()), message=message)
        self._linkRedirectQueue.put(_logging_data(key=payload.link_back, dest=f"{self._logFilePath}#{self.id}"))
        self._writeQueue.put(payload)
        logger.info(f"""Sending message to <a href="{self._linkRedirectFileName}#{payload.link_forward}">log</a>: {message}""", html=True)
        self._linkRedirectQueue.join()

    @keyword
    def receive_message(self) -> None:
        payload = self._readQueue.get()
        self._linkRedirectQueue.put(_logging_data(key=payload.link_forward, dest=f"{self._logFilePath}#{self.id}"))
        logger.info(f"""Receiving message from <a href="{self._linkRedirectFileName}#{payload.link_back}">log</a>: {payload.message}""", html=True)
        self._linkRedirectQueue.join()
        return payload.message
