# rf-processtree
This is an attempt to deal with concurrency in robotframework without needing the
cooperation of the keyword library.

There is another aproach out there.: [AIO](https://github.com/test-fullautomation/RobotFramework_AIO) which attempts to achive the same thing with threads.

## comparison

### speed and features
| Property | rf-processtree | AIO|
| ------------- | ------------- | ------------- |
| GIL | not affected | affected |
| startup overhead | process | thread |
| communication overhead |  serialisation/IPC | within process |
| logging | per process, linked with hyperlinks | debug.log |
| locks | not suported | suported |
| deadlocks | no | possible |
| live locks | no | possible |
|attitude | careful | brave |

### outlook
The processtree lacks a solution for the debugfiles to be merged, syntax suport to mark suites to be only running in child threads, rebot suport suport with infrastructure like jenkins plugin etc...

The AIO solution currently has open issues with concurrency safety, [tkinter and threads](https://github.com/test-fullautomation/robotframework/issues/110]) [deadlock](https://github.com/test-fullautomation/robotframework/issues/117) and [Timeout handling](https://github.com/test-fullautomation/robotframework/issues/118). I am constructive and try to help fixing these issues [fix](https://github.com/robotframework/robotframework/pull/5343) which fixes the tkinter problem of AIO with threads on Windows.
