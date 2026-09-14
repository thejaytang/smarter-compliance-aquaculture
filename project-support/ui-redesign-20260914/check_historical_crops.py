from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2];area=Path(__file__).resolve().parent
rel=Path('artifacts/ecd506cd90695697577fcca2065a0a49/attempt-43/native')
current=root/'system2/runtime/workflow'/rel
copies=[root/'workbench/runtime/acceptance-stage-v2'/part/'system2-workflow'/rel for part in ('full-current08','full')]
def read(p):
 with p.open('rb') as f:return f.read(p.stat().st_size)
canon=[read(p/'canonical.json') for p in [current,*copies]]
assert canon[0]==canon[1]==canon[2] and len(canon[0])==440838
items=[]
for p in sorted((current/'crops').glob('p0127_*.png')):
 data=read(p)
 if len(data)==p.stat().st_size:continue
 paths=[base/'crops'/p.name for base in copies]
 saved=[read(copy) for copy in paths]
 valid=saved[0]==saved[1] and len(saved[0])==p.stat().st_size and len(saved[0])>0
 items.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'read_bytes':len(data),'matching_copies':valid,'sha256':hashlib.sha256(saved[0]).hexdigest() if valid else None})
(area/'historical-crop-read-check.json').write_text(json.dumps(items,indent=2))
print('Unreadable page-127 crops:',len(items),'matching complete dual copies:',sum(i['matching_copies'] for i in items))
