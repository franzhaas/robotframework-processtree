from robot.api.deco import keyword, library
from typing import Any, Optional
import robot.libraries.BuiltIn as BuiltIn
import uuid
import robot.api.logger as logger
from dataclasses import dataclass
import multiprocessing as mp
import contextlib
import tempfile
import os
from rf_processtree import _spawner
import pathlib
import json
from multiprocessing import Queue, JoinableQueue


@dataclass
class _queue_bewtween_processes_payload:
    link_forward: str
    link_back: str
    message: Any

@dataclass
class _logging_data:
    key: str
    dest: str

def _make_ofile_safely(prefix: pathlib.Path, suffix: str):
    handle, name = tempfile.mkstemp(prefix=str(prefix), suffix=suffix)
    os.close(handle)
    return name

def _redirectionProcessWorker(q: JoinableQueue, odir: str, redirectionFile: pathlib.Path):
    redirects = {}
    while True:
        payload = q.get()
        redirects[payload.key] = payload.dest
        handle, name = tempfile.mkstemp(dir=odir)
        with open(handle, "w") as f:
            f.write(f"""<!DOCTYPE html><html><head><script>
const linkMappings = {json.dumps(redirects)}
window.onload = function () {{
    const hashPart = window.location.hash.substring(1);
    if (linkMappings[hashPart]) {{
        window.location.href = linkMappings[hashPart];
    }} else {{
        document.body.innerHTML = '<h1>Error: broken link. likely this link points to something which has not materialised... Or you have overwritten the redirect file in a subsequent run</h1>';
    }}
}};</script></head></html>""")
        os.replace(name, odir / redirectionFile)
        q.task_done()


@library(listener='SELF')
class rf_processtree():
    _linkRedirectQueue: Optional[JoinableQueue] = None
    _linkRedirectFileName: str = "redirect.html"
    _writeQueue: Optional[Queue]  = None
    _readQueue: Optional[Queue] = None

    def __init__(self, target_suite: Optional[str] = None ):
        """Inititalizes either a parent or a child instance depending on the parameter

        - If no target suite is given -> this is a child
        - If a target suite is given -> this is a parent
        """
        with contextlib.suppress(BuiltIn.RobotNotRunningError):
            self._child_starter = mp.get_context("spawn")
            self._target_suite = target_suite
            self._logFilePath = BuiltIn.BuiltIn().get_variable_value("${LOG_FILE}")
            self._oDir = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}")+"/")
            self._loglevel = BuiltIn.BuiltIn().get_variable_value("${LOG LEVEL}")

            if target_suite is None:
                assert self._writeQueue is not None, "Parent did not provide a write queue"
                assert self._readQueue is not None, "Parent did not provide a read queue"
                assert self._linkRedirectQueue is not None, "Parent did not provide a link redirect queue"
            else:
                self._readQueue = self._child_starter.Queue()
                self._writeQueue = self._child_starter.Queue()
                if self._linkRedirectQueue is None:
                    self.__class__._linkRedirectQueue = self._child_starter.JoinableQueue()
                    self._child_starter.Process(target=_redirectionProcessWorker, args=(self._linkRedirectQueue, self._oDir, self._linkRedirectFileName), daemon=True).start()
        
    def start_keyword(self, data, result):
        self.id = result.id

    @keyword
    def send_message(self, message: Any) -> None:
        """Send a message to the child process

        Logging is generated which allows to follow a mesage to its destination.
        
        Limitations of the multiprocessing  Queues apply (only picklable objects can be sent)."""
        assert self._linkRedirectQueue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._writeQueue is not None, "Interprocess communication queue is not online, there is an issue communicating between processes"
        
        payload = _queue_bewtween_processes_payload(link_forward=str(uuid.uuid4()), link_back=str(uuid.uuid4()), message=message)
        self._linkRedirectQueue.put(_logging_data(key=payload.link_back, dest=f"{self._logFilePath}#{self.id}"))
        self._writeQueue.put(payload)
        logger.info(f"""Sending message to <a href="{self._linkRedirectFileName}#{payload.link_forward}">log</a>: {message}""", html=True)
        self._linkRedirectQueue.join()

    @keyword
    def receive_message(self, timeout: Optional[float] = None) -> Any:
        """Receive message
        
        Logging is generated which allows to trace the source of a mesage.

        Limitations of the multiprocessing  Queues apply (only picklable objects can be received)."""
        assert self._linkRedirectQueue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._readQueue is not None, "Interprocess communication queue is not online, there is an issue communicating between processes"
        payload = self._readQueue.get(block=True, timeout=timeout)
        self._linkRedirectQueue.put(_logging_data(key=payload.link_forward, dest=f"{self._logFilePath}#{self.id}"))
        logger.info(f"""Receiving message from <a href="{self._linkRedirectFileName}#{payload.link_back}">log</a>: {payload.message}""", html=True)
        self._linkRedirectQueue.join()
        return payload.message

    @keyword
    def spawn(self) -> None:
        """
        Spawns a child process which will run the suite provided in the constructor.
        
        It is possible to spawn multiple child processes, in which case all of them 
        are treated as equals.

        There is no way to identify a specific child all siblings are equals. The 
        only way to comunicate is via the message queues.
        """
        assert self._target_suite is not None, "This is a child instance, cannot spawn another child process you can create a parent instance in a child suite though"
        logfile = _make_ofile_safely(prefix=self._oDir / "log_", suffix=".html")
        reportfile = _make_ofile_safely(prefix=self._oDir / "report_", suffix=".html")
        consoleFile = _make_ofile_safely(prefix=self._oDir / "console_", suffix=".txt")
        outXml =  _make_ofile_safely(prefix=self._oDir / "output_", suffix=".xml")

        self._child_starter.Process(target=_spawner._start_child,
                                    args=(self._target_suite, self._readQueue, self._writeQueue, self._linkRedirectQueue,
                                            self._linkRedirectFileName, logfile, reportfile, consoleFile, outXml, self._loglevel),
                                    daemon=True).start()
        logger.info(f"""Started child process for suite {self._target_suite}, log file: <a href="{logfile}">log</a>, report file: <a href="{reportfile}">report</a>, console file: <a href="{consoleFile}">console</a>""", html=True)
