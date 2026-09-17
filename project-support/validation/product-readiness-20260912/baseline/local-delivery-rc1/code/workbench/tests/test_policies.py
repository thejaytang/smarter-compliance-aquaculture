import tempfile
import unittest
from pathlib import Path
from local_workbench.policies import Policies


class PolicyTests(unittest.TestCase):
    def test_revision_validation_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'db';store=Policies(path)
            values={k:v for k,v in store.get().items() if k!='revision'}
            values['content']=.98
            self.assertEqual(store.save(values,'Ana Jokic',1)['revision'],2)
            self.assertEqual(Policies(path).get()['content'],.98)
            self.assertEqual(len(store.history()),2)
            with self.assertRaises(ValueError):store.save(values,'Ana Jokic',1)
            with self.assertRaises(ValueError):store.save(dict(values,content=float('nan')),'Ana Jokic',2)
