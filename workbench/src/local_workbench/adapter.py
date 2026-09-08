import json
import os
import subprocess
from pathlib import Path
from .messages import english_message


class System1:
    def __init__(self, system_root, config=None):
        self.root = Path(system_root).resolve()
        self.config = Path(config).resolve() if config else self.root / "Code/config/config.json"

    def call(self, command, **kwargs):
        code = self.root / "Code"
        env = dict(os.environ, PYTHONPATH=str(code / "src"))
        result = subprocess.run(
            [str(code / ".venv/bin/python"), "-m", "system1.workbench_bridge"],
            input=json.dumps({"command":command, "config":str(self.config), **kwargs}),
            capture_output=True, text=True, cwd=code, env=env, timeout=180)
        try:
            reply = json.loads(result.stdout)
        except ValueError:
            raise RuntimeError("System1 did not return a valid receipt. Check the local service log.")
        if not reply["ok"]:
            raise RuntimeError(english_message(reply["error"]))
        data = reply["data"]
        if command == "apply" and isinstance(data, dict):
            data = dict(data, message=english_message(data.get("message", "")))
        return data
