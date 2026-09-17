"""Database material navigation must not depend on the Excel reader."""
import os
from pathlib import Path
import subprocess
import sys


def test_material_list_does_not_import_excel(tmp_path):
    code = '''
import sys, importlib.abc
from pathlib import Path
from types import SimpleNamespace
class RejectExcel(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'openpyxl' or fullname.startswith('openpyxl.'):
            raise AssertionError('Excel imported during database material navigation')
sys.meta_path.insert(0, RejectExcel())
from pdf_extraction.orchestration.material_service import MaterialService
service = MaterialService(Path('workflow'), Path('system1'))
service.handoff = lambda: SimpleNamespace(records=[], evidence={})
assert service.listing()['materials'] == []
assert not any(n == 'openpyxl' or n.startswith('openpyxl.') for n in sys.modules)
'''
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=__import__('os').pathsep.join((str(Path(__file__).resolve().parents[2]/'backend/system2/src'),str(Path(__file__).resolve().parents[2])))),
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
