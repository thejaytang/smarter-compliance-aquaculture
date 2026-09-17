from pathlib import Path
import csv,json,hashlib,base64,zipfile,os,stat
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';out=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic'
site=s/'.venv/lib/python3.12/site-packages';cache=s/'.cache/uv/archive-v0'
result={'dependency_candidates':[],'retained_code_archives':[]}
for pkg,ver,archive,rel in [('numba','0.67.0','MrQ8NgSexFT7SKibQc9qm','numba/experimental/jitclass/base.py'),('anyio','4.14.2','wUoq0ukKkZOYXHqL9xX7h','anyio/streams/memory.py')]:
 record=site/f'{pkg}-{ver}.dist-info/RECORD';rows={r[0]:r[1:] for r in csv.reader(record.open())};p=cache/archive/rel;b=p.read_bytes();actual=base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=');expected=rows[rel][0]
 cache_record=cache/archive/f'{pkg}-{ver}.dist-info/RECORD'
 try: cache_rows={r[0]:r[1:] for r in csv.reader(cache_record.open())};cache_record_error=None
 except OSError as e: cache_rows={};cache_record_error=repr(e)
 files=list((cache/archive/pkg).rglob('*'));dataless=[str(x.relative_to(cache/archive)) for x in files if x.is_file() and x.stat().st_flags & 0x40000000]
 result['dependency_candidates'].append({'package':pkg,'version':ver,'source':str(p),'target':str(site/rel),'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'record_hash':expected,'matches_installed_RECORD':expected=='sha256='+actual,'matches_cache_RECORD':cache_rows.get(rel,[None])[0]==expected,'cache_RECORD_error':cache_record_error,'source_archive':str(cache/archive),'package_file_count':sum(x.is_file() for x in files),'dataless_files_in_cache_package':dataless})
for p in sorted((root/'docs/reports/offline-collaboration-20260912').glob('*code*.zip')):
 try:
  with zipfile.ZipFile(p) as z:
   names=[n for n in z.namelist() if n.endswith('system2/ui/review.html') or n.endswith('system2/ui/review.css')]
   entries=[{'entry':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'size':len(z.read(n))} for n in names]
   result['retained_code_archives'].append({'archive':str(p),'entries':entries})
 except Exception as e:result['retained_code_archives'].append({'archive':str(p),'error':repr(e)})
(out/'recovery-source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
