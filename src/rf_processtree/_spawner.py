import io
import robot
from rf_processtree import _rf_processtree_base, rf_processtree_child


def _start_child(target_suite: str, readQueue, writeQueue, redeirectQueue, redirectFileName, logfile, reportfile, consoleFile, outXml):
    console = io.TextIOWrapper(open(consoleFile, "wb", buffering=0), write_through=True)
    _rf_processtree_base._rf_processtree_base._linkRedirectQueue = redeirectQueue
    _rf_processtree_base._rf_processtree_base._linkRedirectFileName = redirectFileName
    rf_processtree_child.rf_processtree_child._readQueue = readQueue
    rf_processtree_child.rf_processtree_child._writeQueue = writeQueue
    robot.run(target_suite, outputdir=".", loglevel="TRACE", log=logfile, report=reportfile, output=outXml, stdout=console)
