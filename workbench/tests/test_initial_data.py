"""One-time seed restore must never overwrite colleagues' work or local settings."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile
DEPLOY=Path(__file__).resolve().parents[1]/'deployment'
sys.path.insert(0,str(DEPLOY))
from initialize_local import initialize
from restore_initial_data import restore

class InitialDataTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name);p=self.root/'system1/Code/config';p.mkdir(parents=True)
  for name in ('config','schedule'):(p/(name+'.example.json')).write_text('{"enabled": true}')
 def tearDown(self):self.tmp.cleanup()
 def archive(self,entries=None):
  entries=entries or {'system1/Code/runtime/governance.sqlite':b'synthetic source authority','system1/Data/A_Public_Authority/source.html':'æ中文'.encode()}
  p=self.root/'seed.zip';manifest={'schema':'source-initial-data/1','files':{k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in entries.items()}}
  with zipfile.ZipFile(p,'w') as z:
   for k,v in entries.items():z.writestr(k,v)
   z.writestr('manifest.json',json.dumps(manifest))
  return p,hashlib.sha256(p.read_bytes()).hexdigest()
 def test_fresh_restore_and_repeat_refusal(self):
  p,h=self.archive();self.assertEqual(restore(self.root,p,h)['files'],2)
  self.assertEqual((self.root/'system1/Data/A_Public_Authority/source.html').read_text(),'æ中文')
  config=json.loads((self.root/'system1/Code/config/config.json').read_text());self.assertFalse(config['random_qa']['enabled'])
  with self.assertRaisesRegex(ValueError,'already has work'):restore(self.root,p,h)
 def test_bad_checksum_and_paths_write_no_authority(self):
  p,h=self.archive()
  with self.assertRaisesRegex(ValueError,'checksum'):restore(self.root,p,'0'*64)
  p,h=self.archive({'../outside.txt':b'x'})
  with self.assertRaisesRegex(ValueError,'path'):restore(self.root,p,h)
  self.assertFalse((self.root/'system1/Code/runtime').exists())
 def test_initialization_preserves_existing_config_and_disabled_schedule(self):
  initialize(self.root);config=self.root/'system1/Code/config/config.json';config.write_text('{"user_setting": 42}')
  self.assertEqual(initialize(self.root),[]);self.assertEqual(json.loads(config.read_text()),{'user_setting':42})
  self.assertFalse(json.loads((config.parent/'schedule.json').read_text())['enabled'])
 def test_existing_original_refuses_partial_restore(self):
  p,h=self.archive();path=self.root/'system1/Data/A_Public_Authority/source.html';path.parent.mkdir(parents=True);path.write_text('local work')
  with self.assertRaisesRegex(ValueError,'overwrite'):restore(self.root,p,h)
  self.assertFalse((self.root/'system1/Code/runtime/governance.sqlite').exists());self.assertEqual(path.read_text(),'local work')
