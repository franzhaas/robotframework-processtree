import multiprocessing as mp
import json
import os
import tempfile
import robot.libraries.BuiltIn as BuiltIn
import pathlib
import contextlib


_redirectionFile = "redirect.html"

def _redirectionProcessWorker(q, odir):
    redirects = {}
    while True:
        payload = q.get()
        redirects[payload.key] = payload.dest
        handle, name = tempfile.mkstemp(dir=odir)
        with open(handle, "w") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <script>
        const linkMappings = {json.dumps(redirects)}
        window.onload = function () {{
            const hashPart = window.location.hash.substring(1);
            if (linkMappings[hashPart]) {{
                window.location.href = linkMappings[hashPart];
            }} else {{
                document.body.innerHTML = '<h1>Error: broken link. likely this link points to something which has not materialised...</h1>';
            }}
        }};
    </script>
</head>
</html>""")
        os.replace(name, odir / _redirectionFile)
        q.task_done()


def redirectionProcessStarter(oDir=None):
    if oDir is None:
        oDir = pathlib.Path(BuiltIn.BuiltIn().get_variable_value("${OUTPUTDIR}"))
    _child_starter = mp.get_context("spawn")
    toRedirectionProcess = _child_starter.JoinableQueue()
    _child_starter.Process(target=_redirectionProcessWorker, args=(toRedirectionProcess, oDir), daemon=True).start()
    return toRedirectionProcess


with contextlib.suppress(BuiltIn.RobotNotRunningError):
    _redirectionProcess = redirectionProcessStarter()
