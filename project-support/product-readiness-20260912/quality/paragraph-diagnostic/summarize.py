from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
r=json.loads((HERE/'proposal-results.json').read_text()); summaries=[]
for d,gn in zip(r,['farm-standard-p028-p029','interpretation-manual-p019-p021']):
 g=json.loads((ROOT/'system2/gold/requirements/annotations'/f'{gn}.json').read_text())
 ids={x['requirement_id'] for x in g['requirements']}
 def normalize(s):return re.sub(r'\s+',' ',s).strip()
 checks=d['checks']; formal=[c for c in checks if c['id'] in ids]; clauses=[c for c in checks if c['id'] not in ids]
 s={'id':d['id'],'counts':{},'legacy_comparison':[],'table_candidates':[],'source_order_and_payload_unchanged':d['content_and_order_preserved']}
 for name,rows in [('formal_normative_text',formal),('annotated_clause_text',clauses)]:s['counts'][name]={'denominator':len(rows),'before_single_group':sum(x['before'] for x in rows),'after_single_group':sum(x['after'] for x in rows),'note':'Active engineering diagnostics, not recall or Requirement classification; overlapping formal/clause checks must not be pooled.'}
 for rr in g['requirements']:
  legacy=next((x for x in d['legacy_formal_candidates'] if x['requirement_id']==rr['requirement_id']),None)
  s['legacy_comparison'].append({'id':rr['requirement_id'],'native_assembler_exact_normative_text':bool(legacy and normalize(legacy['normative_text'])==normalize(rr['normative_text'])),'source_span_count':len(legacy['source_segments']) if legacy else 0})
 for group in d['groups']:
  for b in group['members']:
   if b['type']=='table':s['table_candidates'].append({'id':b['id'],'source_ref':b['source_refs'][0],'rows':len(b['table']['rows']),'cols':len(b['table']['rows'][0]),'nonempty_cells':sum(bool(x.strip()) for row in b['table']['rows'] for x in row)})
 summaries.append(s)
with (HERE/'summary.json').open('x') as f:json.dump(summaries,f,indent=2)
print(json.dumps(summaries,indent=2))
