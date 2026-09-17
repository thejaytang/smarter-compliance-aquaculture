"""Copy only verified candidate code/tests while the normal service is stopped."""
from pathlib import Path
import hashlib,json,shutil,sys,urllib.request
area=Path(__file__).resolve().parent;root=area.parents[1];candidate=area/'candidate'
sys.path.insert(0,str(candidate/'workbench/src'))
from local_workbench.platform_support import process_alive
marker=root/'workbench/runtime/server.json'
if marker.exists() and process_alive(json.loads(marker.read_text())['pid']):raise SystemExit('Normal workbench must be stopped.')
manifest=json.loads((area/'activation-checkpoint/manifest.json').read_text())
if manifest.get('status')!='complete':raise SystemExit('Activation checkpoint is incomplete.')
lines=(area/'checkpoint-result.txt').read_text().splitlines()
if not lines or json.loads(lines[-1]).get('status')!='complete':raise SystemExit('A verified successful checkpoint receipt is required.')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,entry in manifest['code_files'].items():
 if digest(area/'activation-checkpoint/code'/rel)!=entry['sha256']:raise SystemExit('Code checkpoint changed: '+rel)
for rel,entry in manifest['stores'].items():
 if digest(area/'activation-checkpoint/stores'/rel)!=entry['sha256']:raise SystemExit('Store checkpoint changed: '+rel)
changes=[]
for section in ('workbench/ui','workbench/src','workbench/tests','system1/Code/src','system1/Code/tests'):
 for src in (candidate/section).rglob('*'):
  if not src.is_file() or '__pycache__' in src.parts or src.suffix not in {'.py','.js','.mjs','.css','.html'}:continue
  rel=src.relative_to(candidate);target=root/rel
  after=digest(src);before=digest(target) if target.exists() else None
  if before==after:continue
  baseline=manifest['code_files'].get(str(rel))
  if before is not None and baseline is None:raise SystemExit('Existing code lacks rollback copy: '+str(rel))
  if baseline and before!=baseline['sha256']:raise SystemExit('Normal code changed since recovery: '+str(rel))
  changes.append({'path':str(rel),'before':before,'after':after})
if not changes:raise SystemExit('No candidate changes to promote.')
for change in changes:
 target=root/change['path'];target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(candidate/change['path'],target)
 if digest(target)!=change['after']:raise SystemExit('Copied code mismatch: '+change['path'])
result={'status':'copied','version':'ui-redesign-20260914','files':changes,'recovery':'activation-checkpoint; code rollback and stores only, not full historical assets','business_mutations':'none; code/tests only'}
(area/'promotion.json').write_text(json.dumps(result,indent=2));print('Promoted code/test files:',len(changes))
