import tempfile
import unittest
from pathlib import Path
from system1.source_assessment import Assessments,FIELDS


class MachineAssessmentTests(unittest.TestCase):
    def test_unknown_is_not_high_confidence_and_hash_proof_has_limited_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            owner=Assessments(Path(folder)/'assessment.sqlite')
            source={'source_id':'PA001','source_revision':'r1','content_hash':'a'*64,
                    'snapshot_id':'PA001-001','official_url':'https://example.test','_snapshot_verified':True}
            result=owner.evaluate(source,[])
            self.assertEqual(result['dimensions']['traceability']['confidence'],1)
            self.assertIsNone(result['dimensions']['scope_relevance']['confidence'])

    def test_machine_selection_and_threshold_raise_preserve_humans(self):
        with tempfile.TemporaryDirectory() as folder:
            owner=Assessments(Path(folder)/'assessment.sqlite')
            source={'source_id':'PA001','source_revision':'r1','content_hash':'a'*64,'operator_selection_decision':'PENDING',
                'effective_selection':'PENDING','snapshot_status':'STORED','source_status':'CURRENT','download_status':'SUCCESS',
                'issuer':'Authority','acquisition_channel':'OFFICIAL_WEBSITE','provenance_status':'VERIFIED',
                'official_url':'https://example.test/official'}
            rules=[dict(source_id='PA001',source_revision='r1',source_sha256='a'*64,field=f,
                        rating='HIGH',confidence=.96,evidence=['independently verified fixture'],calibration_version='test/1') for f in FIELDS]
            owner.evaluate(source,rules)
            self.assertEqual(owner.project([dict(source)],[],[])[0]['effective_selection'],'INCLUDE')
            owner.policy(2,.98)
            self.assertEqual(owner.project([dict(source)],[],[])[0]['effective_selection'],'PENDING')
            human=dict(source,operator_selection_decision='INCLUDE',effective_selection='INCLUDE')
            self.assertEqual(owner.project([human],[],[])[0]['selection_origin'],'human')

    def test_provider_failure_preserves_offline_assessment(self):
        with tempfile.TemporaryDirectory() as folder:
            class Broken:
                def assess(self,source):raise TimeoutError('unavailable')
            result=Assessments(Path(folder)/'db').evaluate({'source_id':'PA001','source_revision':'r1'},[],Broken())
            self.assertEqual(result['mode'],'NO_API_FALLBACK')
            self.assertTrue(all(v['confidence'] is None for v in result['dimensions'].values()))

    def test_automatic_task_projection_reopens_and_draft_hold_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            owner=Assessments(Path(folder)/'db')
            source={'source_id':'PA001','source_revision':'r1','content_hash':'a'*64,'operator_selection_decision':'PENDING',
                'effective_selection':'PENDING','snapshot_status':'STORED','source_status':'CURRENT','download_status':'SUCCESS',
                'issuer':'Authority','acquisition_channel':'OFFICIAL_WEBSITE','provenance_status':'VERIFIED',
                'official_url':'https://example.test/official'}
            rules=[dict(source_id='PA001',source_revision='r1',source_sha256='a'*64,field=f,rating='HIGH',
                        confidence=.96,evidence=['fixture evidence'],calibration_version='test/1') for f in FIELDS]
            owner.evaluate(source,rules)
            task={'source_id':'PA001','operation_id':'same-task','operation_type':'SELECTION_REVIEW','trigger':'SELECTION_PENDING'}
            tasks=[dict(task)];owner.project([dict(source)],tasks,[]);self.assertFalse(tasks)
            owner.policy(2,.98);tasks=[dict(task)];owner.project([dict(source)],tasks,[])
            self.assertEqual(tasks[0]['operation_id'],'same-task')
            owner.hold('PA001','Ana Jokic');owner.policy(3,.50)
            self.assertEqual(owner.project([dict(source)],[dict(task)],[])[0]['effective_selection'],'PENDING')
