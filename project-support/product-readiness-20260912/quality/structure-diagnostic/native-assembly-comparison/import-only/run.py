"""One guarded observation of imports, preserving prior parsing failure."""
from pathlib import Path
import sys,os,json,hashlib,subprocess,tempfile,time,datetime
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
PYTHON=ROOT/'system2/.venv/bin/python'
SCRIPT=HERE/'observe_import.py'
TEMP=Path(tempfile.mkdtemp(prefix='smarter-docling-import-'))
ENV=os.environ.copy()
ENV.update({'PYTHONPATH':str(ROOT/'system2/src'),'TMPDIR':str(TEMP),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HOME':str(TEMP/'hf'),'XDG_CACHE_HOME':str(TEMP/'cache'),'PYTHONDONTWRITEBYTECODE':'1'})
COMMAND=[str(PYTHON),'-X','importtime',str(SCRIPT)]
FILES=[SCRIPT,Path(__file__).resolve(),ROOT/'system2/pyproject.toml',ROOT/'system2/uv.lock',ROOT/'system2/config/requirements.yaml',ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py',ROOT/'system2/src/pdf_extraction/ingest/native_extractor.py',ROOT/'system2/.venv/pyvenv.cfg',ROOT/'system2/.venv/lib/python3.12/site-packages/docling_parse/__init__.py',ROOT/'system2/.venv/lib/python3.12/site-packages/docling_parse/pdf_parser.py']
FILES=[p for p in FILES if p.exists()]
freeze={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':COMMAND,'cwd':str(TEMP),'guard_seconds':300,'snapshot_seconds':30,'environment_overrides':{k:ENV[k] for k in ['PYTHONPATH','TMPDIR','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HOME','XDG_CACHE_HOME','PYTHONDONTWRITEBYTECODE']},'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES},'boundary':'Import actual docling_parse.pdf_parser symbol only; no instantiation, PDF read, parse, API app, model, binary copy, environment repair or package installation.'}
with (HERE/'freeze.json').open('x') as f:json.dump(freeze,f,indent=2)
start=time.monotonic()
with (HERE/'stdout.log').open('x') as stdout,(HERE/'importtime-and-stacks.log').open('x') as stderr:
    child=subprocess.Popen(COMMAND,cwd=TEMP,env=ENV,stdout=stdout,stderr=stderr)
    print(json.dumps({'stage':'started','owned_child_pid':child.pid,'temp':str(TEMP)}),flush=True)
    try:
        code=child.wait(timeout=300)
        result={'status':'completed' if code==0 else 'failed','exit_code':code}
    except subprocess.TimeoutExpired:
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill();child.wait()
        result={'status':'operational_guard_timeout','exit_code':child.returncode}
result.update({'elapsed_seconds':time.monotonic()-start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'code_hashes_unchanged':all(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==freeze['files'][str(p.relative_to(ROOT))] for p in FILES)})
with (HERE/'receipt.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result),flush=True)
