import robot
import rf_processtree
from multiprocessing import Queue, JoinableQueue


def start_child(target, read_queue: Queue, write_queue: Queue, redeirectQueue: JoinableQueue, redirectFileName: str, o_dir: str, **kwargs):
    with open(f"{o_dir}/console.log", "w") as console:
        rf_processtree.rf_processtree._link_redirect_queue = redeirectQueue
        rf_processtree.rf_processtree._link_redirect_file_name = redirectFileName
        rf_processtree.rf_processtree._read_queue = write_queue
        rf_processtree.rf_processtree._write_queue = read_queue
        robot.run(target, log=f"{o_dir}/log.html", report=f"{o_dir}/report.html", output=f"{o_dir}/output.xml", stdout=console, **kwargs)
