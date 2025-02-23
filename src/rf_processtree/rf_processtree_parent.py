from rf_processtree import _rf_processtree_base, redirectProcess
import multiprocessing as mp
import tempfile
import robot.libraries.BuiltIn as BuiltIn
import os
import robot.api.logger as logger
from robot.api.deco import keyword, library


#python makes sure that the module is only loaded once, therefore this is both thread and process safe
if _rf_processtree_base._rf_processtree_base._linkRedirectQueue is None:
    _rf_processtree_base._rf_processtree_base._linkRedirectQueue = redirectProcess._redirectionProcess


def _make_ofile_safely(prefix, suffix):
    handle, name = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(handle)
    return name


def _start_child(target_suite: str, readQueue, writeQueue, redeirectQueue, redirectFileName, logfile, reportfile, consoleFile):
    import sys
    import io
    console = io.TextIOWrapper(open(consoleFile, "wb", buffering=0), write_through=True)
    sys.__stdout__ = console
    sys.__stderr__ = console
    import robot
    from rf_processtree import _rf_processtree_base, rf_processtree_child
    _rf_processtree_base._rf_processtree_base._linkRedirectQueue = redeirectQueue
    _rf_processtree_base._rf_processtree_base._linkRedirectFileName = redirectFileName
    rf_processtree_child.rf_processtree_child._readQueue = readQueue
    rf_processtree_child.rf_processtree_child._writeQueue = writeQueue
    robot.run(target_suite, outputdir=".", loglevel="TRACE", log=logfile, report=reportfile)

class rf_processtree_parent(_rf_processtree_base._rf_processtree_base):
    def __init__(self, target_suite: str):
        super().__init__(None, None)
        self._target_suite = target_suite

    @keyword
    def start_child(self, readQueue=None):
        _child_starter = mp.get_context("spawn")
        if readQueue is None:
            readQueue = _child_starter.JoinableQueue()
        self._set_queues(readQueue, _child_starter.JoinableQueue())
        oDir = BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}")+"/"
        logfile = _make_ofile_safely(prefix=oDir, suffix="_log.html")
        reportfile = _make_ofile_safely(prefix=oDir, suffix="_report.html")
        consoleFile = _make_ofile_safely(prefix=oDir, suffix="_console.txt")

        _linkRedirectQueue = _rf_processtree_base._rf_processtree_base._linkRedirectQueue
        _linkRedirectFileName = _rf_processtree_base._rf_processtree_base._linkRedirectFileName
        _child_starter.Process(target=_start_child, 
                   args=(self._target_suite, self._readQueue, self._writeQueue, _linkRedirectQueue, _linkRedirectFileName, logfile, reportfile, consoleFile), daemon=True).start()
        logger.info(f"""Started child process for suite {self._target_suite}, log file: <a href="{logfile}">log</a>, report file: <a href="{reportfile}">report</a>, console file: <a href="{consoleFile}">console</a>""", html=True)
