import unittest
from local_workbench.export_schedule import ExportSchedule


class ExportScheduleTests(unittest.TestCase):
    def test_burst_is_coalesced_and_continuous_edits_cannot_starve_export(self):
        s=ExportSchedule(0)
        self.assertFalse(s.due((1,1),False,0))
        self.assertFalse(s.due((2,1),True,1))
        self.assertFalse(s.due((3,1),True,2))
        self.assertFalse(s.due((4,1),True,3))
        self.assertFalse(s.due((5,1),True,4))
        self.assertFalse(s.due((6,1),True,5))
        self.assertTrue(s.due((7,1),True,6))
        s.finished(True,10)
        # A write during generation is still pending, so it starts the next
        # coalesced snapshot instead of waiting the old full periodic minute.
        self.assertFalse(s.due((8,1),True,11))
        self.assertTrue(s.due((8,1),True,13))

    def test_failed_write_retries_with_backoff_and_clean_periodic_check(self):
        s=ExportSchedule(0)
        s.due((2,1),True,0)
        self.assertTrue(s.due((2,1),True,2))
        s.finished(False,3)
        self.assertFalse(s.due((2,1),True,7))
        self.assertTrue(s.due((2,1),True,8))
        s.finished(False,9)
        self.assertFalse(s.due((2,1),True,18))
        self.assertTrue(s.due((2,1),True,19))
        s.finished(True,20)
        self.assertFalse(s.due((2,1),False,79))
        self.assertTrue(s.due((2,1),False,80))
        s.finished(False,81)
        self.assertFalse(s.due((2,1),False,85))
        self.assertTrue(s.due((2,1),False,86))
