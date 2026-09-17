"""Application updates must not carry active data or per-machine settings."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
from check_app_boundary import business_file, development_file, naming_issues


class AppBoundaryTests(unittest.TestCase):
    def test_development_branch_includes_evidence_but_not_credentials_or_runtime(self):
        for path in ['PROJECT_STATE.md','project-support/design/visuals/diagram.png','workbench/tests/test_app_boundary.py']:
            self.assertTrue(development_file(path),path)
            self.assertTrue(business_file(path),path)
        for path in ['project-support/backup/runtime/sessions.json','project-support/private/.env',
                     'project-support/old-workflow.sqlite','workbench/tests/.venv/bin/python',
                     'project-support/ai-provider.json','workbench/workspace/databases/system1.sqlite']:
            self.assertFalse(development_file(path),path)
        self.assertEqual(naming_issues(['project-support/Legacy/old-script.py'],style=False),[])
        self.assertTrue(naming_issues(['project-support/CON.txt'],style=False))

    def test_naming_rejects_backup_modules_and_windows_collisions(self):
        self.assertTrue(naming_issues(['workbench/backend/system2/src/derived 2.py']))
        self.assertTrue(naming_issues(['workbench/backend/CON.py']))
        self.assertTrue(naming_issues(['workbench/backend/shared/a.py','workbench/backend/Shared/b.py']))
        self.assertEqual(naming_issues(['Open Workbench (Windows).cmd','Open Workbench (macOS).command',
                                      'workbench/backend/shared/workspace_storage.py']),[])

    def test_business_paths_are_rejected(self):
        for path in ['system1/Data/A_Public_Authority/original.pdf',
                     'workbench/backend/system1/config/config.json',
                     'system1/Requirement_Source_Registry.xlsx',
                     'system2/System2_Requirement_Register 2.xlsx',
                     'project-support/old/fixture/source-register.xlsx',
                     'project-support/old/collaboration.zip',
                     'workbench/runtime/workbench.sqlite',
                     'reviewer-workspace/peer/history.sqlite',
                     'workbench/saved-packages/peer.zip',
                     'system1/saved-records/seed.zip.sha256',
                     'settings/ai-provider.json', '.env']:
            with self.subTest(path=path):
                self.assertTrue(business_file(path))

    def test_code_templates_and_synthetic_fixtures_are_allowed(self):
        for path in ['workbench/config/system1/config.example.json',
                     'workbench/frontend/components/materials.js',
                     'workbench/workspace/README.txt',
                     'workbench/deployment/restore_initial_data.py',
                     'workbench/backend/application/local_workbench/runtime_status.py']:
            with self.subTest(path=path):
                self.assertFalse(business_file(path))
