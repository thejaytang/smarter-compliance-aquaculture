"""Bounded DEV copy experiment; no product parser replacement or business writes."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import importlib.util
import json
import sys

ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent; Q=OUT.parents[1]
def write(p,v):
    with p.open('x') as f: json.dump(v,f,indent=2,ensure_ascii=False)
def sha(p): return sha256(p.read_bytes()).hexdigest()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
p=ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py'
original=p.read_text()
needle='''                    page_blocks.sort(key=lambda b:(b['source_refs'][0]['bbox'][1],b['source_refs'][0]['bbox'][0]))'''
insert='''                    from ..assemble.material_rows import join_source_rows
                    with closing(original_page.get_textpage()) as source_text_page:
                        source_text = source_text_page.get_text_range()
                    row_images = []
                    for obj in original_page.get_objects():
                        if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                            left, bottom, right, top = obj.get_bounds()
                            row_images.append([left, page.height_points-top, right, page.height_points-bottom])
                    page_blocks, row_groups = join_source_rows(page_blocks, page.width_points, source_text, lines, row_images)
                    _write(output / f'row-experiment-{index+1:04d}.json', {'page_index':index, 'source_sha256':source.content_hash, 'native_text':source_text, 'groups':row_groups})
'''+needle
assert original.count(needle)==1
copy=OUT/'experimental_parser.py'
if not copy.exists(): copy.write_text(original.replace(needle,insert))
assert copy.read_text()==original.replace(needle,insert)
module=load(copy,'pdf_extraction.orchestration.row_experiment')
module.__file__=str(p)  # Keep the copied parser's relative configuration lookup bound to System2.
OUT=OUT/'trial2'; OUT.mkdir(exist_ok=False)
from pdf_extraction.orchestration.material_parser import parse_material
assessor=load(Q/'verification-after-v4/measure_frozen_windows.py','frozen_assessor')
samples=json.loads((Q/'manifest.json').read_text())['samples']
selection=[s for s in samples if s.get('page_indices') is not None and s['id']!='pa057-reserved']
freeze={str(p.relative_to(ROOT)):sha(p) for p in [p,ROOT/'system2/src/pdf_extraction/assemble/material_rows.py',Q/'manifest.json',Q/'verification-after-v4/measure_frozen_windows.py']}
for s in selection:
    source=ROOT/s['path']; assert sha(source)==s['sha256']; freeze[str(source.relative_to(ROOT))]=sha(source)
    if s['annotation'].get('path'):
        ap=ROOT/s['annotation']['path']; assert sha(ap)==s['annotation']['sha256'];freeze[str(ap.relative_to(ROOT))]=sha(ap)
ann=Q/'verification-annotations/cs010-reserved-source-annotation.json';freeze[str(ann.relative_to(ROOT))]=sha(ann)
write(OUT/'experiment-freeze.json',{'started_at':datetime.now(timezone.utc).isoformat(),'files':freeze,'scope':'8 DEV/mechanism PDFs plus promoted CS010; not independent verification'})
summary=[]
for s in selection:
    path=ROOT/s['path']; sid=s['engineering_source_id']
    src=dict(source_id=sid,snapshot_id=sid+'-001',relative_path=path.name,content_hash=s['sha256'],file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
    row={'sample_id':s['id']}
    for tag,parser in [('before',parse_material),('experiment',module.parse_material)]:
        target=OUT/tag/s['id'];candidate=parser(src,path.parent,target,page_indices=s['page_indices'])
        row[tag]={'blocks':len(candidate['blocks']),'status':candidate['status'],'tables':[b for b in candidate['blocks'] if b['type']=='table']}
        if s['id']=='cs010-reserved':
            result=assessor.assess(json.loads(ann.read_text()),candidate);write(OUT/tag/'cs010-measurement.json',result)
            row[tag].update(content=result['content_strata'],critical=result['critical_summary'],structure=result['structure_by_type'])
    row['tables_exact']=row['before'].pop('tables')==row['experiment'].pop('tables')
    summary.append(row);print(json.dumps(row),flush=True)
assert all(sha(ROOT/n)==h for n,h in freeze.items())
write(OUT/'experiment-summary.json',{'samples':summary,'frozen_files_unchanged':True,'finished_at':datetime.now(timezone.utc).isoformat()})
