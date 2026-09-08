import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from local_workbench.qa import weekly_dashboard
from local_workbench.identities import canonical_name, REVIEWERS
from local_workbench.messages import english_message

class WeeklyDashboardTests(unittest.TestCase):
    def snapshot(self, decisions, week='2026-09-07'):
        return {'tasks': [], 'history': [{'operation_id':str(i),'operation_type':'RANDOM_QA_CHECK',
            'source_id':str(i),'program_status':'APPLIED' if decision else 'PENDING',
            'operator':'Ana Jokic' if decision else '', 'decision':decision,
            'payload_json':json.dumps({'batch_week':week})} for i,decision in enumerate(decisions)]}
    def chart(self,snapshot,stamp='2026-09-07T12:00:00'):
        return weekly_dashboard(snapshot,datetime.fromisoformat(stamp).replace(tzinfo=ZoneInfo('Europe/Oslo')).timestamp())
    def test_partial_batch_is_not_perfect_and_errors_count(self):
        point=self.chart(self.snapshot(['CORRECT',None,None,None,None]))['series'][0]['points'][-1]
        self.assertIsNone(point['accuracy']);self.assertEqual(point['reviewed'],1)
        complete=self.chart(self.snapshot(['CORRECT']*4+['INCORRECT']))
        self.assertEqual(complete['series'][0]['points'][-1]['accuracy'],80)
        self.assertTrue(all(p['accuracy'] is None for s in complete['series'][1:] for p in s['points']))
    def test_five_weeks_calendar_gaps_and_smaller_sample(self):
        chart=self.chart(self.snapshot(['CORRECT']*3))
        self.assertEqual(chart['weeks'],['2026-08-10','2026-08-17','2026-08-24','2026-08-31','2026-09-07'])
        self.assertEqual(chart['series'][0]['points'][-1]['sampled'],3)
        self.assertEqual(chart['series'][0]['points'][-1]['accuracy'],100)
        self.assertIsNone(chart['series'][0]['points'][-2]['accuracy'])
        self.assertEqual(self.chart(self.snapshot([]),'2027-01-03T23:59:00')['weeks'][-1],'2026-12-28')
        self.assertEqual(self.chart(self.snapshot([]),'2027-01-04T00:01:00')['weeks'][-1],'2027-01-04')
    def test_legacy_reviews_and_missing_batch_items_are_not_success(self):
        snapshot=self.snapshot(['CORRECT'])
        snapshot['history'].append({'operation_type':'RANDOM_QA_BATCH_SUMMARY','payload_json':json.dumps({'batch_week':'2026-09-07','sampled_count':5})})
        self.assertIsNone(self.chart(snapshot)['series'][0]['points'][-1]['accuracy'])
        snapshot['history'][0]['payload_json']=json.dumps({'batch_month':'2026-09'})
        self.assertEqual(self.chart(snapshot)['series'][0]['points'][-1]['reviewed'],0)
    def test_identity_and_machine_messages_preserve_unknown_original_text(self):
        self.assertEqual([canonical_name(n) for n in ['Jay','ana','DR']],['Weijie Tang','Ana Jokic','Daniel Restad'])
        self.assertEqual(list(REVIEWERS),sorted(REVIEWERS))
        self.assertEqual(canonical_name('Jokic; Ana'),'Ana Jokic')
        self.assertEqual(english_message('请先选择操作人。'),'Please select a reviewer first.')
        self.assertEqual(english_message('原始同事备注'),'原始同事备注')
