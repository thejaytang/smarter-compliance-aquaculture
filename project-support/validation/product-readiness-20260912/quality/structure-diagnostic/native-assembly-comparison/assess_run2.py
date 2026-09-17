"""Read-only fixed-rule DEV diagnostic; no product changes or fuzzy matching."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
HERE=Path(__file__).resolve().parent;OUT=HERE/'run-2';ROOT=HERE.parents[4];Q=HERE.parents[1]
read=lambda p:json.loads(p.read_text());norm=lambda t:' '.join(t.split())
def text(b):return '\n'.join('\n'.join(row) for row in b['table']['rows']) if b['type']=='table' else b.get('text','')
def page_ids(b):return {r['page_index'] for r in b['source_refs'] if 'page_index' in r}
freeze=read(OUT/'freeze.json');relations=read(Q/'structure-diagnostic/relation-subset-before.json')['relations'];all_results=[]
for sample in freeze['samples']:
 annotation=read(ROOT/sample['annotation']['path']);byseg={s['segment_id']:s for s in annotation['segments']};frozen=next(r for r in freeze['reference_denominators'] if r['sample']==sample['id'])
 for backend in ['pdfium','docling']:
  directory=OUT/(sample['id']+'-'+backend)
  if not (directory/'experiment-provenance.json').exists():continue
  c=read(directory/'candidate.json');blocks=c['blocks'];audit=read(directory/'assembly-audit.json');rawblocks=[b for page in audit for b in page['before']]
  def texts_on(p):return [text(b) for b in blocks if p in page_ids(b)]
  page_text={p:norm('\n'.join(texts_on(p))) for p in sample['page_indices']}
  segments=[]
  for seg in annotation['segments']:
   target=norm(seg['source_text']);p=seg['page_index']
   segments.append({'id':seg['segment_id'],'role':seg['role'],'page_index':p,'target':seg['source_text'],'complete_in_page':target in page_text[p],'single_block_before_grouping':any(target in norm(text(b)) for b in rawblocks if p in page_ids(b)),'single_block_after_grouping':any(target in norm(text(b)) for b in blocks if p in page_ids(b))})
  reqchecks=[]
  for req in annotation['requirements']:
   pages={byseg[i]['page_index'] for i in req['source_segment_ids']}
   for kind,identity,target in [('formal',req['requirement_id'],req['normative_text'])]+[('clause',x['clause_id'],x['text']) for x in req['clauses']]:
    reqchecks.append({'kind':kind,'id':identity,'target':target,'single_block_before_grouping':any(norm(target) in norm(text(b)) for b in rawblocks if pages & page_ids(b)),'single_block_after_grouping':any(norm(target) in norm(text(b)) for b in blocks if pages & page_ids(b)),'complete_on_a_bound_page':any(norm(target) in page_text[p] for p in pages)})
  critical=[]
  for phrase in frozen['critical_phrases']:
   pages=phrase['expected_page_indices'];matches=[p for p in pages if norm(phrase['text']) in page_text[p]]
   critical.append({**phrase,'status':('PASS' if matches else 'FAIL') if pages else 'UNMEASURED','matched_page_indices':matches,'association_accuracy':'UNMEASURED'})
  pairs=[]
  for rel in [r for r in relations if r['sample_id']==sample['id']]:
   selected=[b for b in blocks if rel['page_index'] in page_ids(b)]
   represented=any(b.get('numbering')==rel['marker'] and norm(rel['body']) in norm(text(b)) for b in selected)
   represented=represented or any(norm(text(a))==rel['marker'] and norm(rel['body']) in norm(text(b)) for a,b in zip(selected,selected[1:]))
   pairs.append({'marker':rel['marker'],'body':rel['body'],'page_index':rel['page_index'],'expected_pair':rel['expected_pair'],'represented_pair':represented,'status':'PASS' if represented==rel['expected_pair'] else 'FAIL'})
  native=[]
  for path in sorted(directory.glob('pdf-native-*.json')):
   e=read(path)
   for original,p in zip(e['original_page_indices'],e['pages']):
    native.append({'page_index':original,'backend':e['backend'],'words':len(p['words']),'text_lines':len(p['text_lines']),'nonempty_lines':sum(bool(w['text'].strip()) for w in p['text_lines']),'characters':len(p['characters']),'words_with_font':sum(bool(w.get('font_name')) for w in p['words']),'words_with_multiple_whitespace_tokens':sum(len(w['text'].split())>1 for w in p['words'])})
  r={'sample':sample['id'],'backend':backend,'provenance':read(directory/'experiment-provenance.json'),'native':native,'block_count':len(blocks),'block_types':dict(Counter(b['type'] for b in blocks)),'numbered_blocks':sum(bool(b.get('numbering')) for b in blocks),'actual_heading_blocks':sum(b['type']=='heading' for b in blocks),'parent_linked_blocks':sum(bool(b.get('parent_id')) for b in blocks),'tables':[{'shape':[len(b['table']['rows']),len(b['table']['rows'][0])],'rows':b['table']['rows'],'refs':b['source_refs']} for b in blocks if b['type']=='table'],'segments':segments,'requirement_text_checks':reqchecks,'critical_phrases':critical,'marker_relations':pairs,'candidate_status':c['status'],'unresolved':c['unresolved']}
  r['summary']={'source_segments':{'denominator':len(segments),'page_complete':sum(x['complete_in_page'] for x in segments),'single_block_before':sum(x['single_block_before_grouping'] for x in segments),'single_block_after':sum(x['single_block_after_grouping'] for x in segments)},'critical_phrases':dict(Counter(x['status'] for x in critical)),'marker_relations':dict(Counter(x['status'] for x in pairs))}
  for kind in ['formal','clause']:
   selection=[x for x in reqchecks if x['kind']==kind];r['summary'][kind]={'denominator':len(selection),'single_block_before':sum(x['single_block_before_grouping'] for x in selection),'single_block_after':sum(x['single_block_after_grouping'] for x in selection),'complete_on_a_page':sum(x['complete_on_a_bound_page'] for x in selection)}
  all_results.append(r)
  print(sample['id'],backend,'blocks',len(blocks),'types',r['block_types'],'numbered',r['numbered_blocks'],json.dumps(r['summary']))
with (OUT/'assessment.json').open('x') as f:json.dump({'results':all_results,'assessment_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'boundary':'All scores are overlapping active-DEV diagnostics, not independent coverage/structure acceptance. Exact same whitespace-only rules and existing reference denominators apply to both backends; no fuzzy text repair. Richer font/native heading metadata does not validate visually occluded text.'},f,ensure_ascii=False,indent=2)
