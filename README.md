# rf-processtree
This is an attempt to deal with concurrency in Robot Framework without needing the cooperation of the keyword library.

There is another approach out there: [AIO](https://github.com/test-fullautomation/RobotFramework_AIO) which attempts to achieve the same thing with threads.

## Comparison

### Speed and Features
| Property               | rf-processtree                      | AIO            |
| -------------          | -------------                       | -------------  |
| GIL                    | not affected                        | affected       |
| startup overhead       | process                             | thread         |
| communication overhead | serialization/IPC                   | within process |
| logging                | per process, linked with hyperlinks | debug.log      |
| locks                  | not supported (by choicd)           | supported      |
| deadlocks              | no                                  | possible       |
| live locks             | no                                  | possible       |

## Outlook
### Purpose

It is disputable whether or not threading in Robot Framework is even desirable. There are many well-tested and established methods to achieve concurrency within the keyword libraries, which will break if we have multiple threads in one Robot Framework instance, even sequential Robot Framework may fail.

For example:
```robot
*** Keywords ***
set current chancellor given name: '${CHANCELLOR_GIVEN_NAME}' surname: '${CHANCELLOR_SURNAME}'
      Set global variable       ${CHANCELLOR_GIVEN_NAME}
      Set global variable       ${CHANCELLOR_SURNAME}
      Play Musik                Großer Zapfenstreich.mp3
      Log to console            Germany's chancellor is: ${CHANCELLOR_SURNAME} ${CHANCELLOR_SURNAME}
*** Tasks ***
run chancellor timeline
      Run in Thread1          set current chancellor given name: 'Gerhard' surname: 'Schröder'
      Run in Thread2          set current chancellor given name: 'Angela' surname: 'Merkel'
      Run in Thread3          set current chancellor given name: 'Olaf' surname: 'Scholz'
```
This code is supposed to print:
```
Germany's chancellor is: Gerhard Schröder
Germany's chancellor is: Angela Merkel
Germany's chancellor is: Olaf Scholz
```
and in a pre-threaded environment, this would be correct and fine.

However, in the threaded world (with thread switch on IO, FIFO scheduling), it becomes:
```
Germany's chancellor is: Olaf Scholz
Germany's chancellor is: Olaf Scholz
Germany's chancellor is: Olaf Scholz
```
This problem does not apply to subprocesses and subinterpreters, and also not if there is one Robot Framework instance per thread (however, this would come with its own problems).

### processtree
The processtree lacks a solution for the debug files to be visualized in a merged way. Syntax support to mark suites to be only running in child threads, rebot support with infrastructure like Jenkins plugin, etc. Integrated infrastructure in Robot Framework for the forward/backward links.

Long-term it would be a goal to achieve inside Robot Framework core:
 - support for backwards and forwards linking in the logs, across runs
 - ability to use rebot with these forward/backward linking
 - syntax to mark suites to not be run unless inside a child
 - maybe even a interface specification which can be implemented by various solutions.

Long-term it would be a goal to achieve outside the Robot Framework core:
 - ability to choose different start methods (spawn/forkserver) (easy)
 - ability to use subinterpreters (upstream is necessary)
   - solving the signaling problem "which subinterpreter timed out?"
   - subinterpreters need to become stable and mainline
 - ability to use threads -> by making Robot Framework globals thread-local (direct competition to AIO approach)
   - solving the signaling problem "which thread times out?"

Queue+process-based concurrency is used successfully by stable systems (Erlang, Elixir). Unfortunately, they are unpopular due to the need to separate the state, and explicit
data exchange.

### AIO
The AIO solution currently has open issues with concurrency safety,
[tkinter and threads](https://github.com/test-fullautomation/robotframework/issues/110),
[deadlock](https://github.com/test-fullautomation/robotframework/issues/117), and 
[Timeout handling](https://github.com/test-fullautomation/robotframework/issues/118). I am constructive and try to help fix these issues [fix](https://github.com/robotframework/robotframework/pull/5343) which fixes the tkinter problem of AIO with threads on Windows.

However, in my point of view, the deadlock issue is not solveable, at best manageable, and I lack experience on the signaling issue.

### Improve Guidance and Examples and Infrastructure for the Current Situation

The documentation on how to use async could be extended to show examples.

For example, concurrently listen to more than one socket at a time:
```python
import select
import robot.libraries.BuiltIn as BuiltIn
from robot.api import logger


class parallel_wait:
    def __init__(self, timeout=5.0):
        self._sockets = {}
        self._timeout = timeout

    def add_callback_for_socket(self, socket, callback):
        self._sockets[socket] = callback

    def wait_for_data_on_all_configured_sockets(self):
        while recvable := self._get_readables():
            for item in recvable:
                BuiltIn.BuiltIn().run_keyword(self._sockets[item], item)

    def _get_readables(self):
        (recvable, _, __,) = select.select(self.keys(), [], [], self._timeout)
        return (item for item in recvable if s.recv(1, socket.MSG_PEEK))
```
Every time one of the filehandles/sockets becomes readable, the corresponding keyword gets called.

This concept can be extended to file handles on some systems (Linux), with relative ease.

Infrastructure to make Python keywords run in parallel, while still being connected to the Robot Framework
infrastructure (`run_keyword`), where Robot Framework continues to run in a single thread. (no example).
