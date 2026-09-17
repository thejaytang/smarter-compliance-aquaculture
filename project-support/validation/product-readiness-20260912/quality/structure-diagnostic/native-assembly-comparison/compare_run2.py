"""One isolated DEV comparison; original parser/backend configuration stays frozen."""
from pathlib import Path
from hashlib import sha256
from importlib.metadata import version
from datetime import datetime,timezone
from copy import deepcopy
import json,os,subprocess,sys,tempfile,time,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];Q=HERE.parents[1];SYS=ROOT/'system2';OUT=HERE/'run-2'
read=lambda p:json.loads(p.read_text());norm=lambda t:' '.join(t.split())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def save(path,data):
 with path.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
def adapter(backend):
 if backend=='pdfium':
  import pdf_extraction.orchestration.material_parser as module
  return module
 source=(OUT/'docling_experiment.py').read_text()
 module=types.ModuleType('pdf_extraction.orchestration.material_parser_native_experiment')
 module.__package__='pdf_extraction.orchestration';module.__file__=str(SYS/'src/pdf_extraction/orchestration/material_parser.py')
 exec(compile(source,str(OUT/'docling_experiment.py'),'exec'),module.__dict__)
 return module
if len(sys.argv)>1 and sys.argv[1]=='worker':
 import faulthandler
 faulthandler.dump_traceback_later(30,repeat=True)
 readiness_start=time.monotonic()
 sid,backend=sys.argv[2:];freeze=read(OUT/'freeze.json');sample=next(s for s in freeze['samples'] if s['id']==sid)
 parser=adapter(backend);path=ROOT/sample['path'];assert digest(path)==sample['sha256']
 import pypdfium2
 import pdf_extraction.layout.detector
 if backend=='docling':
  from docling_parse.pdf_parser import DoclingPdfParser
 module_policy=dict(parser.POLICY);audit=[];original_group=parser._group_pdf_paragraphs
 def checked_group(blocks,*args,**kwargs):
  before=deepcopy(blocks);after,ops=original_group(blocks,*args,**kwargs);lookup={o['group_block_id']:o['fragments'] for o in ops}
  reconstructed=[m for b in after for m in lookup.get(b['id'],[b])]
  audit.append({'before':before,'after':after,'fragment_payload_order_exact':reconstructed==before,'input_unmodified':blocks==before,'group_text_exact':all(b['text']=='\n'.join(m['text'] for m in lookup[b['id']]) for b in after if b['id'] in lookup),'group_refs_exact':all(b['source_refs']==[r for m in lookup[b['id']] for r in m['source_refs']] for b in after if b['id'] in lookup)})
  return after,ops
 parser._group_pdf_paragraphs=checked_group
 source=dict(source_id=sample['engineering_source_id'],snapshot_id=sample['engineering_source_id']+'-001',relative_path=path.name,content_hash=sample['sha256'],file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256=digest(Q/'manifest.json'))
 target=OUT/(sid+'-'+backend)
 ready={'sample':sid,'backend':backend,'stage':'import_ready','readiness_elapsed_seconds':time.monotonic()-readiness_start,'ready_monotonic':time.monotonic(),'ready_utc':datetime.now(timezone.utc).isoformat(),'boundary':'No parser instantiated before readiness; includes adapter/source preparation and dependency imports.'}
 save(OUT/(sid+'-'+backend+'-ready.json'),ready);print(json.dumps(ready),flush=True)
 faulthandler.cancel_dump_traceback_later();faulthandler.dump_traceback_later(20,repeat=True)
 parse_start=time.monotonic()
 result=parser.parse_material(source,path.parent,target,page_indices=sample['page_indices'])
 parse_seconds=time.monotonic()-parse_start
 faulthandler.cancel_dump_traceback_later()
 native=[read(p) for p in sorted(target.glob('pdf-native-*.json'))]
 expected='docling-parse' if backend=='docling' else 'pypdfium2'
 actual={e['backend'] for e in native}
 assert all(('docling' in n if backend=='docling' else 'pdfium' in n) for n in actual),actual
 assert all(e['material_backend_policy']==('docling-parse' if backend=='docling' else 'pdfium') for e in native)
 if backend=='docling':assert all('positioned PDFium parser' not in w for w in result['warnings'])
 from pdf_extraction.review.materials import validate_blocks
 validate_blocks(result['blocks'],result['scope'])
 save(target/'assembly-audit.json',audit)
 save(target/'experiment-provenance.json',{'actual_native_backends':sorted(actual),'module_policy':module_policy,'config_hash':parser.CONFIG_HASH,'parser_version':parser.VERSION,'production_parser_hash':freeze['code']['material_parser.py'],'experimental_source_hash':digest(OUT/'docling_experiment.py') if backend=='docling' else None,'installed_docling_package_used':backend=='docling','business_adoption':False,'all_group_invariants':all(all(a[k] for k in ['fragment_payload_order_exact','input_unmodified','group_text_exact','group_refs_exact']) for a in audit)})
 print(json.dumps({'sample':sid,'backend':backend,'actual_native_backends':sorted(actual),'blocks':len(result['blocks']),'status':result['status'],'parse_elapsed_seconds':parse_seconds}),flush=True)
 raise SystemExit(0)
OUT.mkdir(exist_ok=False)
OLD=HERE/'run-1'
# Preserve the exact original source/annotation/denominator/policy freeze bytes.
for name in ['freeze.json','docling_experiment.py']:
 with (OUT/name).open('xb') as f:f.write((OLD/name).read_bytes())
freeze=read(OUT/'freeze.json');samples=freeze['samples'];source_path=SYS/'src/pdf_extraction/orchestration/material_parser.py';code=freeze['code']
assert digest(source_path)==code['material_parser.py']
assert digest(SYS/'src/pdf_extraction/ingest/native_extractor.py')==code['native_extractor.py']
for config in ['pdf-intake-positioned.yaml']:
 assert digest(SYS/'config'/config)==code[config]
for package in ['pyproject.toml','uv.lock']:
 assert digest(SYS/package)==code[package]
for sample in samples:
 assert digest(ROOT/sample['path'])==sample['sha256']
 assert digest(ROOT/sample['annotation']['path'])==sample['annotation']['sha256']
assert digest(Q/'structure-diagnostic/relation-subset-before.json')==freeze['relation_subset_hash']
assert version('docling-parse')==freeze['dependencies']['docling-parse']
assert version('pypdfium2')==freeze['dependencies']['pypdfium2']
tmp=Path(tempfile.mkdtemp(prefix='smarter-native-compare-run2-',dir='/private/tmp'))
env=dict(os.environ,PYTHONPATH=str(SYS/'src'),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),XDG_CACHE_HOME=str(tmp/'cache'),NUMBA_CACHE_DIR=str(tmp/'cache/numba'),HF_HOME=str(tmp/'hf'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
save(OUT/'resumption.json',{'started_at':datetime.now(timezone.utc).isoformat(),'original_freeze_sha256':digest(OLD/'freeze.json'),'copied_freeze_sha256':digest(OUT/'freeze.json'),'resumption_runner_sha256':digest(Path(__file__)),'original_experiment_sha256':digest(OLD/'docling_experiment.py'),'copied_experiment_sha256':digest(OUT/'docling_experiment.py'),'import_readiness_guard_seconds':300,'parse_stage_guard_seconds':60,'guards_are':'Operational process guards; not quality thresholds or work-duration targets. Same child is observed until readiness then through parsing. Readiness includes adapter/source preparation.','justification':'Completed actual parser-symbol import-only observation; retain earlier failure.','temporary_root':str(tmp),'environment_overrides':{k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE','TMPDIR','XDG_CACHE_HOME','NUMBA_CACHE_DIR','HF_HOME','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']}})
for sample in samples:
 for backend in ['pdfium','docling']:
  sid=sample['id'];stem=sid+'-'+backend;cmd=[sys.executable,__file__,'worker',sid,backend]
  t=time.monotonic();ready=None;guard=None
  with (OUT/(stem+'-stdout.log')).open('x') as stdout,(OUT/(stem+'-stderr.log')).open('x') as stderr:
   child=subprocess.Popen(cmd,cwd=tmp,env=env,stdout=stdout,stderr=stderr)
   print(json.dumps({'stage':'condition_started','sample':sid,'backend':backend,'owned_child_pid':child.pid}),flush=True)
   while child.poll() is None:
    ready_path=OUT/(stem+'-ready.json')
    if ready is None and ready_path.exists():
     try:ready=read(ready_path)
     except json.JSONDecodeError:pass
     if ready is not None:print(json.dumps(ready),flush=True)
    if ready is None and time.monotonic()-t>300:guard='import_readiness'
    elif ready is not None and time.monotonic()-ready['ready_monotonic']>60:guard='parse'
    if guard:
     child.terminate()
     try:child.wait(timeout=5)
     except subprocess.TimeoutExpired:child.kill();child.wait()
     break
    try:child.wait(timeout=1)
    except subprocess.TimeoutExpired:pass
  if ready is None and (OUT/(stem+'-ready.json')).exists():ready=read(OUT/(stem+'-ready.json'))
  receipt={'command':cmd,'cwd':str(tmp),'elapsed_seconds':time.monotonic()-t,'exit_code':child.returncode,'status':'operational_guard_timeout' if guard else ('completed' if child.returncode==0 else 'failed'),'guard_stage':guard,'readiness':ready,'stdout_log':stem+'-stdout.log','stderr_log':stem+'-stderr.log'}
  save(OUT/(stem+'-receipt.json'),receipt);print(json.dumps(receipt),flush=True)
  if child.returncode!=0 or guard:
   save(OUT/'STOPPED.json',{'reason':'New failure retained; no retry, resource repair or product edit.','sample':sid,'backend':backend,'receipt':stem+'-receipt.json'})
   raise SystemExit(1)
save(OUT/'preservation.json',{'production_parser_unchanged':digest(source_path)==code['material_parser.py'],'originals_unchanged':all(digest(ROOT/s['path'])==s['sha256'] for s in samples),'annotations_unchanged':all(digest(ROOT/s['annotation']['path'])==s['annotation']['sha256'] for s in samples),'freeze_unchanged':digest(OUT/'freeze.json')==digest(OLD/'freeze.json'),'temporary_root':str(tmp)})
