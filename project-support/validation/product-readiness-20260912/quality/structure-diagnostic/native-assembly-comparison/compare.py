"""One isolated DEV comparison; original parser/backend configuration stays frozen."""
from pathlib import Path
from hashlib import sha256
from importlib.metadata import version
from datetime import datetime,timezone
from copy import deepcopy
import json,os,subprocess,sys,tempfile,time,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];Q=HERE.parents[1];SYS=ROOT/'system2';OUT=HERE/'run-1'
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
 faulthandler.dump_traceback_later(25)
 sid,backend=sys.argv[2:];freeze=read(OUT/'freeze.json');sample=next(s for s in freeze['samples'] if s['id']==sid)
 parser=adapter(backend);path=ROOT/sample['path'];assert digest(path)==sample['sha256']
 module_policy=dict(parser.POLICY);audit=[];original_group=parser._group_pdf_paragraphs
 def checked_group(blocks,*args,**kwargs):
  before=deepcopy(blocks);after,ops=original_group(blocks,*args,**kwargs);lookup={o['group_block_id']:o['fragments'] for o in ops}
  reconstructed=[m for b in after for m in lookup.get(b['id'],[b])]
  audit.append({'before':before,'after':after,'fragment_payload_order_exact':reconstructed==before,'input_unmodified':blocks==before,'group_text_exact':all(b['text']=='\n'.join(m['text'] for m in lookup[b['id']]) for b in after if b['id'] in lookup),'group_refs_exact':all(b['source_refs']==[r for m in lookup[b['id']] for r in m['source_refs']] for b in after if b['id'] in lookup)})
  return after,ops
 parser._group_pdf_paragraphs=checked_group
 source=dict(source_id=sample['engineering_source_id'],snapshot_id=sample['engineering_source_id']+'-001',relative_path=path.name,content_hash=sample['sha256'],file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256=digest(Q/'manifest.json'))
 target=OUT/(sid+'-'+backend)
 result=parser.parse_material(source,path.parent,target,page_indices=sample['page_indices'])
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
 print(json.dumps({'sample':sid,'backend':backend,'actual_native_backends':sorted(actual),'blocks':len(result['blocks']),'status':result['status']}),flush=True)
 raise SystemExit(0)
OUT.mkdir(exist_ok=False)
samples=[s for s in read(Q/'manifest.json')['samples'] if s['id'] in {'asc-farm','asc-interpretation'}]
source_path=SYS/'src/pdf_extraction/orchestration/material_parser.py';source=source_path.read_text()
assert digest(source_path)=='3696f3aab5aff829e7247418bd0b22cec1b5f3008c6419ac842f67ff7c38bce2'
experiment=source.replace("VERSION = 'material-structural-parser/4'","VERSION = 'material-structural-parser/4+dev-native-docling'",1).replace("'pdf_backend': 'pdfium'","'pdf_backend': 'docling-parse'",1).replace('PDF candidate uses the existing positioned PDFium parser','EXPERIMENT: PDF candidate uses the installed native docling-parse parser',1)
with (OUT/'docling_experiment.py').open('x') as f:f.write(experiment)
refs=[]
for s in samples:
 assert digest(ROOT/s['path'])==s['sha256'];assert digest(ROOT/s['annotation']['path'])==s['annotation']['sha256']
 g=read(ROOT/s['annotation']['path']);seg={p['segment_id']:p for p in g['segments']};critical=[]
 for req in g['requirements']:
  source_segments=[seg[i] for i in req['source_segment_ids']]
  for field,key in [('modalities','token'),('thresholds','raw_text'),('conditions','text'),('exceptions','text'),('exemptions','text'),('negations','text'),('dates','text')]:
   for n,item in enumerate(req.get(field,[])):
    text=item.get(key) if isinstance(item,dict) else None
    if not text:continue
    pages=sorted({p['page_index'] for p in source_segments if norm(text) in norm(p['source_text'])})
    critical.append({'id':req['requirement_id']+':'+field+':'+str(n),'requirement_id':req['requirement_id'],'field':field,'text':text,'expected_page_indices':pages,'located_in_existing_source_segment':bool(pages)})
 refs.append({'sample':s['id'],'annotation':s['annotation'],'segments':len(g['segments']),'formal_texts':len(g['requirements']),'clause_bodies':sum(len(r['clauses']) for r in g['requirements']),'critical_phrases':critical})
code={'material_parser.py':digest(source_path),'native_extractor.py':digest(SYS/'src/pdf_extraction/ingest/native_extractor.py'),'pdf-intake-positioned.yaml':digest(SYS/'config/pdf-intake-positioned.yaml'),'pyproject.toml':digest(SYS/'pyproject.toml'),'uv.lock':digest(SYS/'uv.lock'),'experiment_source':digest(OUT/'docling_experiment.py'),'comparison_script':digest(Path(__file__))}
save(OUT/'freeze.json',{'started_at':datetime.now(timezone.utc).isoformat(),'samples':samples,'reference_denominators':refs,'code':code,'dependencies':{'docling-parse':version('docling-parse'),'pypdfium2':version('pypdfium2')},'relation_subset_hash':digest(Q/'structure-diagnostic/relation-subset-before.json'),'policy':'Whitespace-only complete source segment/formal/clause containment, raw/native ordering never repaired for scoring. Every existing annotation segment/requirement/clause retained. Critical phrases enumerate existing labelled verbatim fields; unlocated-in-Gold phrases remain UNMEASURED. Existing 8 positive/1 negative marker relations reused. Font or native heading confidence is not a heading PASS. No acceptance/generalization metric claim.'})
tmp=Path(tempfile.mkdtemp(prefix='smarter-native-compare-',dir='/private/tmp'));env=dict(os.environ,PYTHONPATH=str(SYS/'src'),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),XDG_CACHE_HOME=str(tmp/'cache'),NUMBA_CACHE_DIR=str(tmp/'cache/numba'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
for s in samples:
 for backend in ['pdfium','docling']:
  t=time.monotonic();cmd=[sys.executable,__file__,'worker',s['id'],backend]
  try:
   r=subprocess.run(cmd,cwd=tmp,env=env,capture_output=True,text=True,timeout=60);receipt={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
  except subprocess.TimeoutExpired as e:
   dec=lambda v:v.decode(errors='replace') if isinstance(v,bytes) else v
   receipt={'status':'timeout','stdout':dec(e.stdout),'stderr':dec(e.stderr)}
  receipt.update(command=cmd,cwd=str(tmp),elapsed_seconds=time.monotonic()-t);save(OUT/(s['id']+'-'+backend+'-receipt.json'),receipt);print(json.dumps(receipt),flush=True)
  if receipt.get('exit_code')!=0:
   save(OUT/'STOPPED.json',{'reason':'Retain failure and stop this comparison; no resource repair or product edit.','sample':s['id'],'backend':backend});raise SystemExit(1)
save(OUT/'preservation.json',{'production_parser_unchanged':digest(source_path)==code['material_parser.py'],'originals_unchanged':all(digest(ROOT/s['path'])==s['sha256'] for s in samples),'annotations_unchanged':all(digest(ROOT/s['annotation']['path'])==s['annotation']['sha256'] for s in samples),'temporary_root':str(tmp)})
