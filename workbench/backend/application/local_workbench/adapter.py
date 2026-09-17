import json
import os
import subprocess
from pathlib import Path
from contextlib import nullcontext
from backend.shared.messages import english_message
from backend.shared.platform_support import venv_python, system1_code, python_path
from backend.shared.timing import span, measured


class System1:
    def __init__(self, system_root, config=None):
        self.root = Path(system_root).resolve()
        self.config = Path(config).resolve() if config else system1_code(self.root) / "config/config.json"

    def call(self, command, **kwargs):
        with span('system1.' + command):
            if getattr(self, 'pool', None) is not None:
                code = system1_code(self.root)
                self.pool.prepare(venv_python(code), 'system1.workbench_bridge', code,
                    dict(os.environ, PYTHONPATH=python_path(code / 'src'), PYTHONUTF8='1'))
            with getattr(self,'gate',nullcontext()):return self._call(command,**kwargs)

    @measured('system1.process')
    def _call(self, command, **kwargs):
        code = system1_code(self.root)
        env = dict(os.environ, PYTHONPATH=python_path(code / "src"), PYTHONUTF8="1")
        payload = {"command":command, "config":str(self.config), **kwargs}
        if getattr(self, 'pool', None) is not None:
            reply = self.pool.request(venv_python(code), 'system1.workbench_bridge', code, env, payload)
        else:
            result = subprocess.run([str(venv_python(code)), "-m", "system1.workbench_bridge"],
                input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", cwd=code, env=env, timeout=180)
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
        with span('system2.' + command):
            if command == 'material_compute':
                # Pure parsing touches only immutable originals and new artifacts.
                # Its prepare/finalize commands retain the write gate.
                return self._call(command, **kwargs)
            if getattr(self, 'pool', None) is not None and command != 'source_metadata':
                module = 'pdf_extraction.orchestration.material_service' if command.startswith('material_') else 'pdf_extraction.orchestration.workflow'
                self.pool.prepare(venv_python(self.root), module, self.root,
                    dict(os.environ, PYTHONPATH=python_path(self.root / 'src'), PYTHONUTF8='1'))
            with getattr(self,'gate',nullcontext()):return self._call(command,**kwargs)

    @measured('system2.process')
    def _call(self, command, **kwargs):
        request = dict(root=str(self.runtime), system1=str(self.system1), command=command, **kwargs)
        if self.config:
            request['system1_config'] = str(self.config)
        module = 'pdf_extraction.orchestration.material_service' if command.startswith('material_') else 'pdf_extraction.orchestration.workflow'
        if command == 'source_metadata': module = 'pdf_extraction.intake.source_metadata'
        if command == 'material_compute': module = 'pdf_extraction.orchestration.material_job'
        env = dict(os.environ, PYTHONPATH=python_path(self.root / 'src'), PYTHONUTF8='1')
        timeout = 900 if command in {'tick', 'workbook', 'material_tick', 'material_compute'} else 180
        if getattr(self, 'pool', None) is not None and command not in {'source_metadata', 'material_compute'}:
            reply = self.pool.request(venv_python(self.root), module, self.root, env, request, timeout)
        else:
            result = subprocess.run([str(venv_python(self.root)), '-m', module],
                input=json.dumps(request), capture_output=True, text=True, encoding="utf-8", cwd=self.root,
                env=env, timeout=timeout)
            try:
                reply = json.loads(result.stdout)
            except ValueError:
                raise RuntimeError('System2 did not return a valid receipt.')
        if not reply.get('ok'):
            raise ValueError(reply.get('error', 'System2 request failed.'))
        return reply['data']
