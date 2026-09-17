import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "deployment.py"
spec = importlib.util.spec_from_file_location("workbench_deployment", SOURCE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class EnvironmentRebuildTests(unittest.TestCase):
    def test_windows_uses_scripts_interpreters_and_hash_locked_system1(self):
        root = Path("project with spaces")
        plan = setup.installation_commands(root, "python312.exe", windows=True)
        pip = [cmd for _, cmd in plan if cmd[:3] == ["uv", "pip", "install"]]
        self.assertEqual(len(pip), 2)
        self.assertIn(str(root / "workbench/backend/system1/.venv/Scripts/python.exe"), pip[0])
        self.assertIn("--require-hashes", pip[0])
        self.assertIn(str(root / "workbench/pyproject.toml"), pip[1])

    def test_reviewer_does_not_touch_system1(self):
        plan = setup.installation_commands(Path("project"), "python312", reviewer=True)
        self.assertTrue(all("system1" not in str(directory) for directory, _ in plan))
        self.assertEqual(len(plan), 2)

    def test_base_system2_resolution_cannot_rewrite_lock(self):
        directory, command = next(item for item in setup.installation_commands(Path("project"), "python312") if item[1][:2] == ["uv", "sync"])
        self.assertEqual(directory, Path("project/workbench/backend/system2"))
        self.assertEqual(command, ["uv", "sync", "--locked", "--python", "python312", "--no-editable", "--inexact"])

    def test_macos_workbench_needs_no_dependency_install(self):
        plan = setup.installation_commands(Path("project"), "python312")
        self.assertEqual(len(plan), 4)
        self.assertEqual(sum(cmd[:3] == ["uv", "pip", "install"] for _, cmd in plan), 1)


if __name__ == "__main__":
    unittest.main()
