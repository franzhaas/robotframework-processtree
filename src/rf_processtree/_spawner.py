import io
import robot
import rf_processtree
from multiprocessing import Queue, JoinableQueue


def _start_child(target_suite: str, readQueue: Queue, writeQueue: Queue, redeirectQueue: JoinableQueue, redirectFileName: str, logfile: str, reportfile: str, consoleFile: str, outXml: str, loglevel):
    console = io.TextIOWrapper(open(consoleFile, "wb", buffering=0), write_through=True)
    rf_processtree.rf_processtree._linkRedirectQueue = redeirectQueue
    rf_processtree.rf_processtree._linkRedirectFileName = redirectFileName
    rf_processtree.rf_processtree._readQueue = writeQueue
    rf_processtree.rf_processtree._writeQueue = readQueue
    robot.run(target_suite, outputdir=".", loglevel=loglevel, log=logfile, report=reportfile, output=outXml, stdout=console)
