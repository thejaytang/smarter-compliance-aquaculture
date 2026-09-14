from pathlib import Path
import subprocess, os, tempfile, json, hashlib, time
root=Path(__file__).resolve().parents[4]
out=Path(__file__).resolve().parent
sandbox=Path(tempfile.mkdtemp(prefix='smarter-reader-resolution-',dir='/private/tmp'))
files=['system2/src/pdf_extraction/evidence/material_reader.py','workbench/src/local_workbench/server.py','system2/tests/test_material_reader_resolution.py','workbench/tests/test_material_http.py','system2/src/pdf_extraction/orchestration/material_parser.py']
def hashes():return {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
pre=hashes(); runs=[]
commands=[('system2',[str(root/'system2/.venv/bin/python'),'-m','pytest',str(root/'system2/tests/test_material_reader_resolution.py'),str(root/'system2/tests/test_material_reader_navigation.py'),str(root/'system2/tests/test_material_reader_parser.py'),str(root/'system2/tests/test_material_read_performance.py'),'-q','--basetemp='+str(sandbox/'pytest'),'--junitxml='+str(out/'system2-junit.xml')]),('workbench',[str(root/'workbench/.venv/bin/python'),'-m','unittest','discover','-s',str(root/'workbench/tests'),'-p','test_material_http.py','-v'])]
(out/'start.json').write_text(json.dumps(dict(hashes=pre,temp_root=str(sandbox),commands=commands),indent=2))
for name,cmd in commands:
 env=dict(os.environ,PYTHONPATH=str(root/name/'src'),TMPDIR=str(sandbox),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
 start=time.monotonic()
 with (out/(name+'.log')).open('w') as log:
  result=subprocess.run(cmd,cwd=sandbox,env=env,stdout=log,stderr=subprocess.STDOUT)
 receipt=dict(name=name,exit_code=result.returncode,seconds=time.monotonic()-start)
 runs.append(receipt);print(json.dumps(receipt),flush=True)
(out/'receipt.json').write_text(json.dumps(dict(runs=runs,before=pre,after=hashes(),temp_root=str(sandbox)),indent=2))
