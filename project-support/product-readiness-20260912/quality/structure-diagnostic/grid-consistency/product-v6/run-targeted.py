from pathlib import Path
from hashlib import sha256
import subprocess,os,sys,time,json,tempfile
ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;TMP=Path(tempfile.mkdtemp(prefix='smarter-parser-v6-tests-',dir='/private/tmp'))
files=sorted((ROOT/'system2/tests').glob('test_material*.py'))
cmd=[str(ROOT/'system2/.venv/bin/python'),'-m','pytest',*[str(p) for p in files],'-q','--basetemp='+str(TMP/'pytest'),'--junitxml='+str(HERE/'targeted-junit.xml'),'-o','cache_dir='+str(TMP/'cache')]
env=dict(os.environ,PYTHONPATH=str(ROOT/'system2/src'),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(TMP),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(TMP/'hf'),XDG_CACHE_HOME=str(TMP/'xdg'))
hashf=lambda p:sha256(p.read_bytes()).hexdigest()
freeze={'command':cmd,'cwd':str(TMP),'code_sha256':hashf(ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py'),'test_sha256':{str(p.relative_to(ROOT)):hashf(p) for p in files},'environment':{k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE','TMPDIR','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HOME','XDG_CACHE_HOME']}}
with (HERE/'targeted-start.json').open('x') as f:json.dump(freeze,f,indent=2)
start=time.monotonic()
with (HERE/'targeted.log').open('x') as log:r=subprocess.run(cmd,cwd=TMP,env=env,stdout=log,stderr=subprocess.STDOUT)
receipt={'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'parser_unchanged':hashf(ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py')==freeze['code_sha256']}
with (HERE/'targeted-receipt.json').open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt));print((HERE/'targeted.log').read_text()[-7000:]);raise SystemExit(r.returncode)
