from pathlib import Path
import sys,json
area=Path(__file__).resolve().parent
root=area.parents[1]
sys.path.insert(0,str(area/'candidate/workbench/src'))
from local_workbench import recovery
original=recovery.digest
count=0
restored_count=0
def progress(path):
 global count,restored_count
 try:result=original(path)
 except OSError as error:
  if not str(error).startswith('Incomplete recovery resource:') or restored_count>=10:raise
  from restore_verified_crop import restore
  restored=restore(path);restored_count+=1
  print('Restored hash-bound historical crop:',restored,flush=True)
  result=original(path)
 count+=1
 if count%1000==0:print('Verified resource reads:',count,flush=True)
 return result
recovery.digest=progress
result=recovery.backup(root,area/'pre-activation-recovery')
print(json.dumps(result),flush=True)
