import unittest
from local_workbench.dashboard import build_dashboard


class DashboardTests(unittest.TestCase):
    def test_source_totals_and_overlapping_task_reasons(self):
        sources=[{'source_id':'A','effective_selection':'INCLUDE','snapshot_status':'STORED','folder_code':'A_Public_Authority'},
                 {'source_id':'B','effective_selection':'PENDING','snapshot_status':'MISSING','folder_code':'B_Standards_Body'},
                 {'source_id':'C','effective_selection':'EXCLUDE','snapshot_status':'STORED','folder_code':'C_Certification_Scheme'}]
        task={'source_id':'B','operation_id':'task','source_title':'B','trigger':'SELECTION_PENDING; PAYWALL_BLOCKED','source':sources[1],'human_issue':{'reason':'Verify'}}
        result=build_dashboard({'sources':sources,'tasks':[task]},123)
        self.assertEqual(result['counts'],{'sources':3,'pending':1,'stored':2,'included':1,'missing':1})
        self.assertEqual(sum(row['count'] for row in result['selection']),3)
        self.assertEqual(sum(row['count'] for row in result['categories']),3)
        self.assertEqual([row['count'] for row in result['issues']],[1,1,1,0])
        self.assertEqual(result['issues'][0]['source_ids'],['B'])
        self.assertEqual(result['priority'][0]['task_id'],'task')
        self.assertEqual(result['as_of'],123)
        self.assertEqual(result['scope'],'requirement_workstream')
        self.assertEqual([s['key'] for s in result['systems']],['system1','system2','system3'])
        self.assertEqual(result['systems'][0]['pending']['value'],1)
        self.assertEqual([m['value'] for m in result['systems'][0]['metrics']],[3,1])

    def test_unconnected_systems_do_not_inherit_sources_or_demo_progress(self):
        result=build_dashboard({'sources':[{'source_id':'A','effective_selection':'INCLUDE'}],
                                'tasks':[], 'demo':{'system2':{'reviewed':5}}},0)
        for system in result['systems'][1:]:
            self.assertFalse(system['review_connected'])
            self.assertIsNone(system['pending']['value'])
            self.assertTrue(all(metric['value'] is None for metric in system['metrics']))
        self.assertNotIn('total_pending', result)

    def test_empty_snapshot_has_no_fabricated_progress(self):
        result=build_dashboard({'sources':[],'tasks':[]},0)
        self.assertEqual(result['counts']['sources'],0)
        self.assertEqual(result['priority'],[])
        self.assertEqual(sum(x['count'] for x in result['selection']),0)
