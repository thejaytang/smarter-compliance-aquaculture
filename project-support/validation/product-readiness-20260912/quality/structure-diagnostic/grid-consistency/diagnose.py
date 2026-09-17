"""Read-only geometric diagnosis on existing frozen DEV renders/native evidence."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from statistics import median
import json,sys,time,faulthandler
ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;Q=HERE.parents[1]
BASE=Q/'after-v4-conservative-pdf'
SAMPLES=['asc-farm','asc-interpretation','asc-audit','asc-salmon-cod','born-digital-multicolumn','cross-page-content','borderless-merged-figure']
read=lambda p:json.loads(p.read_text());hashf=lambda p:sha256(p.read_bytes()).hexdigest()
def save(name,d):
 with (HERE/name).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
inputs=[]
for sid in SAMPLES:
 inputs.extend([BASE/sid/'candidate.json',*sorted((BASE/sid).glob('pdf-native-*.json')),*sorted((BASE/sid).glob('pdf-page-*.png'))])
for n in ['born-digital-multicolumn','cross-page-content','borderless-merged-figure']:inputs.append(ROOT/'system2/gold/annotations'/f'{n}.json')
inputs.extend([Path(__file__),ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py',ROOT/'system2/src/pdf_extraction/layout/detector.py',ROOT/'system2/src/pdf_extraction/parsers/table.py',ROOT/'system2/uv.lock'])
freeze={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Existing accepted DEV candidate grids only; re-evaluate their already retained rendered PNGs, not PDFs or reserved materials.','files':{str(p.relative_to(ROOT)):hashf(p) for p in inputs},'tolerances_points':[0,0.5,1,2],'metric_definitions':{'captured':'Nonempty native line center inside the accepted overall grid bbox and an actual merged-cell rectangle; merged-cell center rule equals current cell assignment.','internal_vertical_crossing':'Line bbox extends past owner merged cell left/right at a genuinely internal table boundary by more than tolerance.','internal_horizontal_crossing':'Same for owner merged cell top/bottom.','external_clipping':'Line center is captured but line bbox extends beyond the overall table bbox by more than tolerance.','denominator':'All nonempty native lines whose centers are captured by this accepted table; report each table separately.','fallback':'Exact original native line payloads currently suppressed by this table, plus captured/partially clipped records; no rewritten candidate or product mutation.'},'policy':'Measure all 4 fixed tolerances; do not tune source labels or hide true-table collisions. No font/text-specific decision rule.'}
save('freeze.json',freeze)
faulthandler.dump_traceback_later(30,repeat=True);started=time.monotonic()
import numpy as np
from PIL import Image
from pdf_extraction.config import TableSettings
from pdf_extraction.layout.detector import detect_table_boxes
from pdf_extraction.parsers.table import _grid_positions,_merged_cell_specs,_compact_grid_specs
results=[]
for sid in SAMPLES:
 candidate=read(BASE/sid/'candidate.json');native={}
 for p in (BASE/sid).glob('pdf-native-*.json'):
  e=read(p)
  native.update(zip(e['original_page_indices'],e['pages']))
 tables=[b for b in candidate['blocks'] if b['type']=='table']
 for page_index in sorted({b['source_refs'][0]['page_index'] for b in tables}):
  image_path=BASE/sid/f'pdf-page-{page_index+1:04d}.png';array=np.asarray(Image.open(image_path).convert('RGB'));native_page=native[page_index]
  expected=[b for b in tables if b['source_refs'][0]['page_index']==page_index]
  for number,box in enumerate(detect_table_boxes(image_path,TableSettings(backend='native',recognition_pipeline_enabled=False,img2table_enabled=False,gmft_enabled=False))):
   crop=array[box.y0:box.y1,box.x0:box.x1];xs,ys=_grid_positions(crop)
   if len(xs)<2 or len(ys)<2 or (len(xs)-1)*(len(ys)-1)>10000:continue
   specs,xs,ys=_compact_grid_specs(_merged_cell_specs(crop,xs,ys),xs,ys)
   outer=[(box.x0+xs[0])/1.5,(box.y0+ys[0])/1.5,(box.x0+xs[-1])/1.5,(box.y0+ys[-1])/1.5]
   match=[b for b in expected if max(abs(a-bb) for a,bb in zip(outer,b['source_refs'][0]['bbox']))<1e-5]
   if not match:continue
   assert len(match)==1;b=match[0]
   cells=[{'row':r,'col':c,'rowspan':rs,'colspan':cs,'bbox':[(box.x0+xs[c])/1.5,(box.y0+ys[r])/1.5,(box.x0+xs[c+cs])/1.5,(box.y0+ys[r+rs])/1.5]} for r,c,rs,cs in specs]
   merges=[{k:cell[k] for k in ['row','col','rowspan','colspan']} for cell in cells if cell['rowspan']>1 or cell['colspan']>1]
   assert merges==b['table']['merges'];assert [len(ys)-1,len(xs)-1]==[len(b['table']['rows']),len(b['table']['rows'][0])]
   rows=[['']*(len(xs)-1) for _ in range(len(ys)-1)]
   for cell in cells:
    x0,y0,x1,y1=cell['bbox'];words=[w for w in native_page['words'] if x0<=(w['bbox_points'][0]+w['bbox_points'][2])/2<x1 and y0<=(w['bbox_points'][1]+w['bbox_points'][3])/2<y1]
    rows[cell['row']][cell['col']]=' '.join(w['text'] for w in words).strip()
   assert rows==b['table']['rows']
   captured=[];suppressed=[];lines=native_page['text_lines'] or native_page['words']
   for line in lines:
    if not line['text'].strip():continue
    l,t,r,bt=line['bbox_points'];cx=(l+r)/2;cy=(t+bt)/2
    if outer[0]<=l and outer[1]<=t and r<=outer[2] and bt<=outer[3]:suppressed.append(line)
    owners=[c for c in cells if c['bbox'][0]<=cx<c['bbox'][2] and c['bbox'][1]<=cy<c['bbox'][3]]
    if not owners:continue
    assert len(owners)==1;owner=owners[0];x0,y0,x1,y1=owner['bbox']
    dx=[max(0.,x0-l) if x0>outer[0]+1e-6 else 0.,max(0.,r-x1) if x1<outer[2]-1e-6 else 0.]
    dy=[max(0.,y0-t) if y0>outer[1]+1e-6 else 0.,max(0.,bt-y1) if y1<outer[3]-1e-6 else 0.]
    outside=[max(0.,outer[0]-l),max(0.,outer[1]-t),max(0.,r-outer[2]),max(0.,bt-outer[3])]
    captured.append({'line':line,'owner':owner,'internal_x_overflow_points':dx,'internal_y_overflow_points':dy,'external_overflow_points':outside,'line_height':bt-t})
   metrics=[]
   for tolerance in freeze['tolerances_points']:
    vx=[c for c in captured if max(c['internal_x_overflow_points'])>tolerance];hy=[c for c in captured if max(c['internal_y_overflow_points'])>tolerance];anycross=[c for c in captured if max(c['internal_x_overflow_points']+c['internal_y_overflow_points'])>tolerance];outside=[c for c in captured if max(c['external_overflow_points'])>tolerance]
    metrics.append({'tolerance_points':tolerance,'captured_line_denominator':len(captured),'internal_vertical_crossing_lines':len(vx),'internal_horizontal_crossing_lines':len(hy),'any_internal_crossing_lines':len(anycross),'internal_crossing_fraction':len(anycross)/len(captured) if captured else None,'center_captured_but_partly_outside_lines':len(outside)})
   r={'sample':sid,'page_index':page_index,'table_id':b['id'],'bbox':outer,'shape':[len(ys)-1,len(xs)-1],'column_widths_points':[(xs[i+1]-xs[i])/1.5 for i in range(len(xs)-1)],'row_heights_points':[(ys[i+1]-ys[i])/1.5 for i in range(len(ys)-1)],'cell_rectangles':cells,'reconstructed_grid_merges_and_text_equal_candidate':True,'metrics':metrics,'captured_lines':captured,'exact_suppressed_line_fallback':suppressed,'max_internal_crossing_points':max((max(c['internal_x_overflow_points']+c['internal_y_overflow_points']) for c in captured),default=0.),'max_external_clipping_points':max((max(c['external_overflow_points']) for c in captured),default=0.)}
   results.append(r)
   print(json.dumps({'sample':sid,'page':page_index+1,'shape':r['shape'],'tol1':metrics[2],'max_internal_cut':r['max_internal_crossing_points'],'max_external_clip':r['max_external_clipping_points']}),flush=True)
  assert len([r for r in results if r['sample']==sid and r['page_index']==page_index])==len(expected)
faulthandler.cancel_dump_traceback_later()
save('results.json',{'elapsed_seconds':time.monotonic()-started,'results':results,'preservation':{str(p.relative_to(ROOT)):hashf(p)==freeze['files'][str(p.relative_to(ROOT))] for p in inputs}})
