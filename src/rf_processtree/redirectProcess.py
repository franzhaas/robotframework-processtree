import multiprocessing as mp
import json
import os
import tempfile
import robot.libraries.BuiltIn as BuiltIn
import pathlib
import contextlib


def _redirectionProcess(q, odir):
    with open(odir / "redirect.html", "w") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <script src="redirects.js"></script>
    <script>
        window.onload = function () {
            const hashPart = window.location.hash.substring(1);
            if (linkMappings[hashPart]) {
                window.location.href = linkMappings[hashPart];
            }
        };
    </script>
</head>
</html>""")
    redirects = {}
    while True:
        source, dest = q.get()
        redirects[source] = dest
        handle, name = tempfile.mkstemp(dir=odir)
        with open(handle, "w") as f:
            f.write("const linkMappings = ")
            json.dump(redirects, f)
        os.replace(name, odir / "redirects.js")
        q.task_done()


def redirectionProcessStarter(oDir=None):
    if oDir is None:
        oDir = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}"))
    _child_starter = mp.get_context("spawn")
    toRedirectionProcess = _child_starter.JoinableQueue()
    _child_starter.Process(target=_redirectionProcess, args=(toRedirectionProcess, oDir), daemon=True).start()
    return toRedirectionProcess

with contextlib.suppress(BuiltIn.RobotNotRunningError):
    _redirectionProcess = redirectionProcessStarter()

