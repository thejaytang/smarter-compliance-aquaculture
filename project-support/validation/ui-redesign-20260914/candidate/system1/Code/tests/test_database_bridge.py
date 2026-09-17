import json
from pathlib import Path
from unittest.mock import patch
from test_workbench_bridge import WorkbenchBridgeTests
import source_updater as u
from system1.governance_store import GovernanceStore
from system1 import workbench_bridge as bridge


class DatabaseBridgeTests(WorkbenchBridgeTests):
    def activate(self):
        cfg = u.read_config(self.config_path)
        if cfg.get('governance_db'): return
        wb = u.open_registry(cfg)
        u.save_workbook_atomic(wb, self.workbook, u.workbook_mtime(self.workbook));wb.close()
        store = GovernanceStore.migrate(cfg, self.runtime/'governance/state.sqlite')
        config = json.loads(self.config_path.read_text());config['governance_db'] = str(store.path)
        self.config_path.write_text(json.dumps(config))

    def task(self, issue=False):
        result = super().task(issue)
        self.activate()
        return next(t for t in bridge.read(self.config_path)['tasks'] if t['operation_id']==result['operation_id'])

    def _source_record(self):
        cfg = u.read_config(self.config_path)
        if not cfg.get('governance_db'): return super()._source_record()
        return GovernanceStore(cfg['governance_db']).snapshot()['sources'][0]['record']

    def weekly_qa_task(self):
        self.activate()
        return super().weekly_qa_task()

    def test_database_decision_does_not_wait_for_excel_or_import_its_edits(self):
        request = self.request(self.task())
        raw = self.workbook.read_bytes()
        lock = self.workbook.with_name('~$'+self.workbook.name);lock.touch()
        with patch('source_updater.run_updates', side_effect=AssertionError('No downloads')):
            self.assertEqual(bridge.apply(self.config_path,request)['status'], 'applied')
        self.assertEqual(self.workbook.read_bytes(), raw)
        self.assertEqual(self._source_record()['operator_selection_decision'], 'INCLUDE')
        self.assertEqual(bridge.read(self.config_path)['authority']['kind'], 'sqlite')

    def test_database_rejects_stale_source_and_excel_readback(self):
        request = self.request(self.task());cfg = u.read_config(self.config_path)
        wb = u.open_registry(cfg);headers=u.workbook_headers(wb[cfg['sheet_name']],2)
        wb[cfg['sheet_name']].cell(3,headers['version']).value = 'New source version metadata'
        u.save_registry(wb,cfg,wb._governance_revision);wb.close()
        before=GovernanceStore(cfg['governance_db']).snapshot()
        with self.assertRaisesRegex(ValueError,'STALE'):bridge.apply(self.config_path,request)
        self.assertEqual(GovernanceStore(cfg['governance_db']).snapshot(), before)
        import sync_run_state
        with self.assertRaisesRegex(u.UpdaterError,'readback is forbidden'):sync_run_state.sync_state(cfg,self.workbook)


# Reuse behavioral journeys whose expectations apply to both authorities.
for name in ('test_review_apply_updates_formula_caches_without_opening_excel',
             'test_bridge_rejects_old_revision_without_write','test_bridge_waits_on_excel_and_requires_actor'):
    setattr(DatabaseBridgeTests,name,None)
del WorkbenchBridgeTests
