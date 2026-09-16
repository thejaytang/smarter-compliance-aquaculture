import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "deployment/rebuild_environments.py"
spec = importlib.util.spec_from_file_location("rebuild_environments", SOURCE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class EnvironmentRebuildTests(unittest.TestCase):
    def test_windows_uses_scripts_interpreters_and_hash_locked_system1(self):
        root = Path("project with spaces")
        plan = setup.commands(root, "python312.exe", windows=True)
        pip = [cmd for _, cmd in plan if cmd[:3] == ["uv", "pip", "install"]]
        self.assertEqual(len(pip), 2)
        self.assertIn(str(root / "system1/Code/.venv/Scripts/python.exe"), pip[0])
        self.assertIn("--require-hashes", pip[0])
        self.assertIn(str(root / "workbench/pyproject.toml"), pip[1])

    def test_reviewer_does_not_touch_system1(self):
        plan = setup.commands(Path("project"), "python312", reviewer=True)
        self.assertTrue(all("system1" not in str(directory) for directory, _ in plan))
        self.assertEqual(len(plan), 2)

    def test_base_system2_resolution_cannot_rewrite_lock(self):
        directory, command = setup.commands(Path("project"), "python312")[-1]
        self.assertEqual(directory, Path("project/system2"))
        self.assertEqual(command, ["uv", "sync", "--locked", "--python", "python312", "--no-editable"])

    def test_macos_workbench_needs_no_dependency_install(self):
        plan = setup.commands(Path("project"), "python312")
        self.assertEqual(len(plan), 4)
        self.assertEqual(sum(cmd[:3] == ["uv", "pip", "install"] for _, cmd in plan), 1)


if __name__ == "__main__":
    unittest.main()
