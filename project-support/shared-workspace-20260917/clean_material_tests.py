"""One-off, explicitly authorized development cleanup; never run during updates."""
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
from local_workbench.recovery import layout, quiescent

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'project-support/shared-workspace-20260917/local-backup'

def signature(db):
 result={}
 for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
  rows=db.execute('SELECT * FROM "'+table+'"').fetchall()
  result[table]=dict(count=len(rows),sha256=hashlib.sha256(repr(sorted(rows,key=repr)).encode()).hexdigest())
 return result

def main():
 if DEST.exists():raise RuntimeError('Backup already exists; this cleanup cannot be repeated blindly.')
 info=layout(ROOT);DEST.mkdir(parents=True)
 report={'status':'incomplete','backup':str(DEST),'removed_tables':{},'removed_objects':[],'moved':[]}
 with quiescent(ROOT,info):
  for path in info['stores']:
   target=DEST/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
   with sqlite3.connect(path) as source,sqlite3.connect(target) as out:
    source.backup(out)
    assert out.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not out.execute('PRAGMA foreign_key_check').fetchall()
  with sqlite3.connect(info['stores'][0]) as db:report['source_before']=signature(db)
  with sqlite3.connect(info['stores'][1]) as db:report['assessments_before']=signature(db)
  # Inspect backup and retain exact source-review/draft bytes before releasing reservations.
  with sqlite3.connect(DEST/'workbench/runtime/workbench.sqlite') as db:
   report['workbench_before']=signature(db)
  (DEST/'manifest.json').write_text(json.dumps(report,indent=2))
 # No service is active. The owning SQLite transaction protects the shared store.
 with sqlite3.connect(ROOT/'workbench/runtime/workbench.sqlite') as db:
  db.execute('PRAGMA foreign_keys=OFF');db.execute('BEGIN IMMEDIATE')
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0].startswith(('requirement_','interpretation_'))]
  for t in tables:
   report['removed_tables'][t]=db.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]
   db.execute('DELETE FROM "'+t+'"')
  remove={'workspace','retired_test_workspace','material_list_preferences','baseline','merge','submission','adoption_receipt','material_inspection','collection_adoption','received_adoption'}
  for kind,key,raw in db.execute('SELECT kind,key,data FROM collaboration_objects').fetchall():
   data=json.loads(raw)
   material_request=kind=='request_binding' and not str(data.get('operation','')).startswith('source')
   if kind in remove or kind.startswith('sync_') or material_request:
    report['removed_objects'].append({'kind':kind,'key':key});db.execute('DELETE FROM collaboration_objects WHERE kind=? AND key=?',(kind,key))
  assert not db.execute('PRAGMA foreign_key_check').fetchall()
  report['workbench_after']=signature(db)
  for t in ('actors','drafts','requests','review_policies'):
   assert report['workbench_before'][t]==report['workbench_after'][t],t
 # Quarantine old material files so the normal app/export cannot load them again.
 for rel in ('system2/runtime/workflow','system2/runtime/jobs.sqlite3','system2/runtime/jobs.sqlite3-wal','system2/runtime/jobs.sqlite3-shm','workbench/runtime/collaboration/personal','workbench/runtime/collaboration/snapshot-files','workbench/runtime/collaboration/exports','workbench/runtime/collaboration/imports'):
  p=ROOT/rel
  if p.exists():
   target=DEST/'retired-files'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(p),str(target));report['moved'].append(rel)
 with sqlite3.connect(info['stores'][0]) as db:report['source_after']=signature(db)
 with sqlite3.connect(info['stores'][1]) as db:report['assessments_after']=signature(db)
 assert report['source_before']==report['source_after']
 assert report['assessments_before']==report['assessments_after']
 report['status']='complete'
 (DEST/'manifest.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({'status':report['status'],'source_unchanged':True,'assessment_holds_unchanged':True,'requirement_sessions_removed':report['removed_tables'].get('requirement_sessions'),'interpretations_removed':report['removed_tables'].get('requirement_interpretations'),'backup':str(DEST)},indent=2))

if __name__=='__main__':main()
