"""Application updates must not carry active data or per-machine settings."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
from check_app_boundary import business_file


class AppBoundaryTests(unittest.TestCase):
    def test_business_paths_are_rejected(self):
        for path in ['system1/Data/A_Public_Authority/original.pdf',
                     'system1/Code/config/config.json',
                     'system1/Requirement_Source_Registry.xlsx',
                     'workbench/runtime/workbench.sqlite',
                     'reviewer-workspace/peer/history.sqlite',
                     'workbench/saved-packages/peer.zip',
                     'system1/saved-records/seed.zip.sha256',
                     'settings/ai-provider.json', '.env']:
            with self.subTest(path=path):
                self.assertTrue(business_file(path))

    def test_code_templates_and_synthetic_fixtures_are_allowed(self):
        for path in ['system1/Code/config/config.example.json',
                     'system1/Code/tests/fixtures/source_registry.xlsx',
                     'system1/Data/STORAGE.md',
                     'workbench/deployment/restore_initial_data.py',
                     'workbench/src/local_workbench/runtime_status.py']:
            with self.subTest(path=path):
                self.assertFalse(business_file(path))
