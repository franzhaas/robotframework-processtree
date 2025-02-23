from rf_processtree import _rf_processtree_base, redirectProcess
import multiprocessing as mp
import tempfile
import os
import robot.api.logger as logger
from robot.api.deco import keyword
from rf_processtree._spawner import _start_child


#python makes sure that the module is only loaded once, therefore this is both thread and process safe
if _rf_processtree_base._rf_processtree_base._linkRedirectQueue is None:
    _rf_processtree_base._rf_processtree_base._linkRedirectQueue = redirectProcess._redirectionProcess


def _make_ofile_safely(prefix, suffix):
    handle, name = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(handle)
    return name


class rf_processtree_parent(_rf_processtree_base._rf_processtree_base):
    def __init__(self, target_suite: str):
        self._child_starter = mp.get_context("spawn")
        super().__init__(self._child_starter.JoinableQueue(), self._child_starter.JoinableQueue())
        self._target_suite = target_suite

    @keyword
    def spawn(self):
        logfile = _make_ofile_safely(prefix=self._oDir + "log_", suffix=".html")
        reportfile = _make_ofile_safely(prefix=self._oDir + "report_", suffix=".html")
        consoleFile = _make_ofile_safely(prefix=self._oDir + "console_", suffix=".txt")
        outXml =  _make_ofile_safely(prefix=self._oDir + "output_", suffix=".xml")

        _linkRedirectQueue = _rf_processtree_base._rf_processtree_base._linkRedirectQueue
        _linkRedirectFileName = _rf_processtree_base._rf_processtree_base._linkRedirectFileName
        self._child_starter.Process(target=_start_child, 
                   args=(self._target_suite, self._readQueue, self._writeQueue, _linkRedirectQueue, _linkRedirectFileName, logfile, reportfile, consoleFile, outXml), daemon=True).start()
        logger.info(f"""Started child process for suite {self._target_suite}, log file: <a href="{logfile}">log</a>, report file: <a href="{reportfile}">report</a>, console file: <a href="{consoleFile}">console</a>""", html=True)
