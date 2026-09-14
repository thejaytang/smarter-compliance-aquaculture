from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
HERE=Path(__file__).resolve().parent;OUT=HERE/'outputs';ROOT=HERE.parents[5];Q=HERE.parents[2]
read=lambda p:json.loads(p.read_text());hashf=lambda p:sha256(p.read_bytes()).hexdigest();norm=lambda t:' '.join(t.split())
freeze=read(OUT/'freeze.json');diagnosis=read(HERE.parent/'results.json')['results'];expected={r['table_id']:r for r in diagnosis};results=[]
def flattened(directory,candidate):
 groups={g['group_block_id']:g['fragments'] for g in read(directory/'pdf-paragraph-groups.json')['groups']}
 return [f for b in candidate['blocks'] for f in groups.get(b['id'],[b])]
for sample in freeze['samples']:
 sid=sample['id'];bd=Q/'after-v4-conservative-pdf'/sid;ad=OUT/sid;b=read(bd/'candidate.json');a=read(ad/'candidate.json');bf=flattened(bd,b);af=flattened(ad,a)
 rejections=[];inspected=[]
 for p in sorted(ad.glob('pdf-table-grid-review-*.json')):
  e=read(p);rejections.extend(e['rejected']);inspected.extend(e['inspected'])
 rejected_ids={r['candidate']['id'] for r in rejections}
 amap={f['id']:f for f in af};original_retained=[f for f in bf if f['id'] not in rejected_ids];original_ids={f['id'] for f in original_retained}
 original_payloads=all(amap.get(f['id'])==f for f in original_retained)
 original_order=[f['id'] for f in original_retained]==[f['id'] for f in af if f['id'] in original_ids]
 fallback=[]
 for rej in rejections:
  page=rej['source_refs'][0]['page_index'];native_lines=rej['original_positioned_line_fallback']
  for line in native_lines:
   matches=[f for f in af if any(ref.get('native_id')==line['id'] and ref.get('page_index')==page for ref in f['source_refs'])]
   fallback.append({'page_index':page,'native_id':line['id'],'matches':len(matches),'exact_text':len(matches)==1 and matches[0]['text']==line['text'].strip(),'exact_bbox':len(matches)==1 and any(ref.get('native_id')==line['id'] and ref.get('bbox')==line['bbox_points'] for ref in matches[0]['source_refs'])})
 tables_before={x['id']:x for x in b['blocks'] if x['type']=='table'};tables_after={x['id']:x for x in a['blocks'] if x['type']=='table'}
 native_equal=[]
 for p in sorted(ad.glob('pdf-native-*.json')):
  before=read(bd/p.name);after=read(p)
  native_equal.append(before['pages']==after['pages'] and before['original_page_indices']==after['original_page_indices'] and before['source_sha256']==after['source_sha256'] and before['backend']==after['backend'])
 ratios_equal=all(e['crossing_line_numerator']==expected[e['candidate_id']]['metrics'][2]['any_internal_crossing_lines'] and e['captured_line_denominator']==expected[e['candidate_id']]['metrics'][2]['captured_line_denominator'] for e in inspected)
 unresolved=[u for u in a['unresolved'] if u['code']=='table_grid_inconsistent']
 located_unresolved=all(any(u['rejected_candidate_id']==r['candidate']['id'] and u['source_refs']==r['source_refs'] and u['message'] in a['warnings'] and (ad/u['evidence_ref']).exists() for u in unresolved) for r in rejections)
 r={'sample':sid,'before_blocks':len(b['blocks']),'after_blocks':len(a['blocks']),'inspected_tables':len(inspected),'rejected_tables':len(rejections),'retained_tables':len(tables_after),'retained_table_payloads_exact':all(tables_before.get(i)==t for i,t in tables_after.items()),'expected_table_ids_remaining':set(tables_after)==set(tables_before)-rejected_ids,'all_native_page_evidence_exact':all(native_equal),'all_original_nonrejected_fragment_payloads_exact':original_payloads,'all_original_nonrejected_fragment_order_exact':original_order,'all_new_fallback_lines_exact':all(f['matches']==1 and f['exact_text'] and f['exact_bbox'] for f in fallback),'fallback_lines':fallback,'recomputed_ratios_equal_predeclared_diagnosis':ratios_equal,'unresolved_ranges':unresolved,'all_rejections_located_and_warned':located_unresolved,'candidate_status':a['status'],'scope_coverage_unchanged':all(a[k]==b[k] for k in ['scope','processed_scope','usable_scope','unprocessed_scope']),'all_candidate_blocks_equal':a['blocks']==b['blocks']}
 g=read(ROOT/sample['annotation']['path'])
 if 'cells' in g:
  expectedcells=Counter(norm(str(x)) for x in g['cells']);beforecells=Counter(norm(v) for t in tables_before.values() for row in t['table']['rows'] for v in row if v.strip());aftercells=Counter(norm(v) for t in tables_after.values() for row in t['table']['rows'] for v in row if v.strip())
  r['synthetic_gold_cell_multiset']={'denominator':sum(expectedcells.values()),'before_matches':sum((expectedcells & beforecells).values()),'after_matches':sum((expectedcells & aftercells).values()),'rules':'Exact whitespace-normalized string multiset intersection of Gold cells and candidate nonempty table cells; mechanism diagnostic, not real-material acceptance.','missing_before':dict(expectedcells-beforecells),'missing_after':dict(expectedcells-aftercells)}
 results.append(r)
 print(sid,json.dumps({k:r[k] for k in ['before_blocks','after_blocks','inspected_tables','rejected_tables','retained_tables','all_native_page_evidence_exact','all_original_nonrejected_fragment_payloads_exact','all_original_nonrejected_fragment_order_exact','all_new_fallback_lines_exact','all_rejections_located_and_warned','all_candidate_blocks_equal']}))
 if 'synthetic_gold_cell_multiset' in r:print(r['synthetic_gold_cell_multiset'])
with (OUT/'verification.json').open('x') as f:json.dump({'results':results,'verification_script_sha256':hashf(Path(__file__)),'boundary':'Preservation/rejection behavior on exposed DEV, no production or independent quality acceptance.'},f,indent=2)
