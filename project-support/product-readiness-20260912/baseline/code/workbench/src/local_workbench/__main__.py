import argparse
from contextlib import ExitStack
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from .server import serve
from .platform_support import exclusive_lock, detached_process_kwargs


def running(root, reviewer=False):
    try:
        state=json.loads((root/"runtime/server.json").read_text())
        with urllib.request.urlopen(f"http://127.0.0.1:{state['port']}/health",timeout=1) as response:
            health=json.load(response)
        if health.get("root")==str(root) and health.get("instance")==state["instance"]:
            if (health.get("mode", "coordinator") == "reviewer") != reviewer:
                raise RuntimeError("This directory is already running in a different workbench mode.")
            return f"http://127.0.0.1:{state['port']}/"
    except (OSError,ValueError,KeyError):
        pass
    return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--serve",action="store_true")
    parser.add_argument("--reviewer",action="store_true", help="Open an imported isolated offline reviewer workspace")
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument("--system-root",type=Path)
    parser.add_argument("--config",type=Path)
    args=parser.parse_args()
    root=args.root.resolve();(root/"runtime").mkdir(parents=True,exist_ok=True)
    if args.serve:
        with ExitStack() as stack:
            try: stack.enter_context(exclusive_lock(root/"runtime/service.lock"))
            except BlockingIOError: return
            kwargs = {'reviewer': True} if args.reviewer else {}
            serve(root,args.system_root,args.config,**kwargs)
        return
    with exclusive_lock(root/"runtime/launcher.lock", blocking=True):
        url=running(root, args.reviewer)
        if not url:
            with (root/"runtime/service.log").open("a") as log:
                command=[sys.executable,"-m","local_workbench","--serve","--root",str(root)]
                if args.system_root:command.extend(["--system-root",str(args.system_root)])
                if args.config:command.extend(["--config",str(args.config)])
                if args.reviewer:command.append("--reviewer")
                process=subprocess.Popen(command,stdout=log,stderr=log,stdin=subprocess.DEVNULL,
                                         cwd=root,env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONUTF8="1"),
                                         **detached_process_kwargs())
            for _ in range(100):
                url=running(root, args.reviewer)
                if url:break
                if process.poll() is not None:break
                time.sleep(.1)
        if not url:
            raise SystemExit("Workbench could not start. Check workbench/runtime/service.log.")
    if not args.no_browser:
        if sys.platform=="darwin":subprocess.run(["/usr/bin/open",url],check=True)
        else:webbrowser.open(url)
    print(url)


if __name__=="__main__":
    main()
