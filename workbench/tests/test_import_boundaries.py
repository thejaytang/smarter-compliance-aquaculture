"""Guard ownership boundaries and imports without ambient checkout discovery."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from backend.shared.platform_support import python_path

ROOT = Path(__file__).resolve().parents[1]


class ImportBoundaryTests(unittest.TestCase):
    def test_shared_and_system3_do_not_import_application_or_search_for_modules(self):
        for area in ('shared', 'system3'):
            for file in (ROOT/'backend'/area).glob('*.py'):
                with self.subTest(file=file.name):
                    tree = ast.parse(file.read_text())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            self.assertFalse((node.module or '').startswith('local_workbench'))
                        if isinstance(node, ast.Call):
                            self.assertNotIn(ast.unparse(node.func), ('sys.path.insert', 'sys.path.append', '__path__.extend'))

    def test_declared_roots_work_without_site_packages_or_working_directory(self):
        code = '''from pathlib import Path
import backend.shared.workspace_storage as storage
import backend.system3.requirements as requirements
import local_workbench.server as server
assert Path(storage.__file__).parent.name == 'shared'
assert Path(requirements.__file__).parent.name == 'system3'
assert server.Application.__module__ == 'local_workbench.application'
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-S', '-c', code], cwd=directory,
                env=dict(os.environ, PYTHONPATH=python_path()), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
