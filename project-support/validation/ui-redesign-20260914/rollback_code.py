"""Restore only this activation's code, with the service stopped. Never restore stores."""
from pathlib import Path
import hashlib, json, shutil, sys
area=Path(__file__).resolve().parent;root=area.parents[1]
sys.path.insert(0,str(root/'workbench/src'))
from local_workbench.platform_support import process_alive
marker=root/'workbench/runtime/server.json'
if marker.exists() and process_alive(json.loads(marker.read_text())['pid']):
    raise SystemExit('Exit the normal workbench first.')
promotion=json.loads((area/'promotion.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
retained=area/'rolled-back-code'
if retained.exists():raise SystemExit('A previous rollback exists; inspect it first.')
for item in promotion['files']:
    if sha(root/item['path'])!=item['after']:raise SystemExit('Later code changes exist; stop for review: '+item['path'])
    if item['before'] is not None and sha(area/'activation-checkpoint/code'/item['path'])!=item['before']:
        raise SystemExit('Rollback copy mismatch: '+item['path'])
for item in promotion['files']:
    target=root/item['path'];saved=retained/item['path'];saved.parent.mkdir(parents=True,exist_ok=True)
    target.rename(saved)
    if item['before'] is not None:
        shutil.copy2(area/'activation-checkpoint/code'/item['path'],target)
        if sha(target)!=item['before']:raise SystemExit('Restored code mismatch.')
print('Code rollback complete. Business stores, originals and historical assets were not restored or modified.')
