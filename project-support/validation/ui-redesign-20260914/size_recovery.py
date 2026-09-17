from pathlib import Path
import sys,json,sqlite3
from contextlib import closing
area=Path(__file__).resolve().parent;root=area.parents[1]
sys.path.insert(0,str(area/'candidate/workbench/src'))
from local_workbench.recovery import layout,file_references,quote,source_inventory
info=layout(root)
files=set(info['stores'])|{info['config'],info['companion'],info['workbook']}
for directory in [info['source'],info['logs'],root/'workbench/runtime/uploads',root/'workbench/runtime/collaboration',root/'system2/runtime/workflow/material-originals',root/'system2/runtime/workflow/material-artifacts']:
 if directory.exists():files.update(p for p in directory.rglob('*') if p.is_file())
for directory in (root/'system1/Code/runtime',root/'workbench/runtime',root/'system2/runtime/workflow'):
 files.update(p for p in directory.glob('*') if p.is_file() and not p.name.endswith(('-wal','-shm','.lock','.tmp')))
for path in info['stores']:
 with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
  for table in tables:
   for row in db.execute('SELECT * FROM '+quote(table)):
    for value in row:
     if not isinstance(value,str):continue
     try:decoded=json.loads(value)
     except ValueError:decoded=value
     files.update(ref for ref in file_references(decoded) if ref.is_relative_to(root) and ref.is_file())
  if path.name=='workflow.sqlite' and 'documents' in tables:
   for payload, in db.execute('SELECT data FROM documents'):
    for entry in json.loads(payload).get('canonical',[]):
     ref=Path(entry['path']);files.update(p for p in ref.parent.rglob('*') if p.is_file())
files={p.resolve() for p in files if p.name not in {'server.json','listen-port.json'} and not p.name.endswith(('-wal','-shm','.lock','.tmp'))}
code=source_inventory(root)
size=sum(p.stat().st_size for p in files);code_size=sum(p.stat().st_size for p in code)
import shutil
free=shutil.disk_usage(root).free
report={'scope':'read-only metadata projection of exact backup inventory; no hash bypass used for a backup','files':len(files),'business_bytes':size,'code_bytes':code_size,'total_bytes':size+code_size,'free_bytes':free,'free_after_copy_bytes':free-size-code_size,'largest_files':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size} for p in sorted(files,key=lambda p:p.stat().st_size,reverse=True)[:5]]}
(area/'recovery-size.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
