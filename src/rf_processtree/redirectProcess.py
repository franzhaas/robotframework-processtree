import multiprocessing as mp
import json
import os
import tempfile
import robot.libraries.BuiltIn as BuiltIn
import pathlib
import contextlib


def _redirectionProcess(q, odir):
    redirects = {}
    while True:
        source, dest = q.get()
        redirects[source] = dest
        handle, name = tempfile.mkstemp(dir=odir)
        with open(handle, "w") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <script src="redirects.js"></script>
    <script>
        const linkMappings = {json.dumps(redirects)}
        window.onload = function () {{
            const hashPart = window.location.hash.substring(1);
            if (linkMappings[hashPart]) {{
                window.location.href = linkMappings[hashPart];
            }}
        }};
    </script>
</head>
</html>""")
        os.replace(name, odir / "redirect.html")
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

