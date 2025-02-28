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
import time
import base64
import enum

_message_types = enum.Enum("_message_types", ["payload", "close"])

_LoggingData = namedtuple("_LoggingData", ["key", "dest"])
_QueueBetweenProcessesPayload = namedtuple("_QueueBetweenProcessesPayload", ["type", "link_forward", "link_back", "message"])


def _short_uuid():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf-8").rstrip("=")


class _QueueClosed(Exception):
    pass


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


@library(listener="SELF")
class rf_processtree:
    """This library allows spawning child processes which run robot suites. I am personally
    a bit unsure whether or not it is a good thing to have multiple Robot Framework execution
    lines running simultaneously, but it is possible, and trying it out is likely to be a
    good approach to learn about it.

    == Table of contents ==

    %TOC%

    == Concept ==

    Communication between the parent and the children is done via message queues, no
    communication between children is possible (hence the name, tree).

    The children currently run in a new process space, the start methods are limited to
    forkserver and spawn. The default is spawn, which is supported on all platforms
    and thread-safe in all situations. Forkserver is safe if Python was not embedded
    in a threaded application (if you use the "robot" command or start Robot Framework
    from a regular Python process, forkserver is safe for you). The start method
    "fork" is not supported, as it is not thread-safe.

    == Future outlook ==

    Long term it would be interesting to support subinterpreters, as well as threads in
    addition to the forkserver/spawn solutions.

    == Alternatives ==
    There is an effort at (Bosch)[https://github.com/test-fullautomation/robotframework]
    to modify Robot Framework core to add threads to the Robot Framework language. This
    would also allow running multiple Robot Framework sequences simultaneously. It allows
    defining threads inline (as opposed to this one which needs them to be defined as
    suites), making it less effort to define a thread, which is great but has the
    downside of less clear separation and shared state. Logging inside the log.html is
    currently limited to the existence of the thread, as opposed to having all steps logged.
    """

    _start_method: Optional[str] = None
    _link_redirect_queue: Optional[JoinableQueue] = None
    _link_redirect_file_name: pathlib.Path = pathlib.Path("redirect.html")
    _write_queue: Optional[Queue] = None
    _read_queue: Optional[Queue] = None

    def __init__(self, target_suite: Optional[str] = None, start_method: Optional[str] = None):
        """Initializes either a parent or a child instance depending on the parameter

        - If no target suite is given -> this is a child
        - If a target suite is given -> this is a parent

        If this is a child, but was not equipped by the parent with the necessary queues,
        this will fail.

        The default start method is spawn, which is safe in all situations. Currently, you need
        to choose one start method and stick to it. This is because the redirect process can
        only be started with one method. Using multiple redirect processes and files is possible,
        but is not yet implemented. (PRs are welcome!)
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
            assert self._start_method in (set(mp.get_all_start_methods()) ^ {"fork"}), (
                f"Start method {self._start_method} is not available on this system (fork is not supported)"
            )

            self._child_starter = mp.get_context(self._start_method)
            self._target_suite = target_suite
            self._o_dir = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}"))
            self._log_file_path = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${LOG_FILE}")).relative_to(self._o_dir)
            self._loglevel = BuiltIn.BuiltIn().get_variable_value("${LOG LEVEL}")
            self._processes = []

            if target_suite is None:
                assert self._write_queue is not None, "Parent did not provide a write queue"
                assert self._read_queue is not None, "Parent did not provide a read queue"
                assert self._link_redirect_queue is not None, "Parent did not provide a link redirect queue"
                self._link_redirect_file_name = "../" / self._link_redirect_file_name
            else:
                self._read_queue = self._child_starter.Queue()
                self._write_queue = self._child_starter.Queue()
                if self._link_redirect_queue is None:
                    self.__class__._link_redirect_queue = self._child_starter.JoinableQueue()
                    self._child_starter.Process(
                        target=_redirection_process_worker,
                        args=(
                            self._link_redirect_queue,
                            self._o_dir,
                            self._link_redirect_file_name,
                        ),
                        daemon=True,
                    ).start()

    def start_keyword(self, data, result):
        self.id = result.id

    @keyword
    def send_message(self, message: Any) -> None:
        """Send a message to the child process

        Logging is generated which allows following a message to its destination.
        
        Limitations of the multiprocessing Queues apply (only picklable objects can be sent).
        """
        assert self._link_redirect_queue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._write_queue is not None, (
            "Interprocess communication queue is not online, there is an issue communicating between processes, queue closed?"
        )

        payload = _QueueBetweenProcessesPayload(
            type=_message_types.payload,
            link_forward=_short_uuid(),
            link_back=_short_uuid(),
            message=message,
        )
        self._link_redirect_queue.put(_LoggingData(key=payload.link_back, dest=f"{self._log_file_path}#{self.id}"))
        self._write_queue.put(payload)
        logger.info(
            f"""Sending message to <a href="{self._link_redirect_file_name}#{payload.link_forward}">log</a>: {message}""",
            html=True,
        )
        self._link_redirect_queue.join()

    @keyword
    def receive_message(self, timeout: Optional[float] = None) -> Any:
        """Receive message
        
        Logging is generated which allows tracing the source of a message.

        Limitations of the multiprocessing Queues apply (only picklable objects can be received).
        """

        try:
            return self._receive_message(timeout)
        except _QueueClosed as _:
            assert False, "Queue is closed, no more messages can be received"

    def _receive_message(self, timeout: Optional[float] = None) -> Any:
        assert self._link_redirect_queue is not None, "Redirect system is not online, there is an issue with the linking of messages"
        assert self._read_queue is not None, (
            "Interprocess communication queue is not online, there is an issue communicating between processes, queue closed?"
        )
        payload = self._read_queue.get(block=True, timeout=timeout)
        match payload.type:
            case _message_types.payload:
                self._link_redirect_queue.put(
                    _LoggingData(
                        key=payload.link_forward,
                        dest=f"{self._log_file_path}#{self.id}",
                    )
                )
                logger.info(
                    f"""Receiving message from <a href="{self._link_redirect_file_name}#{payload.link_back}">log</a>: {payload.message}""",
                    html=True,
                )
                self._link_redirect_queue.join()
                return payload.message
            case _message_types.close:
                self._read_queue = None
                raise _QueueClosed()
            case _:
                assert False, "Unknown message type"

    @keyword
    def spawn(self, **robotframework_variables) -> None:
        """
        Spawns a child process which will run the suite provided in the constructor.
        
        It is possible to spawn multiple child processes, in which case all of them 
        are treated as equals.

        There is no way to identify a specific child; all siblings are equals. The 
        only way to communicate with them is via the message queues.

        The children die when the parent dies. This is treated in the logs/reports as a fail, 
        if this is not desired, implement a "we are done, let's go home ⊙" message.
        """
        assert self._target_suite is not None, (
            "This is a child instance, cannot spawn another child process. You can create a parent instance in a child suite though."
        )
        _o_dir = tempfile.TemporaryDirectory(dir=self._o_dir, prefix="rf_tree_node_", delete=False).name
        p = self._child_starter.Process(
            args=(
                self._target_suite,
                self._read_queue,
                self._write_queue,
                self._link_redirect_queue,
                self._link_redirect_file_name,
                _o_dir,
                self._start_method,
            ),
            target=_spawner.start_child,
            daemon=True,
            kwargs={
                "loglevel": self._loglevel,
                "outputdir": self._o_dir,
                "variable": [f"{name}:{value}" for name, value in robotframework_variables.items()],
            },
        )
        p.start()
        self._processes.append(p)
        _o_dir = pathlib.Path(_o_dir).relative_to(self._o_dir)
        logger.info(
            f"""Started child process for suite {self._target_suite}, log file: <a href="./{_o_dir}/log.html">log</a>, report file: <a href="{_o_dir}/report.html">report</a>, console file: <a href="{_o_dir}/console.log">console</a>""",
            html=True,
        )

    @keyword
    def wait_for_processes(self, timeout: float = 1.0):
        """Wait for all child processes to finish

        This is a blocking call, it will wait for all child processes to finish
        or until the timeout is reached.

        If the timeout is reached, this keyword will fail.
        """
        endtime = time.time() + timeout
        for item in self._processes:
            item.join(max(0, endtime - time.time()))
            assert not item.is_alive(), f"Child process {item} did not finish in time"

    @keyword
    def run_keyword_on_received_items_until_queue_is_closed(self, keyword: str):
        """Read all items from the queue and run the keyword with the item as argument.

        This is a blocking call, it will read items until the queue is closed.
        """
        while True:
            try:
                item = self._receive_message(timeout=0.01)
            except _QueueClosed as _:
                return
            BuiltIn.BuiltIn().run_keyword(keyword, item)

    @keyword
    def close_connection(self):
        """Close the queue, no more items can be sent.

        receiving is unaffected. This can only be done by a parent,
        as the children dont know if and how many siblings they have.

        This is the "I did what needed to be done, and i went home ⊙" signal.
        """
        assert self._write_queue is not None, (
            "Interprocess communication queue is not online, there is an issue communicating between processes, queue closed?"
        )
        assert self._target_suite is not None, "This is a child instance, cannot close the connection. (wrong instance?)"

        for _ in self._processes:
            self._write_queue.put("close")
        self._write_queue__ = self._write_queue  # to avoid garbage collection
        self._write_queue = None
