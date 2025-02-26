# rf-processtree
This is an attempt to deal with concurrency in robotframework without needing the
cooperation of the keyword library.

There is another aproach out there.: [AIO](https://github.com/test-fullautomation/RobotFramework_AIO) which attempts to achive the same thing with threads.

## comparison

### speed and features
| Property               | rf-processtree                      | AIO            |
| -------------          | -------------                       | -------------  |
| GIL                    | not affected                        | affected       |
| startup overhead       | process                             | thread         |
| communication overhead | serialisation/IPC                   | within process |
| logging                | per process, linked with hyperlinks | debug.log      |
| locks                  | not suported                        | suported       |
| deadlocks              | no                                  | possible       |
| live locks             | no                                  | possible       |

## outlook
### Purpose

It is disputable weather or not concurrency in robotframework is even desireable. There are many well tested and
established methods to achieve concurrency within the keyword libraries, which will break if we have multiple threads in one robotframework instance.

For example.:
```robot
*** keywords ***
set current chancelor given name: '${CHANCELOR_GIVEN_NAME}' sirname: '${CHANCELOR_SURNAME}'
      Set global variable       ${CHANCELOR_GIVEN_NAME}
      Set global variable       ${CHANCELOR_SURNAME}
      Play Musik                Grosser Zapfenstreich.mp3                       
      Log to console            Germanies chancelor is: ${CHANCELOR_SURNAME} ${CHANCELOR_SURNAME}
*** tasks ***
run chancelor timeline
      Run in Thread1          set current chancelor given name: 'Gerhard' sirname: 'Schröder'
      Run in Thread2          set current chancelor given name: 'Angela' sirname: 'Merkel'
      Run in Thread3          set current chancelor given name: 'Olaf' sirname: 'Scholz'
      
```
This code is suposed to print.:
```
Germanies chancelor is: Gerhard Schröder
Germanies chancelor is: Angela Merkel
Germanies chancelor is: Olaf Scholz
```
and in a pre threaded environment this would be correct and fine.

However in the threaded world it becomes.:
```
Germanies chancelor is: Olaf Scholz
Germanies chancelor is: Olaf Scholz
Germanies chancelor is: Olaf Scholz
```
This problem does not apply to subprocesses and subinterpreters, and also not if there is one robotframework instance per thread (however this would come with its own problems).

### processtree
The processtree lacks a solution for the debugfiles to be visualised usefully. Syntax suport to mark suites to be only running in child threads, rebot suport suport with infrastructure like jenkins plugin etc... Integrated infrastructure 
in robotframework for the forward / backwards links.

Longterm it would be a goal to achieve inside robotframework core.:
 - suport for backwards and forwards linking in the logs, across runs
 - ability to use rebot with these forward/backward linking
 - syntax to mark suites to not be run unless inside a child

Longterm it would be a goal to achieve outside the robotframework core.:
 - ability to choose different start methods (spawn/forkserver) (easy)
 - ability to use subinterpreters (upstream is necessary)
   - solving the signaling problem "which subinterpreter timed out?"
   - subinterpreters need to become stable and mainline
 - ability to use threads -> by making robotframework globals thread local (direct competition to AIO aproach)
   - solving the signaling problem "which thread times out?"

Queue+process based concurency is used succesfully by stable systems (erlang, elixer). Unfortunately they are unpopular due to the increased efford spent seperating the state, and explicit data exchange.

### AIO
The AIO solution currently has open issues with concurrency safety, [tkinter and threads](https://github.com/test-fullautomation/robotframework/issues/110]) [deadlock](https://github.com/test-fullautomation/robotframework/issues/117) and [Timeout handling](https://github.com/test-fullautomation/robotframework/issues/118). I am constructive and try to help fixing these issues [fix](https://github.com/robotframework/robotframework/pull/5343) which fixes the tkinter problem of AIO with threads on Windows.

However In my point of view the deadlock issue is not solveable, at best manageable, and I lack experience on the signaling issue.

### Improve guidance and examples and infrastructure for the current situation

The documentation how to use async could be extended to show examples.

For example concurrently listen to more than one socket at a time.:

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
        return (item for item in recvable if item.recv(1, socket.MSG_PEEK))
```
This concept can be extended to file handles on some systems (linux), and even 
more situations, with relative ease.

Infrastructure to make python keywords run in parallel, while still being connected to the robotframework infrastructure (run_keyword), where robotframework continues to run in a single thread. (no example).