"""Build the explicitly authorized one-time handoff; no Materials or credentials."""
from pathlib import Path
import hashlib,json,sqlite3,zipfile
from local_workbench.recovery import digest
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'project-support/shared-workspace-20260917/local-delivery'
OUT.mkdir(exist_ok=True)
files={}
for rel in ('system1/Code/runtime/governance.sqlite','workbench/runtime/workbench.sqlite'):
 p=ROOT/rel;out=OUT/Path(rel).name
 with sqlite3.connect(p) as src,sqlite3.connect(out) as dst:src.backup(dst)
 files[rel]=out
# Initial package contains saved source drafts, never old login sessions.
with sqlite3.connect(files['workbench/runtime/workbench.sqlite']) as db:
 db.execute('DELETE FROM sessions')
 assert db.execute('SELECT COUNT(*) FROM requirement_sessions').fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM requirement_interpretations').fetchone()[0]==0
 assert db.execute("SELECT COUNT(*) FROM collaboration_objects WHERE kind='workspace'").fetchone()[0]==0
for rel in ('system1/Code/runtime/governance-migration-input.xlsx','system1/Requirement_Source_Registry.xlsx'):
 files[rel]=ROOT/rel
# The selected holds package was verified against live human holds; omit machine result caches.
with zipfile.ZipFile(ROOT/'system1/saved-records/governance-20260916-r8.zip') as z:
 p=OUT/'source-assessments.sqlite';p.write_bytes(z.read('logs/source-assessments.sqlite'))
 files['system1/Code/runtime/logs/source-assessments.sqlite']=p
for p in (ROOT/'system1/Data').rglob('*'):
 if p.is_file() and p.name!='.DS_Store':files[p.relative_to(ROOT).as_posix()]=p
with sqlite3.connect(files['system1/Code/runtime/governance.sqlite']) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert not db.execute('PRAGMA foreign_key_check').fetchall()
 revision=db.execute('SELECT revision FROM state').fetchone()[0]
 state=db.execute('SELECT import_sha256,archive FROM state').fetchone()
 assert digest(ROOT/'system1/Code/runtime'/state[1])==state[0]
 # Owning manifest stores both active and previous immutable source bindings.
 for rel,sha in db.execute('SELECT path,sha256 FROM source_versions'):
  assert digest(ROOT/'system1/Data'/rel)==sha,rel
manifest=dict(schema='source-initial-data/1',source_revision=revision,materials=0,requirements=0,interpretations=0,files={rel:dict(sha256=digest(p),bytes=p.stat().st_size) for rel,p in sorted(files.items())})
zip_path=OUT/'source-initial-data-20260917.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for rel,p in sorted(files.items()):z.write(p,rel)
 z.writestr('manifest.json',json.dumps(manifest,indent=2))
checksum=digest(zip_path)
(zip_path.with_suffix('.zip.sha256')).write_text(checksum+'  '+zip_path.name+'\n')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(dict(file=str(zip_path),sha256=checksum,source_revision=revision,files=len(files),bytes=zip_path.stat().st_size)))
