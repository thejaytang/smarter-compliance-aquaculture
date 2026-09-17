import json
import os
import subprocess
from pathlib import Path
from .messages import english_message
from .platform_support import venv_python


class System1:
    def __init__(self, system_root, config=None):
        self.root = Path(system_root).resolve()
        self.config = Path(config).resolve() if config else self.root / "Code/config/config.json"

    def call(self, command, **kwargs):
        code = self.root / "Code"
        env = dict(os.environ, PYTHONPATH=str(code / "src"), PYTHONUTF8="1")
        result = subprocess.run(
            [str(venv_python(code)), "-m", "system1.workbench_bridge"],
            input=json.dumps({"command":command, "config":str(self.config), **kwargs}),
            capture_output=True, text=True, encoding="utf-8", cwd=code, env=env, timeout=180)
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


class System2:
    def __init__(self, root, system1, config=None, runtime=None):
        self.root = Path(root).resolve()
        self.system1 = Path(system1).resolve()
        self.config = Path(config).resolve() if config else None
        self.runtime = Path(runtime).resolve() if runtime else self.root / 'runtime' / 'workflow'

    def call(self, command, **kwargs):
        request = dict(root=str(self.runtime), system1=str(self.system1), command=command, **kwargs)
        if self.config:
            request['system1_config'] = str(self.config)
        module = 'pdf_extraction.orchestration.material_service' if command.startswith('material_') else 'pdf_extraction.orchestration.workflow'
        if command == 'source_metadata': module = 'pdf_extraction.intake.source_metadata'
        result = subprocess.run([str(venv_python(self.root)), '-m', module],
            input=json.dumps(request), capture_output=True, text=True, encoding="utf-8", cwd=self.root,
            env=dict(os.environ, PYTHONPATH=str(self.root / 'src'), PYTHONUTF8='1'), timeout=900 if command in {'tick', 'workbook', 'material_tick'} else 180)
        try:
            reply = json.loads(result.stdout)
        except ValueError:
            raise RuntimeError('System2 did not return a valid receipt.')
        if not reply.get('ok'):
            raise ValueError(reply.get('error', 'System2 request failed.'))
        return reply['data']
