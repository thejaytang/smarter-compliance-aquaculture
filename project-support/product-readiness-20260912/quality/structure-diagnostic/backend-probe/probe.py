"""One development-window experiment: native Docling capability/resource diagnosis."""
from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version,PackageNotFoundError,distribution
import base64,json,os,shutil,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[4];SYSTEM=ROOT/'system2';Q=OUT.parents[1]
WINDOW=Q/'after-v4-conservative-pdf/asc-farm/pdf-window-0001.pdf'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def save(p,obj):
 with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
if len(sys.argv)>1 and sys.argv[1]=='worker':
 import faulthandler
 faulthandler.dump_traceback_later(20)
 from pdf_extraction.ingest.native_extractor import NativeExtractor
 from pdf_extraction.domains.requirements.hierarchy import learn_requirement_hierarchy_profile
 import docling_parse
 try:
  native=NativeExtractor('docling-parse').extract(WINDOW)
  output={'status':'success','backend':native.backend,'version':native.version,'package_path':str(Path(docling_parse.__file__).parent),'pages':[asdict(p) for p in native.pages],'heading_profile':learn_requirement_hierarchy_profile(native.pages).to_dict()}
 except Exception as e:output={'status':'failed','error_type':type(e).__name__,'error':str(e),'package_path':str(Path(docling_parse.__file__).parent)}
 save(OUT/(sys.argv[2]+'-native.json'),output);print(json.dumps({k:v for k,v in output.items() if k not in {'pages','heading_profile'}}),flush=True);raise SystemExit(0)
pkg=SYSTEM/'.venv/lib/python3.12/site-packages/docling_parse';font=pkg/'pdf_resources/fonts/standard/Times-Bold.afm';dist=distribution('docling-parse');entry=next(f for f in dist.files if str(f).endswith('fonts/standard/Times-Bold.afm'))
versions={}
for name in ['docling','docling-parse','docling-core','paddleocr','paddlex','paddlepaddle','onnxruntime','gmft','img2table','transformers','torch','pytesseract']:
 try:versions[name]=version(name)
 except PackageNotFoundError:versions[name]=None
weights=[{'path':str(p.relative_to(SYSTEM)),'bytes':p.stat().st_size} for p in (SYSTEM/'.cache/paddlex').rglob('*') if p.is_file() and p.suffix in {'.onnx','.pdparams','.pdmodel','.pdiparams'}]
start={'hypothesis':'Historical AFM failure is missing/corrupt font data versus a native resource-access condition; determine whether exact existing backend currently exposes richer native evidence. This is not learned layout or model accuracy.','source_window':str(WINDOW.relative_to(ROOT)),'window_sha256':digest(WINDOW),'original_page_indices':[27,28],'versions':versions,'font_sha256':digest(font),'font_bytes':font.stat().st_size,'font_name_line':next(l for l in font.read_text().splitlines() if l.startswith('FontName ')),'font_matches_installed_RECORD':entry.hash.value==base64.urlsafe_b64encode(font.read_bytes() and sha256(font.read_bytes()).digest()).decode().rstrip('='),'cached_weights_not_runtime_proof':weights,'product_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [SYSTEM/'src/pdf_extraction/orchestration/material_parser.py',SYSTEM/'src/pdf_extraction/ingest/native_extractor.py',SYSTEM/'src/pdf_extraction/layout/detector.py',SYSTEM/'config/pdf-intake-positioned.yaml',SYSTEM/'pyproject.toml',SYSTEM/'uv.lock']}}
save(OUT/'inventory.json',start)
tmp=Path(tempfile.mkdtemp(prefix='smarter-native-backend-',dir='/private/tmp'));env=dict(os.environ,PYTHONPATH=str(SYSTEM/'src'),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',XDG_CACHE_HOME=str(tmp/'cache'),NUMBA_CACHE_DIR=str(tmp/'cache/numba'))
def run(mode,env):
 t=time.monotonic()
 try:
  r=subprocess.run([sys.executable,__file__,'worker',mode],cwd=tmp,env=env,capture_output=True,text=True,timeout=45);receipt={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 except subprocess.TimeoutExpired as e:
  decode=lambda v:v.decode(errors='replace') if isinstance(v,bytes) else v
  receipt={'status':'timeout','stdout':decode(e.stdout),'stderr':decode(e.stderr)}
 receipt.update(mode=mode,elapsed_seconds=time.monotonic()-t,cwd=str(tmp));save(OUT/(mode+'-receipt.json'),receipt);print(json.dumps(receipt),flush=True)
 return json.loads((OUT/(mode+'-native.json')).read_text()) if (OUT/(mode+'-native.json')).exists() else None
first=run('installed-path',env)
if first and first['status']=='failed' and 'FontName' in first.get('error',''):
 alias=tmp/'ascii-package';alias.mkdir();shutil.copytree(pkg,alias/'docling_parse',ignore=shutil.ignore_patterns('__pycache__'))
 save(OUT/'ascii-control.json',{'reason':'Same experiment conditional path/resource-access control after exact AFM failure. Original installed package not edited.','package_copy':str(alias/'docling_parse'),'times_bold_copy_identical':digest(alias/'docling_parse/pdf_resources/fonts/standard/Times-Bold.afm')==digest(font)})
 run('ascii-path-control',{**env,'PYTHONPATH':str(alias)+os.pathsep+env['PYTHONPATH']})
save(OUT/'preservation.json',{'product_hashes_unchanged':all(digest(ROOT/p)==h for p,h in start['product_hashes'].items()),'font_unchanged':digest(font)==start['font_sha256'],'window_unchanged':digest(WINDOW)==start['window_sha256'],'temporary_root':str(tmp)})
