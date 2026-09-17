from pathlib import Path
import json,hashlib,shutil,tempfile,sqlite3,zipfile
from unittest.mock import patch
from restore_initial_data import restore
import local_workbench.workspace_migration as migration
from local_workbench.application import Application
from local_workbench.workspace_integrity import inspect
root=Path(__file__).resolve().parents[3];archive=root/'workbench/initial-data/workspace-20260917.zip'
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='workbench-initial-check-') as folder:
 target=Path(folder);shutil.copytree(root/'workbench/config',target/'workbench/config')
 original=migration.clone_file
 def interrupted(src,dst):
  if dst.name=='system2.sqlite':raise OSError('injected initial-import interruption')
  return original(src,dst)
 with patch.object(migration,'clone_file',side_effect=interrupted):
  try:restore(target,archive,digest)
  except OSError as e:assert 'injected' in str(e)
  else:raise AssertionError('Interruption did not run')
 assert not (target/'workbench/runtime/state/layout.json').exists()
 result=restore(target,archive,digest)
 assert result['status']=='restored'
 with zipfile.ZipFile(archive) as z:
  for name in ('system1','system2','system3_requirements','system3_scd'):
   p=target/'workbench/workspace/databases'/(name+'.sqlite')
   assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(z.read('databases/'+p.name)).hexdigest()
 try:restore(target,archive,digest)
 except ValueError as e:assert 'already has work' in str(e)
 else:raise AssertionError('Existing data overwritten')
 report=inspect(target/'workbench/workspace/databases',target/'workbench/workspace/sources')
 app=Application(target/'workbench',code_root=root,start_workers=False)
 try:
  payload=app.snapshot()
  assert len(payload['sources'])==88,len(payload['sources'])
 finally:app.close()
 print(json.dumps({'fresh_restore':True,'interruption_retry':True,'database_bytes_preserved':True,'refuse_overwrite':True,'sources':88,'originals':len(report['originals'])}))
