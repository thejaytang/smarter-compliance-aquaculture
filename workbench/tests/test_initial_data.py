"""Initial-data verification and preservation of an existing workspace."""
import hashlib,json,sys,unittest,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from restore_initial_data import restore
class InitialDataTests(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def archive(self,entries):
  p=self.root/'seed.zip';m={'schema':'source-initial-data/1','files':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in entries.items()}}
  with zipfile.ZipFile(p,'w') as z:
   for k,v in entries.items():z.writestr(k,v)
   z.writestr('manifest.json',json.dumps(m))
  return p,hashlib.sha256(p.read_bytes()).hexdigest()
 def test_bad_checksum_and_paths_never_activate_data(self):
  p,h=self.archive({'../outside.txt':b'x'})
  with self.assertRaisesRegex(ValueError,'checksum'):restore(self.root,p,'0'*64)
  with self.assertRaisesRegex(ValueError,'path'):restore(self.root,p,h)
  self.assertFalse((self.root/'workbench/runtime/state/layout.json').exists())
  self.assertFalse((self.root/'outside.txt').exists())
 def test_existing_business_database_is_never_overwritten(self):
  p,h=self.archive({'system1/Code/runtime/governance.sqlite':b'invalid incoming database'})
  saved=self.root/'workbench/workspace/databases/system3_scd.sqlite';saved.parent.mkdir(parents=True);saved.write_bytes(b'saved work')
  with self.assertRaisesRegex(ValueError,'already has work'):restore(self.root,p,h)
  self.assertEqual(saved.read_bytes(),b'saved work')
 def test_different_interrupted_seed_is_not_overwritten(self):
  p,h=self.archive({'system1/Data/source.html':b'incoming original'})
  saved=self.root/'workbench/runtime/backups/initial-import/system1/Data/source.html';saved.parent.mkdir(parents=True);saved.write_bytes(b'earlier original')
  with self.assertRaisesRegex(ValueError,'earlier initial-data attempt differs'):restore(self.root,p,h)
  self.assertEqual(saved.read_bytes(),b'earlier original')
 def test_private_api_settings_are_not_touched_on_rejected_seed(self):
  saved=self.root/'workbench/runtime/settings/ai-provider.json';saved.parent.mkdir(parents=True);saved.write_text('{"api_key":"private-test-key"}')
  p,h=self.archive({'workbench/runtime/settings/ai-provider.json':b'overwrite'})
  with self.assertRaisesRegex(ValueError,'path'):restore(self.root,p,h)
  self.assertIn('private-test-key',saved.read_text())
