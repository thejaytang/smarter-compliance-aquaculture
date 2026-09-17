"""Committed response and durable replay retain the same saved version semantics."""
import unittest

class SavedResponseChecks(unittest.TestCase):
    def test_saved_response_replay_conflict_and_newer_revision(self):
        from test_interpretations import InterpretationTests as Fixture, ACTOR
        f=Fixture();f.setUp()
        try:
            req=f.request();result=f.s.save_and_read(ACTOR,req)
            self.assertEqual(result['document']['revision'],1)
            self.assertEqual(len(f.s.save_and_read(ACTOR,req)['document']['history']),1)
            newer=dict(req,request_id='d81d287b-33cd-42fa-9ab7-78d4c3839fda',expected_revision=1)
            self.assertEqual(f.s.save_and_read(ACTOR,newer)['document']['revision'],2)
            replay=f.s.save_and_read(ACTOR,req)
            self.assertEqual(replay['revision'],1)
            self.assertEqual(replay['document']['revision'],2)
            self.assertEqual(len(replay['document']['history']),2)
            rejected=f.s.save_and_read(ACTOR,f.request())
            self.assertEqual(rejected['status'],'conflict')
            self.assertNotIn('document',rejected)
        finally:f.tearDown()
