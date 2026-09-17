from pathlib import Path
import subprocess,json,os,time,hashlib,shutil
from concurrent.futures import ThreadPoolExecutor
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2'
out=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic';out.mkdir(exist_ok=False)
record=json.loads((out.parent/'run-start.json').read_text());snap=out/'frozen-relevant-code';snap.mkdir()
for rel in ['src/pdf_extraction/api/app.py','src/pdf_extraction/parsers/table.py','tests/integration/test_scheme2.py','tests/integration/test_scheme3.py']:
 b=(s/rel).read_bytes();assert hashlib.sha256(b).hexdigest()==record['source_and_tests'][rel],rel
 target=snap/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
paths=[s/'.venv/lib/python3.12/site-packages/numba/experimental/jitclass/base.py',s/'ui/review.html']
def probe(p):
 cmd=[str(s/'.venv/bin/python'),'-c','from pathlib import Path;import sys,hashlib; b=Path(sys.argv[1]).read_bytes(); print(len(b),hashlib.sha256(b).hexdigest())',str(p)]
 result={'file':str(p),'command':cmd,'metadata_before':subprocess.check_output(['ls','-lO',str(p)],text=True)};t=time.monotonic()
 try:
  proc=subprocess.run(cmd,cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=20)
  result.update(returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)
 except subprocess.TimeoutExpired as exc:result.update(status='diagnostic_read_timeout_20s',stdout=str(exc.stdout or ''),stderr=str(exc.stderr or ''))
 result['elapsed_seconds']=time.monotonic()-t
 return result
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(probe,paths))
(out/'read-probes.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
