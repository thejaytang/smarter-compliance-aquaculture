"""Per-sample process limits; fallback experiments remain separate from baseline."""
from measure_baseline import ROOT,HERE,digest,write
from pathlib import Path
from collections import Counter
import json,sys,time,subprocess,faulthandler

def worker(mode,ident):
    faulthandler.dump_traceback_later(35)
    from pdf_extraction.orchestration.material_parser import parse_material
    s=next(s for s in json.loads((HERE/'manifest.json').read_text())['samples'] if s['id']==ident)
    if s['split']=='reserved_do_not_parse':raise ValueError('reserved_sample')
    p=ROOT/s['path']
    if digest(p)!=s['sha256']:raise ValueError('source drift')
    if mode=='pdfium-diagnostic':
        from pdf_extraction.ingest.native_extractor import NativeExtractor
        original=NativeExtractor.__init__
        NativeExtractor.__init__=lambda self,backend='auto':original(self,'pdfium')
    out=HERE/mode/ident
    source=dict(source_id=s['engineering_source_id'],snapshot_id=s['engineering_source_id']+'-001',relative_path=p.name,content_hash=s['sha256'],file_format=p.suffix.lstrip('.'),operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256=digest(HERE/'manifest.json'))
    r=parse_material(source,p.parent,out,page_indices=s.get('page_indices'))
    print(json.dumps({'id':ident,'status':r['status'],'block_count':len(r['blocks']),'block_types':dict(Counter(b['type'] for b in r['blocks'])),'covered_scope':r['covered_scope'],'total_scope_count':len(r['scope']),'warnings':r['warnings'],'unresolved':r['unresolved'],'requirement_status':r['requirement_status'],'candidate_path':str((out/'candidate.json').relative_to(HERE)),'mode':mode,'baseline_equivalent':mode!='pdfium-diagnostic'},ensure_ascii=False),flush=True)

def run(mode):
    target=HERE/mode;target.mkdir(exist_ok=False)
    selected=[s for s in json.loads((HERE/'manifest.json').read_text())['samples'] if s['split']!='reserved_do_not_parse' and (s['path'].endswith('.pdf') if mode in ('pdfium-diagnostic','before-retry') or mode.endswith('-pdf') else not s['path'].endswith('.pdf'))]
    for s in selected:
        started=time.monotonic()
        try:
            r=subprocess.run([sys.executable,__file__,'worker',mode,s['id']],capture_output=True,text=True,timeout=45)
            report={'id':s['id'],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'status':'returned' if r.returncode==0 else 'failed'}
        except subprocess.TimeoutExpired as e:
            decode=lambda x:x.decode(errors='replace') if isinstance(x,bytes) else x
            report={'id':s['id'],'status':'timeout','stdout':decode(e.stdout),'stderr':decode(e.stderr),'limit_seconds':45}
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        write(target/(s['id']+'-receipt.json'),report)
        print(s['id'],report['status'],report['elapsed_seconds'],report.get('stdout','')[-300:] if report.get('stdout') else '',flush=True)
        if mode=='before-retry' and report['status']=='timeout':break

if sys.argv[1]=='worker':worker(sys.argv[2],sys.argv[3])
else:run(sys.argv[1])
