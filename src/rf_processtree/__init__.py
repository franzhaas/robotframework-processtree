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
class _QueueBewtweenProcessesPayload:
    link_forward: str
    link_back: str
    message: Any

@dataclass
class _LoggingData:
    key: str
    dest: str

def _redirection_process_worker(q: JoinableQueue, odir: str, redirection_file: pathlib.Path):
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
        os.replace(name, odir / redirection_file)
        q.task_done()


@library(listener='SELF')
class rf_processtree():
    _link_redirect_queue: Optional[JoinableQueue] = None
    _link_redirect_file_name: str = "redirect.html"
    _write_queue: Optional[Queue]  = None
    _read_queue: Optional[Queue] = None

    def __init__(self, target_suite: Optional[str] = None ):
        """Inititalizes either a parent or a child instance depending on the parameter

        - If no target suite is given -> this is a child
        - If a target suite is given -> this is a parent
        """
        with contextlib.suppress(BuiltIn.RobotNotRunningError):
            self._child_starter = mp.get_context("spawn")
            self._target_suite = target_suite
            self._log_file_path = BuiltIn.BuiltIn().get_variable_value("${LOG_FILE}")
            self._o_dir = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}"))
            self._loglevel = BuiltIn.BuiltIn().get_variable_value("${LOG LEVEL}")

            if target_suite is None:
                assert self._write_queue is not None, "Parent did not provide a write queue"
                assert self._read_queue is not None, "Parent did not provide a read queue"
                assert self._link_redirect_queue is not None, "Parent did not provide a link redirect queue"
                self._link_redirect_file_name = "../" + self._link_redirect_file_name
            else:
                self._read_queue = self._child_starter.Queue()
                self._write_queue = self._child_starter.Queue()
                if self._link_redirect_queue is None:
                    self.__class__._link_redirect_queue = self._child_starter.JoinableQueue()
                    self._child_starter.Process(target=_redirection_process_worker, args=(self._link_redirect_queue, self._o_dir, self._link_redirect_file_name), daemon=True).start()
        
    def start_keyword(self, data, result):
        self.id = result.id

    @keyword
    def send_message(self, message: Any) -> None:
        """Send a message to the child process

        Logging is generated which allows to follow a mesage to its destination.
        
        Limitations of the multiprocessing  Queues apply (only picklable objects can be sent)."""
        assert self._link_redirect_queue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._write_queue is not None, "Interprocess communication queue is not online, there is an issue communicating between processes"
        
        payload = _QueueBewtweenProcessesPayload(link_forward=str(uuid.uuid4()), link_back=str(uuid.uuid4()), message=message)
        self._link_redirect_queue.put(_LoggingData(key=payload.link_back, dest=f"{self._log_file_path}#{self.id}"))
        self._write_queue.put(payload)
        logger.info(f"""Sending message to <a href="{self._link_redirect_file_name}#{payload.link_forward}">log</a>: {message}""", html=True)
        self._link_redirect_queue.join()

    @keyword
    def receive_message(self, timeout: Optional[float] = None) -> Any:
        """Receive message
        
        Logging is generated which allows to trace the source of a mesage.

        Limitations of the multiprocessing  Queues apply (only picklable objects can be received)."""
        assert self._link_redirect_queue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._read_queue is not None, "Interprocess communication queue is not online, there is an issue communicating between processes"
        payload = self._read_queue.get(block=True, timeout=timeout)
        self._link_redirect_queue.put(_LoggingData(key=payload.link_forward, dest=f"{self._log_file_path}#{self.id}"))
        logger.info(f"""Receiving message from <a href="{self._link_redirect_file_name}#{payload.link_back}">log</a>: {payload.message}""", html=True)
        self._link_redirect_queue.join()
        return payload.message

    @keyword
    def spawn(self) -> None:
        """
        Spawns a child process which will run the suite provided in the constructor.
        
        It is possible to spawn multiple child processes, in which case all of them 
        are treated as equals.

        There is no way to identify a specific child all siblings are equals. The 
        only way to comunicate with them is via the message queues.

        The childs die when the parent dies. This is treated in the logs/reports as a fail, 
        if this is not desired, implement a "we are done, lets go home ⊙" message.
        """
        assert self._target_suite is not None, "This is a child instance, cannot spawn another child process you can create a parent instance in a child suite though"
        _oDir = tempfile.TemporaryDirectory(dir=str(self._o_dir), delete=False).name
        self._child_starter.Process(args=(self._target_suite, self._read_queue, self._write_queue, self._link_redirect_queue, self._link_redirect_file_name, _oDir,),
                                    target=_spawner.start_child, daemon=True, kwargs={"loglevel":self._loglevel, "outputdir": self._o_dir}).start()
        _oDir = pathlib.Path(_oDir).relative_to(self._o_dir)
        logger.info(f"""Started child process for suite {self._target_suite}, log file: <a href="{_oDir}/log.html">log</a>, report file: <a href="{_oDir}/report.html">report</a>, console file: <a href="{_oDir}/console.log">console</a>""", html=True)
