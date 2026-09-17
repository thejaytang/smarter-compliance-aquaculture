"""Read immutable baseline; output bounded engineering diagnostics, not acceptance."""
from pathlib import Path
from collections import Counter
import json
import re
import sys
from openpyxl.utils.cell import range_boundaries, coordinate_to_tuple

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
manifest=json.loads((HERE/'manifest.json').read_text())
results=[]
norm=lambda s: re.sub(r'\s+',' ',str(s)).strip()
for sample in manifest['samples']:
    candidates=[HERE/mode/sample['id']/'candidate.json' for mode in ('before','before-guarded','before-retry','pdfium-diagnostic')]
    cp=next((p for p in candidates if p.exists()),None)
    if cp is None:continue
    candidate=json.loads(cp.read_text())
    blocks=candidate['blocks']
    strings=[]
    for b in blocks:
        if b.get('text'):strings.append(b['text'])
        strings.extend(str(v) for row in b.get('table',{}).get('rows',[]) for v in row if v)
    text=norm('\n'.join(strings))
    result={'id':sample['id'],'mode':cp.parents[1].name,'baseline_equivalent':cp.parents[1].name!='pdfium-diagnostic','status':candidate['status'],'types':dict(Counter(b['type'] for b in blocks)), 'nonempty_text_or_table_cells':len(strings),'numbered_blocks':sum(bool(b.get('numbering')) for b in blocks),'parent_linked_blocks':sum(bool(b.get('parent_id')) for b in blocks),'warning_count':len(candidate['warnings']),'unresolved_count':len(candidate['unresolved'])}
    ap=ROOT/sample['annotation']['path']
    annotation=json.loads(ap.read_text())
    if 'segments' in annotation:
        segments=[s for s in annotation['segments'] if s.get('source_text')]
        misses=[{'id':s['segment_id'],'role':s['role'],'source_text':s['source_text']} for s in segments if norm(s['source_text']) not in text]
        result['segment_text_substring_diagnostic']={'found':len(segments)-len(misses),'denominator':len(segments),'missing':misses,'limitation':'Whitespace-normalized contiguous substring match only. Segments may be fragmented or reordered. Not source coverage recall; denominator completeness and relationships not validated.'}
    elif 'block_types' in annotation:
        result['synthetic_expectations']={'block_types':dict(Counter(annotation['block_types'])),'heading_levels':annotation['heading_levels'],'cells':annotation['cells'],'critical_spans':annotation['critical_spans'],'missing_critical_literals':[v for v in annotation['critical_spans'] if str(v) not in text],'limitation':'Literal presence ignores position, duplicates and context. Not critical-content fidelity acceptance.'}
    elif sample['id']=='globalgap-xlsx':
        mismatches=[];empty=0;nonempty=0;duplicates=[]
        for cell in annotation['cells']:
            r,c=coordinate_to_tuple(cell['coordinate']);values=[]
            for b in blocks:
                if b['type']!='table':continue
                for ref in b.get('source_refs',[]):
                    if ref.get('sheet')!=annotation['sheet']:continue
                    x1,y1,x2,y2=range_boundaries(ref['cell_range'])
                    if x1<=c<=x2 and y1<=r<=y2:values.append(b['table']['rows'][r-y1][c-x1])
            expected='' if cell['value'] is None else str(cell['value'])
            if expected:nonempty+=1
            else:empty+=1
            if len(values)>1:duplicates.append(cell['coordinate'])
            if len(values)!=1 or str(values[0])!=expected:mismatches.append({'cell':cell['coordinate'],'expected':expected,'observed':values})
        result['independent_cell_correspondence']={'denominator':len(annotation['cells']),'nonempty_denominator':nonempty,'empty_denominator':empty,'exact_unique':len(annotation['cells'])-len(mismatches),'mismatches':mismatches,'duplicate_cells':duplicates,'scope':annotation['sheet']+'!'+annotation['cell_range'],'trust':'source-only openpyxl inventory frozen before parser; no business or visual acceptance'}
    results.append(result)
with (HERE/(sys.argv[1] if len(sys.argv)>1 else 'baseline-diagnostics.json')).open('x') as f:json.dump({'results':results,'acceptance':'UNMEASURED: no independently validated complete source-unit/structure/Requirement denominators or untouched holdout'},f,ensure_ascii=False,indent=2)
for r in results:
    print(r['id'],r['status'],r['types'],'text/cells',r['nonempty_text_or_table_cells'])
    if 'segment_text_substring_diagnostic' in r:
        d=r['segment_text_substring_diagnostic'];print('  segment diagnostic',d['found'], '/',d['denominator'],'NOT recall')
    if 'independent_cell_correspondence' in r:
        d=r['independent_cell_correspondence'];print('  cell correspondence',d['exact_unique'],'/',d['denominator'])
