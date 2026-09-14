from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import os,sys,json,subprocess,tempfile,time,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5];Q=HERE.parents[2];OUT=HERE/'outputs'
read=lambda p:json.loads(p.read_text());hashf=lambda p:sha256(p.read_bytes()).hexdigest()
def save(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
if len(sys.argv)>1:
 import faulthandler
 faulthandler.dump_traceback_later(30,repeat=True)
 started=time.monotonic();sid=sys.argv[1];freeze=read(OUT/'freeze.json');sample=next(s for s in freeze['samples'] if s['id']==sid)
 source=(HERE/'material_experiment.py').read_text();module=types.ModuleType('pdf_extraction.orchestration.pdfium_granularity_experiment')
 module.__file__=str(ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py');module.__package__='pdf_extraction.orchestration'
 exec(compile(source,str(HERE/'material_experiment.py'),'exec'),module.__dict__)
 import rich_native
 import pdf_extraction.layout.detector
 audits=[];oldgroup=module._group_pdf_paragraphs
 def checked_group(blocks,*args,**kwargs):
  before=deepcopy(blocks);after,ops=oldgroup(blocks,*args,**kwargs);lookup={o['group_block_id']:o['fragments'] for o in ops}
  reconstructed=[m for b in after for m in lookup.get(b['id'],[b])]
  audits.append({'before':before,'after':after,'fragment_payload_order_exact':reconstructed==before,'input_unmodified':blocks==before,'group_text_exact':all(b['text']=='\n'.join(m['text'] for m in lookup[b['id']]) for b in after if b['id'] in lookup),'group_refs_exact':all(b['source_refs']==[r for m in lookup[b['id']] for r in m['source_refs']] for b in after if b['id'] in lookup)})
  return after,ops
 module._group_pdf_paragraphs=checked_group
 path=ROOT/sample['path'];assert hashf(path)==sample['sha256']
 governed=dict(source_id=sample['engineering_source_id'],snapshot_id=sample['engineering_source_id']+'-001',relative_path=path.name,content_hash=sample['sha256'],file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256=hashf(Q/'manifest.json'))
 ready={'stage':'ready','readiness_seconds':time.monotonic()-started,'ready_monotonic':time.monotonic()};save(OUT/(sid+'-ready.json'),ready);print(json.dumps(ready),flush=True)
 faulthandler.cancel_dump_traceback_later();faulthandler.dump_traceback_later(20,repeat=True);parse_start=time.monotonic()
 target=OUT/sid;candidate=module.parse_material(governed,path.parent,target,page_indices=sample['page_indices']);elapsed=time.monotonic()-parse_start
 faulthandler.cancel_dump_traceback_later()
 from pdf_extraction.review.materials import validate_blocks
 validate_blocks(candidate['blocks'],candidate['scope'])
 native=[read(p) for p in sorted(target.glob('pdf-native-*.json'))];assert all(n['backend']=='pypdfium2' for n in native)
 assert not any(k.startswith('docling') for k in sys.modules)
 save(target/'assembly-audit.json',audits)
 save(target/'experiment-provenance.json',{'actual_native_backends':['pypdfium2'],'module_policy':module.POLICY,'config_hash':module.CONFIG_HASH,'parser_version':module.VERSION,'production_parser_hash':freeze['code']['material_parser.py'],'experimental_source_hash':hashf(HERE/'material_experiment.py'),'native_generator':rich_native.VERSION,'native_generator_sha256':rich_native.SOURCE_SHA256,'all_group_invariants':all(all(a[k] for k in ['fragment_payload_order_exact','input_unmodified','group_text_exact','group_refs_exact']) for a in audits),'business_adoption':False,'docling_imported':False})
 print(json.dumps({'sample':sid,'parse_seconds':elapsed,'status':candidate['status'],'blocks':len(candidate['blocks'])}),flush=True);raise SystemExit(0)
OUT.mkdir(exist_ok=False)
original=Q/'structure-diagnostic/native-assembly-comparison/run-1/freeze.json'
with (OUT/'freeze.json').open('xb') as f:f.write(original.read_bytes())
freeze=read(original)
assert hashf(ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py')==freeze['code']['material_parser.py']
assert hashf(ROOT/'system2/src/pdf_extraction/ingest/native_extractor.py')==freeze['code']['native_extractor.py']
for s in freeze['samples']:
 assert hashf(ROOT/s['path'])==s['sha256'];assert hashf(ROOT/s['annotation']['path'])==s['annotation']['sha256']
tmp=Path(tempfile.mkdtemp(prefix='smarter-pdfium-granularity-',dir='/private/tmp'))
env=dict(os.environ,PYTHONPATH=str(ROOT/'system2/src'),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),XDG_CACHE_HOME=str(tmp/'cache'),HF_HOME=str(tmp/'hf'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
save(OUT/'experiment-freeze.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'original_freeze_sha256':hashf(original),'copied_freeze_sha256':hashf(OUT/'freeze.json'),'scripts':{p.name:hashf(p) for p in [Path(__file__),HERE/'material_experiment.py',HERE/'rich_native.py']},'baseline_candidates':{s['id']:hashf(Q/'after-v4-conservative-pdf'/s['id']/'candidate.json') for s in freeze['samples']},'native_config_sha256':hashf(ROOT/'system2/config/pdf-intake-positioned.yaml'),'temp':str(tmp),'readiness_guard_seconds':300,'parse_guard_seconds':60,'purpose':'Operational guards, not quality thresholds; same fixed DEV sources and denominators; no product edits.'})
for s in freeze['samples']:
 sid=s['id'];cmd=[sys.executable,str(Path(__file__).resolve()),sid];start=time.monotonic();ready=None;guard=None
 with (OUT/(sid+'-stdout.log')).open('x') as stdout,(OUT/(sid+'-stderr.log')).open('x') as stderr:
  child=subprocess.Popen(cmd,cwd=tmp,env=env,stdout=stdout,stderr=stderr);print(json.dumps({'started':sid,'owned_pid':child.pid}),flush=True)
  while child.poll() is None:
   if ready is None and (OUT/(sid+'-ready.json')).exists():
    try:ready=read(OUT/(sid+'-ready.json'))
    except json.JSONDecodeError:pass
   if ready is None and time.monotonic()-start>300:guard='readiness'
   elif ready and time.monotonic()-ready['ready_monotonic']>60:guard='parse'
   if guard:
    child.terminate()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:child.kill();child.wait()
    break
   try:child.wait(timeout=1)
   except subprocess.TimeoutExpired:pass
 if ready is None and (OUT/(sid+'-ready.json')).exists():ready=read(OUT/(sid+'-ready.json'))
 receipt={'command':cmd,'cwd':str(tmp),'status':'timeout' if guard else ('completed' if child.returncode==0 else 'failed'),'guard_stage':guard,'exit_code':child.returncode,'elapsed_seconds':time.monotonic()-start,'readiness':ready,'stdout':sid+'-stdout.log','stderr':sid+'-stderr.log'}
 save(OUT/(sid+'-receipt.json'),receipt);print(json.dumps(receipt),flush=True)
 if child.returncode!=0 or guard:save(OUT/'STOPPED.json',{'sample':sid,'receipt':receipt});raise SystemExit(1)
