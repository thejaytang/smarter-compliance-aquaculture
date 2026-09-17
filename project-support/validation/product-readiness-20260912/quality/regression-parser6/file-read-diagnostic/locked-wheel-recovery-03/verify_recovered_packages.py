from pathlib import Path
import csv,hashlib,base64,json,time
s=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side/system2');site=s/'.venv/lib/python3.12/site-packages';out=s.parent/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic/locked-wheel-recovery-03';result={'scope':'All installed RECORD-listed package files in only numba, anyio, img2table, excludes dist-info and pyc not present in RECORD','packages':[]};started=time.monotonic()
for name,ver in [('numba','0.67.0'),('anyio','4.14.2'),('img2table','1.4.0')]:
 rows=list(csv.reader((site/f'{name}-{ver}.dist-info/RECORD').open()));item={'name':name,'version':ver,'total':0,'verified':0,'errors':[]};result['packages'].append(item)
 for rel,expected,size in rows:
  if not rel.startswith(name+'/'):continue
  item['total']+=1
  try:
   b=(site/rel).read_bytes();actual='sha256='+base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=')
   if actual!=expected or len(b)!=int(size):item['errors'].append({'file':rel,'error':'RECORD mismatch','actual':actual,'expected':expected});continue
   item['verified']+=1
  except Exception as exc:item['errors'].append({'file':rel,'error':repr(exc)})
result.update(elapsed_seconds=time.monotonic()-started,status='PASS' if all(p['verified']==p['total'] for p in result['packages']) else 'FAIL',whole_environment_health='NOT_ESTABLISHED')
(out/'installed-file-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
