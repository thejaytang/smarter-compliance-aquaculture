"""Full current System2 tests with temporary runtime/caches outside business data."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from importlib.metadata import distributions
import json,os,platform,shutil,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];SYSTEM=ROOT/'system2'
def hashfile(p):return sha256(p.read_bytes()).hexdigest()
def fingerprint():
 paths=[p for directory in ['src','tests','config'] for p in (SYSTEM/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
 paths += [SYSTEM/'pyproject.toml',SYSTEM/'uv.lock']
 return {str(p.relative_to(SYSTEM)):hashfile(p) for p in sorted(paths)}
def save(name,data):
 with (OUT/name).open('x') as f:json.dump(data,f,indent=2)
assert not (OUT/'run-start.json').exists(),'preserve existing run'
task_tmp=Path(tempfile.mkdtemp(prefix='smarter-system2-regression-',dir='/private/tmp'))
for d in ['tmp','cache','runtime']: (task_tmp/d).mkdir()
# A few contract tests resolve config relative to cwd. Copy rather than link so
# any unexpected test write remains isolated. Tests/source retain original paths.
shutil.copytree(SYSTEM/'config',task_tmp/'config')
env=dict(os.environ)
overrides={'PYTHONPATH':str(SYSTEM/'src'),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(task_tmp/'tmp'),'XDG_CACHE_HOME':str(task_tmp/'cache'),'MPLCONFIGDIR':str(task_tmp/'cache/matplotlib'),'HF_HOME':str(task_tmp/'cache/huggingface'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PADDLE_PDX_CACHE_HOME':str(task_tmp/'cache/paddlex'),'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True'}
env.update(overrides)
cmd=[str(SYSTEM/'.venv/bin/python'),'-m','pytest','-c',str(SYSTEM/'pyproject.toml'),str(SYSTEM/'tests'),'--basetemp',str(task_tmp/'pytest'),'--junitxml',str(OUT/'junit.xml'),'-o',f'cache_dir={task_tmp}/pytest-cache','-ra']
before=fingerprint();gold_before={str(p.relative_to(SYSTEM)):hashfile(p) for p in (SYSTEM/'gold').rglob('*') if p.is_file()}
start={'started_at':datetime.now(timezone.utc).isoformat(),'command':cmd,'cwd':str(task_tmp),'test_temp_root':str(task_tmp),'environment_overrides':overrides,'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'source_and_tests':before,'gold':gold_before,'installed_distributions':sorted([{'name':d.metadata.get('Name'),'version':d.version} for d in distributions()],key=lambda d:(d['name'] or '').lower()),'boundary':'No Gold rebuilding, full benchmark or business service launch. API default import database is isolated by cwd. Existing relative config tests use an unmodified isolated copy.'}
save('run-start.json',start);print('Started full System2 tests:',task_tmp,flush=True)
began=time.monotonic()
with (OUT/'pytest.log').open('x') as log:
 try:
  result=subprocess.run(cmd,cwd=task_tmp,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
  exit_code=result.returncode;status='completed'
 except subprocess.TimeoutExpired:exit_code=None;status='operational_timeout'
after=fingerprint();gold_after={str(p.relative_to(SYSTEM)):hashfile(p) for p in (SYSTEM/'gold').rglob('*') if p.is_file()}
save('run-result.json',{'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-began,'exit_code':exit_code,'status':status,'source_test_config_unchanged':after==before,'changed_files':[k for k in set(before)|set(after) if before.get(k)!=after.get(k)],'gold_unchanged':gold_before==gold_after,'temporary_runtime_files':[str(p.relative_to(task_tmp)) for p in (task_tmp/'runtime').rglob('*') if p.is_file()],'log_sha256':hashfile(OUT/'pytest.log')})
print((OUT/'run-result.json').read_text(),flush=True)
