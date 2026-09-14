from pathlib import Path
import json,os,subprocess,hashlib,time,shutil,xml.etree.ElementTree as E
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';out=root/'project-support/product-readiness-20260912/quality/regression-parser6/targeted-recovery-02';out.mkdir(exist_ok=False)
for name in ['cwd','tmp','cache']: (out/name).mkdir()
shutil.copytree(s/'config',out/'cwd/config')
relevant=['src/pdf_extraction/api/app.py','src/pdf_extraction/parsers/table.py','tests/integration/test_scheme2.py','tests/integration/test_scheme3.py']
def fp():return {rel:hashlib.sha256((s/rel).read_bytes()).hexdigest() for rel in relevant}
before=fp();old=json.loads((out.parent/'run-start.json').read_text());assert all(before[k]==old['source_and_tests'][k] for k in relevant)
paths=[str(s/'tests/integration/test_scheme2.py')+'::test_links_notes_and_real_img2table_route']
cmd=[str(s/'.venv/bin/python'),'-m','pytest','-c',str(s/'pyproject.toml'),'-o','addopts=','-vv','-p','no:cacheprovider','--basetemp='+str(out/'tmp/pytest'),'--junitxml='+str(out/'junit.xml'),*paths]
overrides={'PYTHONPATH':str(s/'src'),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(out/'tmp'),'XDG_CACHE_HOME':str(out/'cache'),'MPLCONFIGDIR':str(out/'cache/matplotlib'),'HF_HOME':str(out/'cache/huggingface'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PADDLE_PDX_CACHE_HOME':str(out/'cache/paddlex'),'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True'}
result={'command':cmd,'cwd':str(out/'cwd'),'environment_overrides':overrides,'relevant_code_before':before,'scope':'Only the original img2table failure after 907/907 three-package RECORD verification; legacy page remains unavailable, full suite remains FAIL.'}
(out/'invocation.json').write_text(json.dumps(result,indent=2)+'\n');start=time.monotonic()
with (out/'pytest.log').open('w') as log:
 try:p=subprocess.run(cmd,cwd=out/'cwd',env=dict(os.environ,**overrides),stdout=log,stderr=subprocess.STDOUT,timeout=500);rc=p.returncode
 except subprocess.TimeoutExpired:rc=None
result.update(returncode=rc,elapsed_seconds=time.monotonic()-start,relevant_code_after=fp())
result['relevant_code_unchanged']=result['relevant_code_before']==result['relevant_code_after']
if (out/'junit.xml').exists():
 suites=E.parse(out/'junit.xml').getroot().findall('testsuite');result.update({k:sum(int(x.get(a,0)) for x in suites) for k,a in [('tests','tests'),('failures','failures'),('errors','errors'),('skips','skipped')]})
result['status']='PASS_TARGET_ONLY' if rc==0 and result['relevant_code_unchanged'] else 'FAIL'
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
