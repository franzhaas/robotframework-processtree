from robot.api.deco import keyword, library
from typing import Any, Optional
import robot.libraries.BuiltIn as BuiltIn
import uuid
import robot.api.logger as logger
from collections import namedtuple
import multiprocessing as mp
import contextlib
import tempfile
import os
from rf_processtree import _spawner
import pathlib
from json import dumps
from multiprocessing import Queue, JoinableQueue
from importlib.resources import read_text

_LoggingData = namedtuple("_LoggingData", ["key", "dest"])
_QueueBetweenProcessesPayload = namedtuple("_QueueBetweenProcessesPayload", ["link_forward", "link_back", "message"])

def _redirection_process_worker(q: JoinableQueue, odir: str, redirection_file: pathlib.Path):
    redirects = {}
    while True:
        payload = q.get()
        redirects[payload.key] = payload.dest
        handle, name = tempfile.mkstemp(dir=odir)
        with open(handle, "w") as f:
            f.write(read_text("rf_processtree", "redir_template.html").format(redir_hashmap=dumps(redirects)))
        os.replace(name, odir / redirection_file)
        q.task_done()


@library(listener='SELF')
class rf_processtree:
    _start_method: Optional[str] = None
    _link_redirect_queue: Optional[JoinableQueue] = None
    _link_redirect_file_name: str = "redirect.html"
    _write_queue: Optional[Queue] = None
    _read_queue: Optional[Queue] = None

    def __init__(self, target_suite: Optional[str] = None, start_method: Optional[str] = None):
        """Initializes either a parent or a child instance depending on the parameter

        - If no target suite is given -> this is a child
        - If a target suite is given -> this is a parent
        """
        with contextlib.suppress(BuiltIn.RobotNotRunningError):
            match (self._start_method, start_method):
                case (None, None):
                    self.__class__._start_method = "spawn"
                case (None, method):
                    self.__class__._start_method = method
                case (method, None):
                    pass  # self._start_method is already set, no change needed
                case (method1, method2):
                    assert method1 == method2, f"Start method cannot be changed after initialization {self._start_method} != {start_method}"
            assert self._start_method in (set(mp.get_all_start_methods()) ^ {"fork"}), f"Start method {self._start_method} is not available on this system (fork is not suported)"

            self._child_starter = mp.get_context(self._start_method)
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

        Logging is generated which allows to follow a message to its destination.
        
        Limitations of the multiprocessing Queues apply (only picklable objects can be sent)."""
        assert self._link_redirect_queue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._write_queue is not None, "Interprocess communication queue is not online, there is an issue communicating between processes"
        
        payload = _QueueBetweenProcessesPayload(link_forward=str(uuid.uuid4()), link_back=str(uuid.uuid4()), message=message)
        self._link_redirect_queue.put(_LoggingData(key=payload.link_back, dest=f"{self._log_file_path}#{self.id}"))
        self._write_queue.put(payload)
        logger.info(f"""Sending message to <a href="{self._link_redirect_file_name}#{payload.link_forward}">log</a>: {message}""", html=True)
        self._link_redirect_queue.join()

    @keyword
    def receive_message(self, timeout: Optional[float] = None) -> Any:
        """Receive message
        
        Logging is generated which allows to trace the source of a message.

        Limitations of the multiprocessing Queues apply (only picklable objects can be received)."""
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

        There is no way to identify a specific child; all siblings are equals. The 
        only way to communicate with them is via the message queues.

        The children die when the parent dies. This is treated in the logs/reports as a fail, 
        if this is not desired, implement a "we are done, let's go home ⊙" message.
        """
        assert self._target_suite is not None, "This is a child instance, cannot spawn another child process. You can create a parent instance in a child suite though."
        _o_dir = tempfile.TemporaryDirectory(dir=str(self._o_dir), delete=False).name
        self._child_starter.Process(args=(self._target_suite, self._read_queue, self._write_queue, self._link_redirect_queue, self._link_redirect_file_name, _o_dir, self._start_method,),
                                    target=_spawner.start_child, daemon=True, kwargs={"loglevel": self._loglevel, "outputdir": self._o_dir}).start()
        _o_dir = pathlib.Path(_o_dir).relative_to(self._o_dir)
        logger.info(f"""Started child process for suite {self._target_suite}, log file: <a href="{_o_dir}/log.html">log</a>, report file: <a href="{_o_dir}/report.html">report</a>, console file: <a href="{_o_dir}/console.log">console</a>""", html=True)
