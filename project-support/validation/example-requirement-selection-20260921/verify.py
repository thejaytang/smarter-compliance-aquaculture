"""Verify captured API readback of the Example Requirement selection (stdlib only)."""
from pathlib import Path
from hashlib import sha256
from itertools import product
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(name):return json.loads((HERE/name).read_text())
def walk(node):
 yield node
 for c in node.get('children',[]):yield from walk(c)
def evaluate(node,facts):
 if 'expression' in node:return facts[node['id']]
 values=[evaluate(r,facts) for r in node['rules']]
 value=all(values) if node['condition']=='AND' else any(values)
 return not value if node.get('not') else value
before=read('before-documents.json');after=read('after-documents.json');oldlogic=read('before-interpretations.json');logic=read('after-interpretations.json')
m=read('after-material.json');prior=read('before-material.json');manifest=read('selection-manifest.json');listing=read('after-requirements.json')
assert m['revision']==prior['revision']==3 and m['blocks']==prior['blocks'] and m['source']==prior['source']
assert len(m['blocks'])==85 and not m['confirmation'] and m['checked_scope']==[]
assert sha256((ROOT/'workbench/resources/examples/example.html').read_bytes()).hexdigest()=='9334a78a021971411e5c8826a2bb16aab1db707d778f6249c9a36b0afc90a4a1'
assert len(after)==len(logic)==len(listing['sessions'])==21 and len(listing['deleted'])==15
assert len([r for r in manifest if r['action']=='context-only'])==13
assert {r['key'] for r in manifest if r['classification'] in ('obligation','historical-obligation')}==set(after)
blocks={b['id']:b for b in m['blocks']}
active_ids={next(iter(d['units'])) for d in after.values()}
for key,d in after.items():
 uid=next(iter(d['units']));v=logic[key]
 assert not d['stale'] and not d.get('deleted', False) and not v['stale'] and not v['reviewed']
 assert v['session_id']==d['id'] and v['session_revision']==d['revision']
 assert v['logic']['handoff']['executable'] is False
 assert len(v['context']['materials'][0]['blocks'])==85
 citations={c['id']:c['text'] for c in v['context']['citations']}
 for context_id in ('s1-1','s2-1','s2-2','s3-1','s5-1','s8-4','s11-1','s12-1','s13-1','s14-1','s15-1'):
  assert citations[m['id']+':'+context_id]==blocks[context_id]['text']
 for field in v['fields'].values():
  for ref in field['references']:assert citations[ref['id']][ref['start']:ref['end']]==ref['quote']
 for seg in d['source_segments']:
  assert d['text'][seg['start']:seg['end']]==blocks[seg['block_id']]['text']==seg['text']
  assert seg['source_refs']==blocks[seg['block_id']]['source_refs']
 for n in walk(d['structures'][uid]):
  if n['kind']=='fragment':assert d['text'][n['span'][0]:n['span'][1]]==n['text']
  if n['kind']=='group':assert n['children'] and n['quantity'] is not None
  if n['kind']=='reference':assert n['target_id'] in active_ids
 if key!='counting':
  for k in ('id','revision','units','structures','roots','source_segments','done','reference_evidence'):
   assert d.get(k)==before[key].get(k),(key,k)
  for k in ('revision','fields','check_design','session_revision','context_fingerprint','reviewed'):
   assert v[k]==oldlogic[key][k],(key,k)
count=after['counting'];uid=next(iter(count['units']));tree=count['structures'][uid]
assert [s['block_id'] for s in count['source_segments']]==['s6-2','s6-3']
assert count['text']==blocks['s6-2']['text']+'\n\n'+blocks['s6-3']['text']
conditions=next(n for n in tree['children'] if n['role']=='conditions')
assert conditions['quantity']==2 and [n['text'] for n in conditions['children']]==[blocks['s6-2']['text'][137:205],blocks['s6-3']['text']]
assert len([n for n in walk(tree) if n['kind']=='reference'])==7
assert logic['counting']['fields']==oldlogic['counting']['fields'] and logic['counting']['check_design']==oldlogic['counting']['check_design']
for temp,brood,slaughter in product((3.99,4.0,4.01),(False,True),(False,True)):
 assert evaluate(logic['counting']['check_design']['groups']['condition'],{'count-slaughter':slaughter,'count-ge4':temp>=4,'count-lt4':temp<4,'count-broodstock':brood})==(not slaughter and not (brood and temp<4))
assert evaluate(logic['temperature']['check_design']['groups']['condition'],{'temp-no-trigger':True})
assert logic['temperature']['revision']==3 and len(logic['temperature']['check_design']['concepts'])==9
assert '2013' in logic['transition']['fields']['condition']['value'] and '15 February 2013' in logic['transition']['fields']['demand']['value']
# Every substantive paragraph still has a role: duty, attached exemption, or context.
covered={b for row in manifest for b in row['blocks']}
substantive={b['id'] for b in m['blocks'] if b['type']=='text' and not b['text'].startswith('0 ')}
# The enabling-law preamble was never a Requirement entry and remains context.
assert substantive<=covered|{'preamble-1'},substantive-covered
assert blocks['preamble-1']=={b['id']:b for b in prior['blocks']}['preamble-1']
old=read('before-store-records.json');new=read('after-store-records.json')
expected_added={'requirement_sessions':16,'requirement_steps':16,'requirement_interpretations':1,'interpretation_history':1}
for table in old:
 assert len(set(old[table])-set(new[table]))==(15 if table=='requirement_sessions' else 0),table
 assert len(set(new[table])-set(old[table]))==expected_added[table],table
receipts=read('retirement-receipts.json')
for key,receipt in receipts.items():
 d=receipt['response']['document'];assert d['deleted'] and d['revision']==before[key]['revision']+1
 for k in ('id','units','structures','roots','source_segments','reference_evidence'):
  assert d.get(k)==before[key].get(k),(key,k)
report=dict(active_requirements=21,unchanged_retained_requirements=20,context_only_entries=13,combined_counting_entries=1,recoverable_removed_entries=15,source_blocks_unchanged=85,original_html_sha256='9334a78a021971411e5c8826a2bb16aab1db707d778f6249c9a36b0afc90a4a1',all_prior_requirement_history_preserved=True,all_prior_interpretation_records_and_history_preserved=True,unrelated_requirement_heads_unchanged=True,full_context_preserved=True,exact_spans_citations_links='passed',counting_boundary_exemption_cases=12,temperature_concepts_preserved=9,human_review_completed=False,site_compliance_executed=False)
(HERE/'verification.json').write_text(json.dumps(report,indent=2))
print('PASS: 21 duties, 13 context-only entries, one combined counting requirement, unchanged full source/context, exact spans/links, all prior history, 12 counting cases, pending human review.')
