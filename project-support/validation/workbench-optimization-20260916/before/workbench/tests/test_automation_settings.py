from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from datetime import datetime,timezone,timedelta
from local_workbench.collaboration import Collaboration
from local_workbench.automation_settings import AutomationSettings
class AutomationTests(unittest.TestCase):
 def test_save_delays_first_run_and_rejects_stale_update(self):
  with TemporaryDirectory() as temp:
   app=SimpleNamespace(runtime=Path(temp),reviewer=False);app.collaboration=Collaboration(app)
   service=AutomationSettings(app);before=service.read()
   self.assertFalse(before['settings']['enabled']);self.assertIsNone(before['next_run'])
   values={'enabled':True,'timezone':'Europe/Oslo','interval_days':14,'sample_size':3,'assignee':'Ana Jokic'}
   after=service.save('Daniel Restad',{'revision':before['revision'],'settings':values})
   self.assertGreater(datetime.fromisoformat(after['next_run']),datetime.now(timezone.utc)+timedelta(days=13))
   self.assertEqual(app.collaboration.all('material_inspection_batch'),[])
   with self.assertRaisesRegex(ValueError,'changed'):service.save('Daniel Restad',{'revision':before['revision'],'settings':values})
   app.reviewer=True
   with self.assertRaises(ValueError):service.save('Daniel Restad',{'revision':after['revision'],'settings':values})
if __name__=='__main__':unittest.main()
